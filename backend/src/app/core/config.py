"""Parse environment settings and enforce deployment-specific startup requirements."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEFAULT_APP_NAME = "LetsGoSA API"
DEFAULT_DEBUG = False
DEFAULT_API_PREFIX = "/api"
DEFAULT_API_VERSION = "0.1.0"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_STORAGE_PROVIDER = "gcs"
DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0
DEFAULT_OPENAI_MAX_RETRIES = 2
VALID_ENVIRONMENTS = frozenset({"development", "test", "staging", "production"})
DEPLOYED_ENVIRONMENTS = frozenset({"staging", "production"})
SUPPORTED_POSTGRESQL_DRIVERS = frozenset({"postgresql+psycopg"})
SUPPORTED_SQLITE_DRIVERS = frozenset({"sqlite", "sqlite+pysqlite"})
DEFAULT_DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_CHATBOT_CONTENT_DATA_DIR = Path(__file__).resolve().parents[4] / "data"
DEFAULT_CHATBOT_CONVERSATION_STORAGE_DIR = (
    DEFAULT_CHATBOT_CONTENT_DATA_DIR / "conversations"
)
_CLAIM_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class ConfigurationError(ValueError):
    """Raised when startup configuration is missing, incomplete, or malformed."""


def _find_dotenv_path() -> Path | None:
    """Find the nearest repository-level .env file, if one exists."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def _strip_optional_quotes(value: str) -> str:
    """Remove matching quotes around a value read from a local .env file."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _read_dotenv(path: Path) -> dict[str, str]:
    """Parse simple key-value pairs from a development .env file."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key:
            values[key] = _strip_optional_quotes(value.strip())
    return values


def _load_dotenv() -> None:
    """Load a local file only when it explicitly identifies development."""
    process_environment = (os.getenv("LETSGOSA_ENV") or "").strip().lower()
    if process_environment and process_environment != "development":
        return
    dotenv_path = _find_dotenv_path()
    if dotenv_path is None:
        return
    values = _read_dotenv(dotenv_path)
    if values.get("LETSGOSA_ENV", "").strip().lower() != "development":
        return
    for key, value in values.items():
        os.environ.setdefault(key, value)


def _optional_env(name: str) -> str | None:
    """Read a trimmed environment value and treat blank input as missing."""
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _pem_env(name: str) -> str | None:
    """Read PEM text while expanding escaped newlines used in .env files."""
    value = _optional_env(name)
    return value.replace("\\n", "\n") if value else None


def _as_bool(name: str, default: bool = False) -> bool:
    """Parse a required-or-defaulted boolean environment value."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean")


def _as_int(name: str, default: int) -> int:
    """Parse an integer environment value or return its safe default."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


def _optional_int(name: str) -> int | None:
    """Parse an optional integer environment value."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


def _optional_bool(name: str) -> bool | None:
    """Parse an optional boolean environment value."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean")


def _as_float(name: str, default: float) -> float:
    """Parse a numeric environment value or return its safe default."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc


def _as_csv(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Split a comma-separated environment value into trimmed entries."""
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _resolve_path(value: str | None, default: Path) -> Path:
    """Resolve configured paths relative to the repository root."""
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[4] / path).resolve()
    return path


def _require_values(group: str, values: tuple[tuple[str, object | None], ...]) -> None:
    """Raise a redacted error listing missing variables in one config group."""
    missing = [
        name for name, value in values if value is None or not str(value).strip()
    ]
    if missing:
        raise ConfigurationError(
            f"Missing required {group} configuration: {', '.join(missing)}"
        )


