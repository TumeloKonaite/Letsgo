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


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
