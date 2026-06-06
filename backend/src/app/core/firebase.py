from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import Settings

if TYPE_CHECKING:
    from firebase_admin import App
else:
    App = Any


def _firebase_app_name(settings: Settings) -> str:
    project_id = settings.firebase_project_id or "default"
    return f"letsgosa-{project_id}"


def initialize_firebase_app(settings: Settings) -> App:
    from firebase_admin import credentials, get_app, initialize_app

    app_name = _firebase_app_name(settings)
    try:
        return get_app(app_name)
    except ValueError:
        return initialize_app(
            credential=credentials.ApplicationDefault(),
            options={"projectId": settings.firebase_project_id},
            name=app_name,
        )
