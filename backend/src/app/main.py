from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.firebase_auth import FirebaseAuthService
from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.firebase import initialize_firebase_app
from app.domain.contact.service import ContactService
from app.domain.bookings.service import BookingService
from app.domain.packages.service import PackageService
from app.infrastructure.contact import build_contact_repository
from app.infrastructure.bookings import PostgresBookingRepository
from app.infrastructure.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from app.infrastructure.email.smtp_email_sender import SMTPEmailSender
from app.infrastructure.packages.postgres_package_repository import (
    PostgresPackageRepository,
)
from app.infrastructure.storage import create_storage_service


def create_application(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_settings.validate_database_configuration()
    resolved_settings.validate_firebase_configuration()
    resolved_settings.validate_storage_configuration()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_database_engine(resolved_settings.database_url)
        session_factory = create_session_factory(engine)
        initialize_database(engine)

        package_repository = PostgresPackageRepository(session_factory=session_factory)
        booking_repository = PostgresBookingRepository(session_factory=session_factory)
        contact_repository = build_contact_repository(session_factory=session_factory)
        contact_email_sender = SMTPEmailSender(
            host=resolved_settings.smtp_host,
            port=resolved_settings.smtp_port,
            username=resolved_settings.smtp_username,
            password=resolved_settings.smtp_password,
            from_email=resolved_settings.smtp_from_email,
            to_email=resolved_settings.contact_to_email,
            use_tls=resolved_settings.smtp_use_tls,
        )
        storage_service = create_storage_service(resolved_settings)
        app.state.settings = resolved_settings
        app.state.db_session_factory = session_factory
        app.state.package_repository = package_repository
        app.state.package_service = PackageService(
            repository=package_repository,
            storage_service=storage_service,
        )
        app.state.booking_repository = booking_repository
        app.state.booking_service = BookingService(repository=booking_repository)
        app.state.contact_repository = contact_repository
        app.state.contact_email_sender = contact_email_sender
        app.state.contact_service = ContactService(
            email_sender=contact_email_sender,
            repository=contact_repository,
        )
        app.state.storage_service = storage_service
        app.state.firebase_auth_service = FirebaseAuthService(
            app_factory=lambda: initialize_firebase_app(resolved_settings)
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
    if resolved_settings.cors_allow_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors_allow_origins),
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_application()
