from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.domain.packages.service import PackageService
from app.infrastructure.packages.in_memory_package_repository import (
    InMemoryPackageRepository,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    repository = InMemoryPackageRepository()
    app.state.settings = settings
    app.state.package_service = PackageService(repository=repository)
    app.state.started = True
    yield


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version=settings.api_version,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_application()
