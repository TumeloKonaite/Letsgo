from app.core.config import DEFAULT_ENVIRONMENT, Settings


def test_settings_support_environment_alias(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config._load_dotenv", lambda: None)
    monkeypatch.delenv("LETSGOSA_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings.from_env()

    assert settings.environment == "production"
    assert settings.is_production is True


def test_letsgosa_environment_takes_precedence_over_environment_alias(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config._load_dotenv", lambda: None)
    monkeypatch.setenv("LETSGOSA_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings.from_env()

    assert settings.environment == "development"
    assert settings.is_production is False


def test_settings_support_port_alias(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config._load_dotenv", lambda: None)
    monkeypatch.delenv("LETSGOSA_PORT", raising=False)
    monkeypatch.setenv("PORT", "8080")

    settings = Settings.from_env()

    assert settings.port == 8080


def test_settings_use_default_environment_when_no_aliases_are_set(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config._load_dotenv", lambda: None)
    monkeypatch.delenv("LETSGOSA_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    settings = Settings.from_env()

    assert settings.environment == DEFAULT_ENVIRONMENT
