import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

os.environ.setdefault("GCP_PROJECT_ID", "letsgodb")
os.environ.setdefault("FIREBASE_PROJECT_ID", "letsgodb")
os.environ.setdefault("FIREBASE_ADMIN_ROLE", "admin")
os.environ.setdefault("GCS_BUCKET_NAME", "letsgosa-package-images")
os.environ.setdefault(
    "GCS_PUBLIC_BASE_URL",
    "https://storage.googleapis.com/letsgosa-package-images",
)

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
