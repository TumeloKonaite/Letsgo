"""Deploy staging with: modal deploy --env staging modal_app.py."""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
app = modal.App("letsgosa-backend-staging", include_source=False)

# Only explicit non-secret constants enter the image. Runtime values come from
# environment-scoped Modal Secrets; never copy the checkout or a local .env.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(ROOT / "backend/requirements.txt"))
    .env(
        {
            "PYTHONPATH": "/app/backend/src",
            "CONTENT_DATA_DIR": "/app/data",
            "CONVERSATION_STORAGE_DIR": "/tmp/letsgosa-conversations",
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
    modal.Secret.from_name(name, environment_name="staging")
    for name in (
        "letsgosa-runtime-staging",
        "letsgosa-database-staging-runtime",
        "letsgosa-clerk-staging",
        "letsgosa-gcs-staging",
        "letsgosa-openai-staging",
        "letsgosa-smtp-staging",
    )
]


@app.function(
    image=image, secrets=secrets, min_containers=0, max_containers=1, timeout=120
)
@modal.asgi_app()
def web():
    import os

    # Never accidentally launch development defaults in the staging app.
    os.environ["LETSGOSA_ENV"] = "staging"
    from app.main import app as application

    return application
