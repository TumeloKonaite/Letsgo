from dataclasses import dataclass
from functools import lru_cache
import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "LetsGoSA API"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    api_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("LETSGOSA_APP_NAME", cls.app_name),
            environment=os.getenv("LETSGOSA_ENV", cls.environment),
            debug=_as_bool(os.getenv("LETSGOSA_DEBUG"), default=cls.debug),
            api_prefix=os.getenv("LETSGOSA_API_PREFIX", cls.api_prefix),
            api_version=os.getenv("LETSGOSA_API_VERSION", cls.api_version),
            host=os.getenv("LETSGOSA_HOST", cls.host),
            port=int(os.getenv("LETSGOSA_PORT", str(cls.port))),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
