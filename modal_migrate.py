"""Run production Alembic migrations as a one-off Modal job."""

import subprocess
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
app = modal.App("letsgosa-database-migrations-production")

# Package only the migration configuration, revisions, and application model code
# Alembic needs. Database credentials are attached to the function at runtime.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ca-certificates")
    .pip_install_from_requirements(str(ROOT / "backend/requirements.txt"))
    .env(
        {
            "PYTHONPATH": "/app/backend/src",
            "LETSGOSA_ENV": "production",
        }
    )
    .add_local_file(str(ROOT / "alembic.ini"), "/app/alembic.ini")
)
for source in sorted((ROOT / "backend/src/app").rglob("*.py")):
    image = image.add_local_file(
        str(source), "/app/" + source.relative_to(ROOT).as_posix()
    )
for source in sorted((ROOT / "alembic").rglob("*.py")):
    image = image.add_local_file(
        str(source), "/app/" + source.relative_to(ROOT).as_posix()
    )
image = image.add_local_file(
    str(ROOT / "alembic/script.py.mako"), "/app/alembic/script.py.mako"
)

migration_secret = modal.Secret.from_name(
    "letsgosa-database-production-migration",
    environment_name="production",
)


@app.function(image=image, secrets=[migration_secret], timeout=600)
def migrate() -> None:
    """Upgrade the production schema to the repository's current head revision."""
    subprocess.run(
        ["alembic", "-c", "/app/alembic.ini", "upgrade", "head"],
        cwd="/app",
        check=True,
    )


@app.local_entrypoint()
def main() -> None:
    migrate.remote()
