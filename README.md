# LetsGoSouth

LetsGoSouth is a FastAPI backend with a React/Vite frontend for browsing and administering South African travel packages.

Configuration is environment-driven and validated before the backend starts or the frontend builds. The authoritative variable inventory, ownership rules, and development/staging/production boundaries are in [docs/environment-secrets.md](docs/environment-secrets.md).

## Backend development

1. Copy `backend/.env.example` to `.env` at the repository root.
2. Replace every required placeholder with development-only values. A local `.env` is loaded only when it contains `LETSGOSA_ENV=development`.
3. Start the API:

```sh
uv run python -m uvicorn app.main:app --app-dir backend/src --reload
```

The backend does not use compatibility aliases or deployment fallbacks. `LETSGOSA_DATABASE_URL`, Clerk settings, storage settings, and `CORS_ORIGINS` are required. SQLite is accepted only in development and test; staging and production require PostgreSQL with certificate-verifying TLS. Run migrations before starting against PostgreSQL:

```sh
uv run alembic upgrade head
```

## Frontend development

1. Copy `frontend/.env.example` to `frontend/.env.local`.
2. Install dependencies and start Vite:

```sh
cd frontend
npm ci
npm run dev
```

Development may omit `VITE_API_BASE_URL`, in which case the frontend uses `http://localhost:8000`. Non-development builds require an explicit HTTPS API origin and fail if it is missing or invalid. Clerk browser values are always explicit; only the allowlisted public `VITE_*` names may be exposed.

## Verification

```sh
uv run pytest
uv run ruff check .
uv run ruff format . --check
cd frontend && npm test && npm run build
```

Deployment provisioning is intentionally outside this repository task. See [docs/rebuild-dependencies.md](docs/rebuild-dependencies.md) for the clean-start dependency boundaries.

See [the authentication boundary](docs/authentication.md) for normalized identity
semantics, error responses, and adding another authentication provider.
