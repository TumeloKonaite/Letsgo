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
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
