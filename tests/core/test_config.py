from pathlib import Path

from app.core import config
import pytest


def test_load_dotenv_sets_missing_environment_values(monkeypatch, tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "GOOGLE_CLOUD_PROJECT=letsgodb",
                "FIREBASE_PROJECT_ID=letsgodb",
                'FIREBASE_ADMIN_ROLE="admin"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("FIREBASE_ADMIN_ROLE", raising=False)
    monkeypatch.setattr(config, "_find_dotenv_path", lambda: dotenv_path)

    config._load_dotenv()

    assert config.os.environ["GOOGLE_CLOUD_PROJECT"] == "letsgodb"
    assert config.os.environ["FIREBASE_PROJECT_ID"] == "letsgodb"
    assert config.os.environ["FIREBASE_ADMIN_ROLE"] == "admin"


def test_load_dotenv_does_not_override_existing_environment_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "FIREBASE_ADMIN_ROLE=admin\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FIREBASE_ADMIN_ROLE", "super-admin")
    monkeypatch.setattr(config, "_find_dotenv_path", lambda: dotenv_path)

    config._load_dotenv()

    assert config.os.environ["FIREBASE_ADMIN_ROLE"] == "super-admin"


def test_settings_parse_cors_origins_from_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "LETSGOSA_CORS_ALLOW_ORIGINS",
        "http://localhost:5173, https://letsgosouth.africa ,http://127.0.0.1:4173",
    )

    settings = config.Settings.from_env()

    assert settings.cors_allow_origins == (
        "http://localhost:5173",
        "https://letsgosouth.africa",
        "http://127.0.0.1:4173",
    )


def test_production_settings_reject_sqlite_database_urls() -> None:
    settings = config.Settings(
        environment="production",
        database_url="sqlite:///./letsgosa.db",
    )

    with pytest.raises(
        ValueError,
        match="Production requires PostgreSQL via LETSGOSA_DATABASE_URL",
    ):
        settings.validate_database_configuration()


def test_production_settings_accept_postgresql_psycopg_database_urls() -> None:
    settings = config.Settings(
        environment="production",
        database_url="postgresql+psycopg://user:password@db.example.com:5432/letsgosa_prod",
    )

    settings.validate_database_configuration()


def test_non_production_settings_allow_sqlite_fallback() -> None:
    settings = config.Settings()

    settings.validate_database_configuration()
    assert settings.database_url == config.DEFAULT_DATABASE_URL
