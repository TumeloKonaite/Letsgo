import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "letsgodb")
os.environ.setdefault("FIREBASE_PROJECT_ID", "letsgodb")
os.environ.setdefault("FIREBASE_ADMIN_ROLE", "admin")

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
