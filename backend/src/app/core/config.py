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
PRODUCTION_ENVIRONMENTS = frozenset({"prod", "production"})
DEFAULT_FIREBASE_ADMIN_ROLE = "admin"
DEFAULT_STORAGE_PROVIDER = "minio"
DEFAULT_MINIO_ENDPOINT = "localhost:9000"
DEFAULT_MINIO_ACCESS_KEY = "minioadmin"
DEFAULT_MINIO_SECRET_KEY = "minioadmin"
DEFAULT_MINIO_BUCKET = "package-images"
DEFAULT_MINIO_SECURE = False
DEFAULT_MINIO_REGION = "us-east-1"
DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_CORS_ALLOW_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


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


def _as_csv(value: str | None, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None:
        return default

    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items


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
    google_cloud_project: str | None = None
    firebase_project_id: str | None = None
    firebase_admin_role: str = DEFAULT_FIREBASE_ADMIN_ROLE
    storage_provider: str = DEFAULT_STORAGE_PROVIDER
    minio_endpoint: str = DEFAULT_MINIO_ENDPOINT
    minio_access_key: str = DEFAULT_MINIO_ACCESS_KEY
    minio_secret_key: str = DEFAULT_MINIO_SECRET_KEY
    minio_bucket: str = DEFAULT_MINIO_BUCKET
    minio_secure: bool = DEFAULT_MINIO_SECURE
    minio_region: str = DEFAULT_MINIO_REGION
    package_image_max_upload_bytes: int = DEFAULT_PACKAGE_IMAGE_MAX_UPLOAD_BYTES
    cors_allow_origins: tuple[str, ...] = DEFAULT_CORS_ALLOW_ORIGINS

    @property
    def normalized_environment(self) -> str:
        return self.environment.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.normalized_environment in PRODUCTION_ENVIRONMENTS

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
            google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIREBASE_PROJECT_ID"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"),
            firebase_admin_role=os.getenv("FIREBASE_ADMIN_ROLE", DEFAULT_FIREBASE_ADMIN_ROLE),
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
            cors_allow_origins=_as_csv(
                os.getenv("LETSGOSA_CORS_ALLOW_ORIGINS"),
                default=DEFAULT_CORS_ALLOW_ORIGINS,
            ),
        )

    def validate_firebase_configuration(self) -> None:
        missing = [
            name
            for name, value in (
                ("FIREBASE_PROJECT_ID", self.firebase_project_id),
                ("FIREBASE_ADMIN_ROLE", self.firebase_admin_role),
            )
            if value is None or not value.strip()
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required Firebase configuration: {names}")

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

    def validate_database_configuration(self) -> None:
        database_url = self.database_url.strip()
        if not database_url:
            raise ValueError("LETSGOSA_DATABASE_URL must not be empty")

        if not self.is_production:
            return

        if database_url.startswith("sqlite"):
            raise ValueError(
                "Production requires PostgreSQL via LETSGOSA_DATABASE_URL; "
                "SQLite is only supported for local development and testing"
            )

        if not database_url.startswith("postgresql"):
            raise ValueError(
                "Production LETSGOSA_DATABASE_URL must use a PostgreSQL driver, "
                "for example postgresql+psycopg://USER:PASSWORD@HOST:5432/letsgosa_prod"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
