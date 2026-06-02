import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

os.environ.setdefault("KEYCLOAK_SERVER_URL", "https://keycloak.example.com")
os.environ.setdefault("KEYCLOAK_REALM", "letsgosa")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "letsgosa-admin")
os.environ.setdefault("KEYCLOAK_AUDIENCE", "letsgosa-admin")

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