def _validate_http_url(name: str, value: str, *, https_only: bool = False) -> None:
    """Validate an absolute HTTP URL without embedded credentials."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ConfigurationError(f"{name} must be a valid absolute URL") from None
    allowed_schemes = {"https"} if https_only else {"http", "https"}
    if (
        parsed.scheme.lower() not in allowed_schemes
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        and not 1 <= port <= 65535
    ):
        scheme_description = "HTTPS" if https_only else "HTTP(S)"
        raise ConfigurationError(
            f"{name} must be a valid absolute {scheme_description} URL"
        )


def _validate_origin(name: str, value: str, *, https_only: bool = False) -> None:
    """Validate a URL as an exact origin with no path or trailing slash."""
    _validate_http_url(name, value, https_only=https_only)
    parsed = urlsplit(value)
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ConfigurationError(
            f"{name} entries must be origins without paths, queries, or fragments"
        )
    if value.endswith("/"):
        raise ConfigurationError(f"{name} entries must not have a trailing slash")


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = ""
    database_url: str = field(default="", repr=False)
    cors_allow_origins: tuple[str, ...] = ()
    clerk_secret_key: str | None = field(default=None, repr=False)
    clerk_jwt_key: str | None = field(default=None, repr=False)
    clerk_issuer_url: str | None = None
    clerk_authorized_parties: tuple[str, ...] = ()
    clerk_admin_claim: str | None = None
    clerk_webhook_signing_secret: str | None = field(default=None, repr=False)
    storage_provider: str = ""
    gcp_project_id: str | None = None
    gcs_bucket_name: str | None = None
    gcs_public_base_url: str | None = None
    gcs_conversation_bucket_name: str | None = None
    gcp_service_account_json: str | None = field(default=None, repr=False)
    google_application_credentials: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = field(default=None, repr=False)
    smtp_password: str | None = field(default=None, repr=False)
    smtp_from_email: str | None = None
    contact_to_email: str | None = None
    smtp_use_tls: bool | None = None
    openai_api_key: str | None = field(default=None, repr=False)
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_timeout_seconds: float = DEFAULT_OPENAI_TIMEOUT_SECONDS
    openai_max_retries: int = DEFAULT_OPENAI_MAX_RETRIES
    chatbot_content_data_dir: Path = DEFAULT_CHATBOT_CONTENT_DATA_DIR
    chatbot_conversation_storage_dir: Path = DEFAULT_CHATBOT_CONVERSATION_STORAGE_DIR
    package_image_max_upload_bytes: int = DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES
    app_name: str = DEFAULT_APP_NAME
    debug: bool = DEFAULT_DEBUG
    api_prefix: str = DEFAULT_API_PREFIX
    api_version: str = DEFAULT_API_VERSION
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @property
    def normalized_environment(self) -> str:
        """Return the normalized deployment-tier name."""
        return self.environment.strip().lower()

    @property
    def is_production(self) -> bool:
        """Report whether these settings target production."""
        return self.normalized_environment == "production"

    @property
    def is_deployed(self) -> bool:
        """Report whether strict staging/production rules should apply."""
        return self.normalized_environment in DEPLOYED_ENVIRONMENTS

    @classmethod
    def from_env(cls) -> Settings:
        """Build typed settings from canonical environment variables."""
        _load_dotenv()
        environment = _optional_env("LETSGOSA_ENV") or ""
        development_origins = (
            DEFAULT_DEVELOPMENT_CORS_ORIGINS
            if environment.lower() == "development"
            else ()
        )
        return cls(
            environment=environment,
            database_url=_optional_env("LETSGOSA_DATABASE_URL") or "",
            cors_allow_origins=_as_csv("CORS_ORIGINS", development_origins),
            clerk_secret_key=_optional_env("CLERK_SECRET_KEY"),
            clerk_jwt_key=_pem_env("CLERK_JWT_KEY"),
            clerk_issuer_url=_optional_env("CLERK_ISSUER_URL"),
            clerk_authorized_parties=_as_csv("CLERK_AUTHORIZED_PARTIES"),
            clerk_admin_claim=_optional_env("CLERK_ADMIN_CLAIM"),
            clerk_webhook_signing_secret=_optional_env("CLERK_WEBHOOK_SIGNING_SECRET"),
            storage_provider=_optional_env("STORAGE_PROVIDER") or "",
            gcp_project_id=_optional_env("GCP_PROJECT_ID"),
            gcs_bucket_name=_optional_env("GCS_BUCKET_NAME"),
            gcs_public_base_url=_optional_env("GCS_PUBLIC_BASE_URL"),
            gcs_conversation_bucket_name=_optional_env("GCS_CONVERSATION_BUCKET_NAME"),
            gcp_service_account_json=_optional_env("GCP_SERVICE_ACCOUNT_JSON"),
            google_application_credentials=_optional_env(
                "GOOGLE_APPLICATION_CREDENTIALS"
            ),
            smtp_host=_optional_env("SMTP_HOST"),
            smtp_port=_optional_int("SMTP_PORT"),
            smtp_username=_optional_env("SMTP_USERNAME"),
            smtp_password=_optional_env("SMTP_PASSWORD"),
            smtp_from_email=_optional_env("SMTP_FROM_EMAIL"),
            contact_to_email=_optional_env("CONTACT_TO_EMAIL"),
            smtp_use_tls=_optional_bool("SMTP_USE_TLS"),
            openai_api_key=_optional_env("OPENAI_API_KEY"),
            openai_model=_optional_env("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
            openai_timeout_seconds=_as_float(
                "OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_TIMEOUT_SECONDS
            ),
            openai_max_retries=_as_int(
                "OPENAI_MAX_RETRIES", DEFAULT_OPENAI_MAX_RETRIES
            ),
            chatbot_content_data_dir=_resolve_path(
                _optional_env("CONTENT_DATA_DIR"), DEFAULT_CHATBOT_CONTENT_DATA_DIR
            ),
            chatbot_conversation_storage_dir=_resolve_path(
                _optional_env("CONVERSATION_STORAGE_DIR"),
                DEFAULT_CHATBOT_CONVERSATION_STORAGE_DIR,
            ),
            package_image_max_upload_bytes=_as_int(
                "PACKAGE_IMAGE_MAX_UPLOAD_BYTES",
                DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES,
            ),
            app_name=_optional_env("LETSGOSA_APP_NAME") or DEFAULT_APP_NAME,
            debug=_as_bool("LETSGOSA_DEBUG", DEFAULT_DEBUG),
            api_prefix=_optional_env("LETSGOSA_API_PREFIX") or DEFAULT_API_PREFIX,
            api_version=_optional_env("LETSGOSA_API_VERSION") or DEFAULT_API_VERSION,
        )

    def validate_environment(self) -> None:
        """Validate the deployment tier and its debug policy."""
        if self.normalized_environment not in VALID_ENVIRONMENTS:
            raise ConfigurationError(
                "LETSGOSA_ENV must be one of: development, test, staging, production"
            )
        if self.is_deployed and self.debug:
            raise ConfigurationError(
                "LETSGOSA_DEBUG must be false in staging and production"
            )

    def validate_database_configuration(self) -> None:
        """Validate the database driver, address, credentials, and TLS policy."""
        _require_values("database", (("LETSGOSA_DATABASE_URL", self.database_url),))
        try:
            url = make_url(self.database_url)
            _ = url.port
        except (ArgumentError, ValueError):
            raise ConfigurationError("LETSGOSA_DATABASE_URL is malformed") from None
        driver = url.drivername.lower()
        if driver in SUPPORTED_POSTGRESQL_DRIVERS:
            if not url.username or not url.host or not url.database:
                raise ConfigurationError(
                    "LETSGOSA_DATABASE_URL must include a username, host, and database name"
                )
            if self.is_deployed and not url.password:
                raise ConfigurationError(
                    "LETSGOSA_DATABASE_URL must include credentials in staging and production"
                )
            if self.is_deployed and url.query.get("sslmode") not in {
                "verify-ca",
                "verify-full",
            }:
                raise ConfigurationError(
                    "LETSGOSA_DATABASE_URL must use sslmode=verify-ca or verify-full "
                    "in staging and production"
                )
            return
        if self.is_deployed or driver not in SUPPORTED_SQLITE_DRIVERS:
            raise ConfigurationError(
                "LETSGOSA_DATABASE_URL must use postgresql+psycopg; SQLite is allowed "
                "only in development and test"
            )

    def validate_clerk_configuration(self) -> None:
        """Validate the complete Clerk token-verification configuration."""
        _require_values(
            "Clerk",
            (
                ("CLERK_SECRET_KEY", self.clerk_secret_key),
                ("CLERK_JWT_KEY", self.clerk_jwt_key),
                ("CLERK_ISSUER_URL", self.clerk_issuer_url),
                (
                    "CLERK_AUTHORIZED_PARTIES",
                    ",".join(self.clerk_authorized_parties),
                ),
                ("CLERK_ADMIN_CLAIM", self.clerk_admin_claim),
            ),
        )
        assert self.clerk_jwt_key and self.clerk_issuer_url and self.clerk_admin_claim
        try:
            load_pem_public_key(self.clerk_jwt_key.encode())
        except (TypeError, ValueError):
            raise ConfigurationError(
                "CLERK_JWT_KEY must be a valid PEM-encoded public key"
            ) from None
        _validate_http_url("CLERK_ISSUER_URL", self.clerk_issuer_url, https_only=True)
        for party in self.clerk_authorized_parties:
            _validate_origin(
                "CLERK_AUTHORIZED_PARTIES", party, https_only=self.is_deployed
            )
        if set(self.clerk_authorized_parties) != set(self.cors_allow_origins):
            raise ConfigurationError("CLERK_AUTHORIZED_PARTIES must match CORS_ORIGINS")
        if not self.clerk_secret_key or not self.clerk_secret_key.startswith("sk_"):
            raise ConfigurationError("CLERK_SECRET_KEY has an invalid format")
        if not _CLAIM_NAME_PATTERN.fullmatch(self.clerk_admin_claim):
            raise ConfigurationError("CLERK_ADMIN_CLAIM must be a valid claim name")
        if (
            self.clerk_webhook_signing_secret
            and not self.clerk_webhook_signing_secret.startswith("whsec_")
        ):
            raise ConfigurationError(
                "CLERK_WEBHOOK_SIGNING_SECRET has an invalid format"
            )

    def validate_storage_configuration(self) -> None:
        """Validate the selected object-storage provider and credentials."""
        if self.storage_provider.strip().lower() != DEFAULT_STORAGE_PROVIDER:
            raise ConfigurationError(
                "STORAGE_PROVIDER must be set to a supported provider: gcs"
            )
        _require_values(
            "GCS storage",
            (
                ("GCP_PROJECT_ID", self.gcp_project_id),
                ("GCS_BUCKET_NAME", self.gcs_bucket_name),
                ("GCS_PUBLIC_BASE_URL", self.gcs_public_base_url),
            ),
        )
        assert self.gcs_public_base_url
        _validate_http_url(
            "GCS_PUBLIC_BASE_URL",
            self.gcs_public_base_url,
            https_only=self.is_deployed,
        )
        if self.gcs_public_base_url.endswith("/"):
            raise ConfigurationError(
                "GCS_PUBLIC_BASE_URL must not have a trailing slash"
            )
        bucket_pattern = re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")
        if not self.gcs_bucket_name or not bucket_pattern.fullmatch(
            self.gcs_bucket_name
        ):
            raise ConfigurationError("GCS_BUCKET_NAME has an invalid format")
        if self.normalized_environment != "test" and not (
            self.gcp_service_account_json or self.google_application_credentials
        ):
            raise ConfigurationError(
                "Missing required GCS credentials: set GCP_SERVICE_ACCOUNT_JSON "
                "or GOOGLE_APPLICATION_CREDENTIALS"
            )
        if self.gcp_service_account_json:
            try:
                credential = json.loads(self.gcp_service_account_json)
            except (TypeError, json.JSONDecodeError):
                raise ConfigurationError(
                    "GCP_SERVICE_ACCOUNT_JSON must contain valid JSON"
                ) from None
            required_keys = {
                "type",
                "project_id",
                "private_key",
                "client_email",
                "token_uri",
            }
            if not isinstance(credential, dict) or not required_keys.issubset(
                credential
            ):
                raise ConfigurationError("GCP_SERVICE_ACCOUNT_JSON is incomplete")
            if (
                credential.get("type") != "service_account"
                or credential.get("project_id") != self.gcp_project_id
                or "BEGIN PRIVATE KEY" not in str(credential.get("private_key"))
            ):
                raise ConfigurationError(
                    "GCP_SERVICE_ACCOUNT_JSON does not match the configured GCS provider"
                )
            _validate_http_url(
                "GCP_SERVICE_ACCOUNT_JSON token_uri",
                str(credential["token_uri"]),
                https_only=True,
            )
        if (
            self.is_deployed
            and self.google_application_credentials
            and not Path(self.google_application_credentials).is_absolute()
        ):
            raise ConfigurationError(
                "GOOGLE_APPLICATION_CREDENTIALS must be an absolute path in staging and production"
            )

    def validate_cors_configuration(self) -> None:
        """Validate exact browser origins and deployed wildcard restrictions."""
        _require_values("CORS", (("CORS_ORIGINS", ",".join(self.cors_allow_origins)),))
        for origin in self.cors_allow_origins:
            if origin == "*" and self.is_deployed:
                raise ConfigurationError(
                    "CORS_ORIGINS cannot contain '*' in staging or production"
                )
            if origin != "*":
                _validate_origin("CORS_ORIGINS", origin, https_only=self.is_deployed)

    def validate_integrations(self) -> None:
        """Validate OpenAI and SMTP settings as complete integration groups."""
        if self.openai_timeout_seconds <= 0:
            raise ConfigurationError("OPENAI_TIMEOUT_SECONDS must be greater than zero")
        if self.openai_max_retries < 0:
            raise ConfigurationError("OPENAI_MAX_RETRIES cannot be negative")
        if self.smtp_port is not None and self.smtp_port not in range(1, 65536):
            raise ConfigurationError("SMTP_PORT must be between 1 and 65535")
        smtp_values = (
            self.smtp_host,
            self.smtp_username,
            self.smtp_password,
            self.smtp_from_email,
            self.contact_to_email,
            self.smtp_port,
            self.smtp_use_tls,
        )
        if any(smtp_values):
            if bool(self.smtp_username) != bool(self.smtp_password):
                raise ConfigurationError(
                    "SMTP_USERNAME and SMTP_PASSWORD must be configured together"
                )
            _require_values(
                "SMTP",
                (
                    ("SMTP_HOST", self.smtp_host),
                    ("SMTP_FROM_EMAIL", self.smtp_from_email),
                    ("CONTACT_TO_EMAIL", self.contact_to_email),
                    ("SMTP_PORT", self.smtp_port),
                    ("SMTP_USE_TLS", self.smtp_use_tls),
                ),
            )
        if self.is_deployed:
            _require_values("OpenAI", (("OPENAI_API_KEY", self.openai_api_key),))
            _require_values(
                "SMTP",
                (
                    ("SMTP_HOST", self.smtp_host),
                    ("SMTP_FROM_EMAIL", self.smtp_from_email),
                    ("CONTACT_TO_EMAIL", self.contact_to_email),
                    ("SMTP_PORT", self.smtp_port),
                    ("SMTP_USE_TLS", self.smtp_use_tls),
                ),
            )

    def validate(self) -> None:
        """Run every startup validation before application resources are created."""
        self.validate_environment()
        self.validate_database_configuration()
        self.validate_clerk_configuration()
        self.validate_storage_configuration()
        self.validate_cors_configuration()
        self.validate_integrations()
        if self.package_image_max_upload_bytes <= 0:
            raise ConfigurationError(
                "PACKAGE_IMAGE_MAX_UPLOAD_BYTES must be greater than zero"
            )


@lru_cache
def get_settings() -> Settings:
    """Load and cache the single validated settings instance for this process."""
    settings = Settings.from_env()
    settings.validate()
    return settings
