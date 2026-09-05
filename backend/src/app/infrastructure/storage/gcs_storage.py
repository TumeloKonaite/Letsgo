"""Private, prefix-scoped GCS image storage with explicit credentials."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import timedelta
from urllib.parse import quote, unquote, urlparse

import google.auth
from google.api_core.exceptions import Forbidden, GoogleAPIError, NotFound, Unauthorized
from google.auth import identity_pool
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.cloud.storage import Client
from google.oauth2 import service_account

from app.core.config import Settings
from app.domain.packages.storage import (
    StorageAuthenticationError,
    StorageBucketNotFoundError,
    StorageError,
    StorageService,
    StoredObject,
)


class ModalTokenSupplier(identity_pool.SubjectTokenSupplier):
    def get_subject_token(self, context, request):
        token = os.environ.get("MODAL_IDENTITY_TOKEN")
        if not token:
            raise GoogleAuthError("Workload identity unavailable")
        return token


class GcsStorageService(StorageService):
    def __init__(
        self,
        *,
        project_id: str,
        bucket_name: str,
        object_prefix: str,
        client: Client | None = None,
        client_factory: Callable[[], Client] | None = None,
        service_account_email: str | None = None,
    ) -> None:
        self._bucket_name = bucket_name
        self._prefix = object_prefix
        self._client = client
        self._client_factory = client_factory
        self._service_account_email = service_account_email

    def _get_client(self):
        if self._client is None:
            if self._client_factory is None:
                raise StorageAuthenticationError("Image storage unavailable")
            self._client = self._client_factory()
        return self._client

    def _validate_name(self, name):
        if (
            not name.startswith(self._prefix)
            or any(part in ("", ".", "..") for part in name.split("/"))
            or "\\" in name
        ):
            raise StorageError("Invalid image reference")
        return name

    def _blob(self, name):
        self._validate_name(name)
        # No bucket metadata or list permission is required.
        return self._get_client().bucket(self._bucket_name).blob(name)

    def _run(self, operation):
        try:
            return operation()
        except (Forbidden, Unauthorized, GoogleAuthError):
            raise StorageAuthenticationError("Image storage unavailable") from None
        except NotFound:
            raise StorageBucketNotFoundError("Image storage unavailable") from None
        except (GoogleAPIError, OSError, ValueError, TypeError):
            raise StorageError("Image storage unavailable") from None

    def upload_image(self, object_name, content, content_type):
        # Domain names begin with packages/; prefix is a deployment namespace.
        name = self._prefix + object_name
        self._run(
            lambda: self._blob(name).upload_from_string(
                content, content_type=content_type, if_generation_match=0
            )
        )
        return StoredObject(
            name,
            f"https://storage.googleapis.com/{self._bucket_name}/{quote(name, safe='/')}",
            content_type,
            len(content),
        )

    def delete_image(self, object_name):
        def delete():
            try:
                self._blob(object_name).delete()
            except NotFound:
                pass

        self._run(delete)

    def get_public_url(self, object_name):
        """Legacy interface name: return a private GET capability valid for 15 minutes."""

        def sign():
            blob = self._blob(object_name)
            kwargs = {}
            if self._service_account_email:
                credentials = self._get_client()._credentials
                if not credentials.valid:
                    credentials.refresh(Request())
                kwargs = {
                    "service_account_email": self._service_account_email,
                    "access_token": credentials.token,
                }
            return blob.generate_signed_url(
                version="v4", expiration=timedelta(minutes=15), method="GET", **kwargs
            )

        return self._run(sign)

    def extract_object_name(self, url):
        parsed = urlparse(url)
        prefix = f"/{self._bucket_name}/"
        if (
            parsed.scheme != "https"
            or parsed.netloc != "storage.googleapis.com"
            or not parsed.path.startswith(prefix)
        ):
            return None
        try:
            return self._validate_name(unquote(parsed.path[len(prefix) :]))
        except StorageError:
            return None


def create_storage_service(settings: Settings) -> StorageService:
    settings.validate_storage_configuration()

    def create_client():
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        if settings.gcs_wif_audience:
            credentials = identity_pool.Credentials(
                audience=settings.gcs_wif_audience,
                subject_token_type="urn:ietf:params:oauth:token-type:jwt",
                subject_token_supplier=ModalTokenSupplier(),
                token_url="https://sts.googleapis.com/v1/token",
                service_account_impersonation_url=(
                    "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
                    f"{settings.gcs_service_account_email}:generateAccessToken"
                ),
                scopes=scopes,
            )
        elif settings.gcp_service_account_json:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(settings.gcp_service_account_json), scopes=scopes
            )
        elif settings.google_application_credentials:
            credentials, _ = google.auth.load_credentials_from_file(
                settings.google_application_credentials, scopes=scopes
            )
        else:
            raise GoogleAuthError("Explicit credentials required")
        return Client(project=settings.gcp_project_id, credentials=credentials)

    return GcsStorageService(
        project_id=settings.gcp_project_id,
        bucket_name=settings.gcs_bucket_name,
        object_prefix=settings.gcs_object_prefix,
        client_factory=create_client,
        service_account_email=settings.gcs_service_account_email,
    )
