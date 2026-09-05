from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from app.core import config

TEST_JWT_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5nhAUsF4yGsMxkuAnXMX
yzHzrpah8+DlwvHp8nifUbbfbWe5n1RXimcCEKnrcwxOqh0C2mWjpXl1eSZUIBuY
CU4ikpI1O3vb7wY2wpYGDR9Adw2BGKpo/+NKA6uUiWRhj24YN/P5PuctqrNRnRRg
q3S9BOu9zy7ce82VJ5o0tPVUsTsQ3TtzcLDvZtCfJewY5JbjEao1t3ZIGGkFJW+z
4vsc+dEdhHvh5L8dOEPxUoH+YTx0GfO1PJQOyT+B+IkvRyhlgUYVprMTwmKI2/xj
iD80dQjQOIQJW8nX7TLOZdFpUhdbzQXj/hTDAXECnCRka9NLDxPmWxPvrQC4n2k1
gQIDAQAB
-----END PUBLIC KEY-----"""


def valid_settings(**overrides) -> config.Settings:
    values = {
        "environment": "test",
        "database_url": "sqlite:///:memory:",
        "cors_allow_origins": ("http://localhost:5173",),
        "clerk_secret_key": "sk_test_synthetic",
        "clerk_jwt_key": TEST_JWT_KEY,
        "clerk_issuer_url": "https://clerk.example.invalid",
        "clerk_authorized_parties": ("http://localhost:5173",),
        "clerk_admin_claim": "admin",
        "storage_provider": "gcs",
        "gcp_project_id": "test-project",
        "gcs_bucket_name": "test-images",
        "gcs_object_prefix": "staging/",
        "gcs_public_base_url": "https://storage.example.invalid/images",
    }
    values.update(overrides)
    return config.Settings(**values)


def production_settings(**overrides) -> config.Settings:
    settings = replace(
        valid_settings(),
        environment="production",
        database_url=(
            "postgresql+psycopg://app:synthetic@db.example.invalid:5432/letsgosa"
            "?sslmode=verify-full"
        ),
        cors_allow_origins=("https://travel.example.invalid",),
        clerk_authorized_parties=("https://travel.example.invalid",),
        google_application_credentials="/run/secrets/gcs-credentials.json",
        openai_api_key="synthetic-openai-key",
        smtp_host="smtp.example.invalid",
        smtp_port=587,
        smtp_from_email="sender@example.invalid",
        contact_to_email="contact@example.invalid",
        smtp_use_tls=True,
    )
    return replace(settings, **overrides)


def test_load_dotenv_sets_missing_values_for_explicit_development_file(
    monkeypatch, tmp_path: Path
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "LETSGOSA_ENV=development\nCLERK_ADMIN_CLAIM=admin\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LETSGOSA_ENV", raising=False)
    monkeypatch.delenv("CLERK_ADMIN_CLAIM", raising=False)
    monkeypatch.setattr(config, "_find_dotenv_path", lambda: dotenv_path)

    config._load_dotenv()

    assert config.os.environ["LETSGOSA_ENV"] == "development"
    assert config.os.environ["CLERK_ADMIN_CLAIM"] == "admin"


def test_dotenv_is_not_loaded_for_production(monkeypatch, tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "LETSGOSA_ENV=development\nCLERK_SECRET_KEY=must-not-load\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LETSGOSA_ENV", "production")
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.setattr(config, "_find_dotenv_path", lambda: dotenv_path)

    config._load_dotenv()

    assert "CLERK_SECRET_KEY" not in config.os.environ


def test_settings_parse_canonical_environment_variables(monkeypatch) -> None:
    monkeypatch.setattr(config, "_load_dotenv", lambda: None)
    monkeypatch.setenv("LETSGOSA_ENV", "development")
    monkeypatch.setenv("LETSGOSA_DATABASE_URL", "sqlite:///./local.db")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, http://127.0.0.1:5173")

    settings = config.Settings.from_env()

    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///./local.db"
    assert settings.cors_allow_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def test_development_cors_default_is_never_applied_to_production(monkeypatch) -> None:
    monkeypatch.setattr(config, "_load_dotenv", lambda: None)
    monkeypatch.setenv("LETSGOSA_ENV", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = config.Settings.from_env()

    assert settings.cors_allow_origins == ()


def test_retired_environment_and_database_aliases_are_ignored(monkeypatch) -> None:
    monkeypatch.setattr(config, "_load_dotenv", lambda: None)
    monkeypatch.delenv("LETSGOSA_ENV", raising=False)
    monkeypatch.delenv("LETSGOSA_DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://legacy:secret@legacy.invalid/app")

    settings = config.Settings.from_env()

    assert settings.environment == ""
    assert settings.database_url == ""


def test_environment_identifier_is_required() -> None:
    with pytest.raises(config.ConfigurationError, match="LETSGOSA_ENV"):
        replace(valid_settings(), environment="").validate_environment()


def test_valid_production_configuration_passes() -> None:
    production_settings().validate()


def test_production_requires_explicit_database_url() -> None:
    with pytest.raises(config.ConfigurationError, match="LETSGOSA_DATABASE_URL"):
        production_settings(database_url="").validate()


@pytest.mark.parametrize(
    "database_url",
    (
        "not a database url",
        "mysql://user:password@db.example.invalid/app",
        "postgresql+unsupported://user:password@db.example.invalid/app?sslmode=verify-full",
        "postgresql+psycopg://user:password@db.example.invalid:not-a-port/app?sslmode=verify-full",
        "postgresql+psycopg://db.example.invalid/app",
        "postgresql+psycopg://user:password@db.example.invalid/app",
    ),
)
def test_production_rejects_malformed_or_unsafe_database_urls(
    database_url: str,
) -> None:
    with pytest.raises(config.ConfigurationError):
        production_settings(database_url=database_url).validate_database_configuration()


def test_incomplete_clerk_configuration_is_rejected() -> None:
    with pytest.raises(config.ConfigurationError, match="CLERK_JWT_KEY"):
        replace(valid_settings(), clerk_jwt_key=None).validate_clerk_configuration()


def test_malformed_clerk_issuer_is_rejected_without_echoing_secret() -> None:
    secret = "sk_live_do-not-log-this"
    settings = replace(
        valid_settings(), clerk_secret_key=secret, clerk_issuer_url="not-a-url"
    )

    with pytest.raises(config.ConfigurationError) as caught:
        settings.validate_clerk_configuration()

    assert secret not in str(caught.value)


def test_settings_repr_redacts_secret_bearing_values() -> None:
    settings = replace(
        valid_settings(),
        database_url="postgresql://user:database-secret@db.example.invalid/app",
        clerk_secret_key="clerk-secret",
        clerk_jwt_key="jwt-secret",
        clerk_webhook_signing_secret="webhook-secret",
        gcp_service_account_json="storage-secret",
        smtp_password="smtp-secret",
        openai_api_key="openai-secret",
    )

    rendered = repr(settings)

    for secret in (
        "database-secret",
        "clerk-secret",
        "jwt-secret",
        "webhook-secret",
        "storage-secret",
        "smtp-secret",
        "openai-secret",
    ):
        assert secret not in rendered


def test_incomplete_storage_configuration_is_rejected() -> None:
    with pytest.raises(config.ConfigurationError, match="GCS_BUCKET_NAME"):
        replace(valid_settings(), gcs_bucket_name=None).validate_storage_configuration()


def test_production_storage_requires_explicit_credentials() -> None:
    with pytest.raises(config.ConfigurationError, match="GCS credentials"):
        production_settings(
            google_application_credentials=None,
            gcp_service_account_json=None,
        ).validate_storage_configuration()


def test_invalid_service_account_json_is_rejected_without_echoing_it() -> None:
    secret = '{"private_key":"do-not-log"'
    settings = replace(valid_settings(), gcp_service_account_json=secret)

    with pytest.raises(config.ConfigurationError) as caught:
        settings.validate_storage_configuration()

    assert secret not in str(caught.value)
    assert "do-not-log" not in str(caught.value)


@pytest.mark.parametrize("environment", ("staging", "production"))
def test_deployed_cors_rejects_wildcards(environment: str) -> None:
    settings = replace(
        production_settings(), environment=environment, cors_allow_origins=("*",)
    )

    with pytest.raises(config.ConfigurationError, match="cannot contain '\\*'"):
        settings.validate_cors_configuration()


def test_deployed_cors_rejects_paths_and_insecure_origins() -> None:
    with pytest.raises(config.ConfigurationError):
        replace(
            production_settings(),
            cors_allow_origins=("https://travel.example.invalid/admin",),
        ).validate_cors_configuration()
    with pytest.raises(config.ConfigurationError):
        replace(
            production_settings(),
            cors_allow_origins=("http://travel.example.invalid",),
        ).validate_cors_configuration()


def test_partial_smtp_credentials_are_rejected() -> None:
    with pytest.raises(config.ConfigurationError, match="configured together"):
        replace(
            valid_settings(), smtp_username="mailer", smtp_password=None
        ).validate_integrations()


@pytest.mark.parametrize(
    "prefix", ["", "/staging/", "staging", "staging/../", "staging//"]
)
def test_storage_prefix_validation(prefix):
    with pytest.raises(config.ConfigurationError):
        replace(
            valid_settings(), gcs_object_prefix=prefix
        ).validate_storage_configuration()


def test_federation_configuration():
    settings = replace(
        valid_settings(),
        google_application_credentials=None,
        gcs_wif_audience="//iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/modal/providers/staging",
        gcs_service_account_email="modal-staging@test-project.iam.gserviceaccount.com",
    )
    settings.validate_storage_configuration()
    with pytest.raises(config.ConfigurationError, match="exactly one"):
        replace(
            settings, google_application_credentials="/run/secrets/credentials.json"
        ).validate_storage_configuration()
