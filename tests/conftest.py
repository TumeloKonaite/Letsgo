import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

os.environ.setdefault("LETSGOSA_ENV", "test")
os.environ.setdefault("LETSGOSA_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("CLERK_SECRET_KEY", "sk_test_synthetic")
os.environ.setdefault(
    "CLERK_JWT_KEY",
    """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA5nhAUsF4yGsMxkuAnXMX
yzHzrpah8+DlwvHp8nifUbbfbWe5n1RXimcCEKnrcwxOqh0C2mWjpXl1eSZUIBuY
CU4ikpI1O3vb7wY2wpYGDR9Adw2BGKpo/+NKA6uUiWRhj24YN/P5PuctqrNRnRRg
q3S9BOu9zy7ce82VJ5o0tPVUsTsQ3TtzcLDvZtCfJewY5JbjEao1t3ZIGGkFJW+z
4vsc+dEdhHvh5L8dOEPxUoH+YTx0GfO1PJQOyT+B+IkvRyhlgUYVprMTwmKI2/xj
iD80dQjQOIQJW8nX7TLOZdFpUhdbzQXj/hTDAXECnCRka9NLDxPmWxPvrQC4n2k1
gQIDAQAB
-----END PUBLIC KEY-----""",
)
os.environ.setdefault("CLERK_ISSUER_URL", "https://clerk.example.invalid")
os.environ.setdefault("CLERK_AUTHORIZED_PARTIES", "http://localhost:5173")
os.environ.setdefault("CLERK_ADMIN_CLAIM", "admin")
os.environ.setdefault("STORAGE_PROVIDER", "gcs")
os.environ.setdefault("GCS_OBJECT_PREFIX", "staging/")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GCS_BUCKET_NAME", "test-package-images")
os.environ.setdefault("GCS_PUBLIC_BASE_URL", "https://storage.example.invalid/images")

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
