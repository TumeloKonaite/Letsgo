from pathlib import Path

from app.core import config


def test_load_dotenv_sets_missing_environment_values(monkeypatch, tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "KEYCLOAK_ISSUER=http://localhost:8080/realms/letsgosa",
                "KEYCLOAK_AUDIENCE=letsgosa-admin",
                'KEYCLOAK_ADMIN_ROLE="admin"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("KEYCLOAK_ISSUER", raising=False)
    monkeypatch.delenv("KEYCLOAK_AUDIENCE", raising=False)
    monkeypatch.delenv("KEYCLOAK_ADMIN_ROLE", raising=False)
    monkeypatch.setattr(config, "_find_dotenv_path", lambda: dotenv_path)

    config._load_dotenv()

    assert config.os.environ["KEYCLOAK_ISSUER"] == "http://localhost:8080/realms/letsgosa"
    assert config.os.environ["KEYCLOAK_AUDIENCE"] == "letsgosa-admin"
    assert config.os.environ["KEYCLOAK_ADMIN_ROLE"] == "admin"


def test_load_dotenv_does_not_override_existing_environment_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "KEYCLOAK_ADMIN_ROLE=admin\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("KEYCLOAK_ADMIN_ROLE", "super-admin")
    monkeypatch.setattr(config, "_find_dotenv_path", lambda: dotenv_path)

    config._load_dotenv()

    assert config.os.environ["KEYCLOAK_ADMIN_ROLE"] == "super-admin"
