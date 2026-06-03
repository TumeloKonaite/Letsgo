from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.keycloak import KeycloakJWTValidator
from app.core.config import Settings, get_settings
from app.domain.bookings.service import BookingService
from app.domain.packages.service import PackageService
from app.infrastructure.bookings import PostgresBookingRepository
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from app.infrastructure.packages.postgres_package_repository import PostgresPackageRepository
from app.infrastructure.storage import create_storage_service


def create_application(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.validate_keycloak_configuration()
    resolved_settings.validate_storage_configuration()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_database_engine(resolved_settings.database_url)
        session_factory = create_session_factory(engine)
        initialize_database(engine)

        package_repository = PostgresPackageRepository(session_factory=session_factory)
        booking_repository = PostgresBookingRepository(session_factory=session_factory)
        storage_service = create_storage_service(resolved_settings)
        app.state.settings = resolved_settings
        app.state.db_session_factory = session_factory
        app.state.package_repository = package_repository
        app.state.package_service = PackageService(repository=package_repository)
        app.state.booking_repository = booking_repository
        app.state.booking_service = BookingService(repository=booking_repository)
        app.state.storage_service = storage_service
        app.state.keycloak_auth_service = KeycloakJWTValidator(
            issuer=resolved_settings.keycloak_issuer or "",
            audience=resolved_settings.keycloak_audience or "",
            jwks_url=resolved_settings.keycloak_jwks_url or "",
            timeout_seconds=resolved_settings.keycloak_timeout_seconds,
        )
        app.state.started = True

        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version=resolved_settings.api_version,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_application()
