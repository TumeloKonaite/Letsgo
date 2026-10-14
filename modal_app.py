"""Deploy production with: modal deploy --env production modal_app.py."""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
app = modal.App("letsgosa-backend-production")

# Modal includes this entrypoint module, while application source and content
# resources are added explicitly below. Runtime values come from environment-
# scoped Modal Secrets; no local .env or credential file is copied.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ca-certificates")
    .pip_install_from_requirements(str(ROOT / "backend/requirements.txt"))
    .env(
        {
            "PYTHONPATH": "/app/backend/src",
            "CONTENT_DATA_DIR": "/app/data",
            "CONVERSATION_STORAGE_DIR": "/tmp/letsgosa-conversations",
            "LETSGOSA_DEPLOYMENT_REVISION": "2026-10-14-database-secret-fix",
        }
    )
)
for source in sorted((ROOT / "backend/src/app").rglob("*.py")):
    image = image.add_local_file(
        str(source), "/app/" + source.relative_to(ROOT).as_posix()
    )
for filename in (
    "fallback_personality.txt",
    "linkedin.pdf",
    "style.txt",
    "summary.txt",
    "twin_profile.json",
):
    image = image.add_local_file(str(ROOT / "data" / filename), f"/app/data/{filename}")

# The runtime group holds CORS and other non-secret application settings.
# Migration credentials are deliberately not attached to the web function.
secrets = [
    modal.Secret.from_name(name, environment_name="production")
    for name in (
        "letsgosa-runtime-production",
        "letsgosa-database-production-runtime",
        "letsgosa-clerk-production",
        "letsgosa-gcs-production",
        "letsgosa-openai-production",
        "letsgosa-smtp-production",
    )
]


@app.function(
    image=image, secrets=secrets, min_containers=0, max_containers=3, timeout=120
)
@modal.asgi_app()
def web():
    import os

    # Never accidentally launch development defaults in the production app.
    os.environ["LETSGOSA_ENV"] = "production"
    from app.main import app as application

    return application
