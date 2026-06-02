from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

DEFAULT_APP_NAME = "LetsGoSA API"
DEFAULT_ENVIRONMENT = "development"
DEFAULT_DEBUG = False
DEFAULT_API_PREFIX = "/api"
DEFAULT_API_VERSION = "0.1.0"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_DATABASE_URL = "sqlite:///./letsgosa.db"
DEFAULT_KEYCLOAK_TIMEOUT_SECONDS = 5.0
DEFAULT_STORAGE_PROVIDER = "minio"
DEFAULT_MINIO_ENDPOINT = "localhost:9000"
DEFAULT_MINIO_ACCESS_KEY = "minioadmin"
DEFAULT_MINIO_SECRET_KEY = "minioadmin"
DEFAULT_MINIO_BUCKET = "package-images"
DEFAULT_MINIO_SECURE = False
DEFAULT_MINIO_REGION = "us-east-1"
DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _find_dotenv_path() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_dotenv() -> None:
    dotenv_path = _find_dotenv_path()
    if dotenv_path is None:
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue

        os.environ.setdefault(key, _strip_optional_quotes(value.strip()))


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = DEFAULT_APP_NAME
    environment: str = DEFAULT_ENVIRONMENT
    debug: bool = DEFAULT_DEBUG
    api_prefix: str = DEFAULT_API_PREFIX
    api_version: str = DEFAULT_API_VERSION
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    database_url: str = DEFAULT_DATABASE_URL
    keycloak_issuer: str | None = None
    keycloak_audience: str | None = None
    keycloak_jwks_url: str | None = None
    keycloak_admin_role: str | None = None
    keycloak_timeout_seconds: float = DEFAULT_KEYCLOAK_TIMEOUT_SECONDS
    storage_provider: str = DEFAULT_STORAGE_PROVIDER
    minio_endpoint: str = DEFAULT_MINIO_ENDPOINT
    minio_access_key: str = DEFAULT_MINIO_ACCESS_KEY
    minio_secret_key: str = DEFAULT_MINIO_SECRET_KEY
    minio_bucket: str = DEFAULT_MINIO_BUCKET
    minio_secure: bool = DEFAULT_MINIO_SECURE
    minio_region: str = DEFAULT_MINIO_REGION
    package_image_max_upload_bytes: int = DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        return cls(
            app_name=os.getenv("LETSGOSA_APP_NAME", DEFAULT_APP_NAME),
            environment=os.getenv("LETSGOSA_ENV", DEFAULT_ENVIRONMENT),
            debug=_as_bool(os.getenv("LETSGOSA_DEBUG"), default=DEFAULT_DEBUG),
            api_prefix=os.getenv("LETSGOSA_API_PREFIX", DEFAULT_API_PREFIX),
            api_version=os.getenv("LETSGOSA_API_VERSION", DEFAULT_API_VERSION),
            host=os.getenv("LETSGOSA_HOST", DEFAULT_HOST),
            port=int(os.getenv("LETSGOSA_PORT", str(DEFAULT_PORT))),
            database_url=os.getenv("LETSGOSA_DATABASE_URL", DEFAULT_DATABASE_URL),
            keycloak_issuer=os.getenv("KEYCLOAK_ISSUER"),
            keycloak_audience=os.getenv("KEYCLOAK_AUDIENCE"),
            keycloak_jwks_url=os.getenv("KEYCLOAK_JWKS_URL"),
            keycloak_admin_role=os.getenv("KEYCLOAK_ADMIN_ROLE"),
            keycloak_timeout_seconds=float(
                os.getenv(
                    "KEYCLOAK_TIMEOUT_SECONDS",
                    str(DEFAULT_KEYCLOAK_TIMEOUT_SECONDS),
                )
            ),
            storage_provider=os.getenv("STORAGE_PROVIDER", DEFAULT_STORAGE_PROVIDER),
            minio_endpoint=os.getenv("MINIO_ENDPOINT", DEFAULT_MINIO_ENDPOINT),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", DEFAULT_MINIO_ACCESS_KEY),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", DEFAULT_MINIO_SECRET_KEY),
            minio_bucket=os.getenv("MINIO_BUCKET", DEFAULT_MINIO_BUCKET),
            minio_secure=_as_bool(os.getenv("MINIO_SECURE"), default=DEFAULT_MINIO_SECURE),
            minio_region=os.getenv("MINIO_REGION", DEFAULT_MINIO_REGION),
            package_image_max_upload_bytes=int(
                os.getenv(
                    "PACKAGE_IMAGE_MAX_UPLOAD_BYTES",
                    str(DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES),
                )
            ),
        )

    def validate_keycloak_configuration(self) -> None:
        missing = [
            name
            for name, value in (
                ("KEYCLOAK_ISSUER", self.keycloak_issuer),
                ("KEYCLOAK_AUDIENCE", self.keycloak_audience),
                ("KEYCLOAK_JWKS_URL", self.keycloak_jwks_url),
                ("KEYCLOAK_ADMIN_ROLE", self.keycloak_admin_role),
            )
            if value is None or not value.strip()
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required Keycloak configuration: {names}")

    def validate_storage_configuration(self) -> None:
        provider = self.storage_provider.strip().lower()
        if provider != "minio":
            raise ValueError(f"Unsupported storage provider: {self.storage_provider}")

        missing = [
            name
            for name, value in (
                ("MINIO_ENDPOINT", self.minio_endpoint),
                ("MINIO_ACCESS_KEY", self.minio_access_key),
                ("MINIO_SECRET_KEY", self.minio_secret_key),
                ("MINIO_BUCKET", self.minio_bucket),
            )
            if not value or not value.strip()
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required storage configuration: {names}")


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
