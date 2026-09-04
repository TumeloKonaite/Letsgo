from __future__ import annotations

from pathlib import Path

from app.core.dependencies import get_twin_service
from app.main import create_application
from fastapi.testclient import TestClient

from tests.api.firebase_auth_helpers import build_test_settings


def _create_chatbot_data_dir(base_dir: Path) -> Path:
    data_dir = base_dir / "chatbot-data"
    data_dir.mkdir()
    (data_dir / "twin_profile.json").write_text(
        '{"name":"Tumelo","full_name":"Tumelo Tshana Konaite"}',
        encoding="utf-8",
    )
    (data_dir / "summary.txt").write_text("Summary", encoding="utf-8")
    (data_dir / "style.txt").write_text("Style", encoding="utf-8")
    (data_dir / "fallback_personality.txt").write_text(
        "Fallback personality",
        encoding="utf-8",
    )
    return data_dir


def test_chat_endpoint_is_exposed_at_service_root(tmp_path: Path) -> None:
    data_dir = _create_chatbot_data_dir(tmp_path)
    application = create_application(
        settings=build_test_settings(
            f"sqlite:///{tmp_path / 'chat-root.db'}",
            chatbot_content_data_dir=data_dir,
            chatbot_conversation_storage_dir=data_dir / "conversations",
            cors_allow_origins=("https://letsgodb.web.app",),
            openai_api_key=None,
        )
    )

    with TestClient(application) as client:
        response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Chat service is unavailable."}


def test_chat_endpoint_allows_firebase_origin_at_service_root(tmp_path: Path) -> None:
    data_dir = _create_chatbot_data_dir(tmp_path)
    application = create_application(
        settings=build_test_settings(
            f"sqlite:///{tmp_path / 'chat-cors.db'}",
            chatbot_content_data_dir=data_dir,
            chatbot_conversation_storage_dir=data_dir / "conversations",
            cors_allow_origins=("https://letsgodb.web.app",),
        )
    )

    with TestClient(application) as client:
        response = client.options(
            "/chat",
            headers={
                "Origin": "https://letsgodb.web.app",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://letsgodb.web.app"


def test_chat_returns_safe_500_without_leaking_exception_details(
    tmp_path: Path,
) -> None:
    data_dir = _create_chatbot_data_dir(tmp_path)
    application = create_application(
        settings=build_test_settings(
            f"sqlite:///{tmp_path / 'chat-error.db'}",
            chatbot_content_data_dir=data_dir,
            chatbot_conversation_storage_dir=data_dir / "conversations",
            cors_allow_origins=("https://letsgodb.web.app",),
            openai_api_key="test-key",
        )
    )

    class BrokenTwinService:
        def chat(self, user_message: str, session_id: str | None = None):
            raise RuntimeError("OPENAI_API_KEY=test-key should never leak")

    application.dependency_overrides[get_twin_service] = lambda: BrokenTwinService()

    with TestClient(application) as client:
        response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Chat request failed."}
