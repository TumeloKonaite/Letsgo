from dataclasses import dataclass
from functools import lru_cache
import os

DEFAULT_APP_NAME = "LetsGoSA API"
DEFAULT_ENVIRONMENT = "development"
DEFAULT_DEBUG = False
DEFAULT_API_PREFIX = "/api"
DEFAULT_API_VERSION = "0.1.0"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_DATABASE_URL = "sqlite:///./letsgosa.db"
DEFAULT_KEYCLOAK_TIMEOUT_SECONDS = 5.0


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
    keycloak_server_url: str | None = None
    keycloak_realm: str | None = None
    keycloak_client_id: str | None = None
    keycloak_audience: str | None = None
    keycloak_timeout_seconds: float = DEFAULT_KEYCLOAK_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("LETSGOSA_APP_NAME", DEFAULT_APP_NAME),
            environment=os.getenv("LETSGOSA_ENV", DEFAULT_ENVIRONMENT),
            debug=_as_bool(os.getenv("LETSGOSA_DEBUG"), default=DEFAULT_DEBUG),
            api_prefix=os.getenv("LETSGOSA_API_PREFIX", DEFAULT_API_PREFIX),
            api_version=os.getenv("LETSGOSA_API_VERSION", DEFAULT_API_VERSION),
            host=os.getenv("LETSGOSA_HOST", DEFAULT_HOST),
            port=int(os.getenv("LETSGOSA_PORT", str(DEFAULT_PORT))),
            database_url=os.getenv("LETSGOSA_DATABASE_URL", DEFAULT_DATABASE_URL),
            keycloak_server_url=os.getenv("KEYCLOAK_SERVER_URL"),
            keycloak_realm=os.getenv("KEYCLOAK_REALM"),
            keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
            keycloak_audience=os.getenv("KEYCLOAK_AUDIENCE"),
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
                ("KEYCLOAK_SERVER_URL", self.keycloak_server_url),
                ("KEYCLOAK_REALM", self.keycloak_realm),
                ("KEYCLOAK_CLIENT_ID", self.keycloak_client_id),
                ("KEYCLOAK_AUDIENCE", self.keycloak_audience),
            )
            if value is None or not value.strip()
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required Keycloak configuration: {names}")


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
