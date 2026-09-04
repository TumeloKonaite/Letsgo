# LetsGoSouth

LetsGoSouth is a FastAPI backend with a React/Vite public frontend for browsing published South African travel packages.

The authoritative clean-start configuration and secret contract for Modal, Vercel, Clerk, Azure PostgreSQL, GitHub Actions and GCS is [docs/environment-secrets.md](docs/environment-secrets.md). The broader deployment dependency contract is documented in [docs/rebuild-dependencies.md](docs/rebuild-dependencies.md).

## Backend setup

1. Copy [.env.example](/c:/Users/l/Documents/letsgosa/.env.example) to `.env` and adjust the backend settings for your environment.
2. Start the API from the repository root:

```powershell
uv run python -m uvicorn app.main:app --app-dir backend/src --reload
```

The API is served at `http://localhost:8000`, public package routes are available under `/api/packages`, and the database readiness check is exposed at `/health/db`.

SQLite remains the default local fallback when `LETSGOSA_DATABASE_URL` is not set. Production must use PostgreSQL through `LETSGOSA_DATABASE_URL`; see [docs/production-database.md](/c:/Users/l/Documents/letsgosa/docs/production-database.md).
Package images are stored in Google Cloud Storage and the backend expects `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, and `GCS_PUBLIC_BASE_URL` to be configured.
For the Cloud Run deployment flow used in PR 19, including `POST /chat` on the same backend service, see [docs/backend-cloud-run.md](/c:/Users/l/Documents/letsgosa/docs/backend-cloud-run.md).

## Managed PostgreSQL

This project uses Google Cloud SQL PostgreSQL for the managed production database. If you are looking for "RDS" setup notes here, use this Cloud SQL flow instead.

### Local proxy workflow

1. Authenticate `gcloud` and set the project:

```powershell
gcloud auth login
gcloud config set project letsgodb
gcloud auth application-default login
```

2. Start the Cloud SQL Auth Proxy in a dedicated terminal and leave it running. This example uses local port `6543`:

```powershell
cd C:\Users\l\Documents\cloudsql
.\cloud-sql-proxy.exe --port 6543 letsgodb:us-central1:free-trial-first-project
```

3. In a second terminal, point the backend at the proxy:

```powershell
cd C:\Users\l\Documents\letsgosa
$env:LETSGOSA_ENV="production"
$env:LETSGOSA_DATABASE_URL="postgresql+psycopg://letsgodev:YOUR_PASSWORD@127.0.0.1:6543/letsgo?sslmode=disable"
```

4. Run migrations:

```powershell
uv run alembic upgrade head
```

5. Start the backend:

```powershell
uv run python -m uvicorn app.main:app --app-dir backend/src --host 0.0.0.0 --port 8000
```

6. Verify the API is reading from PostgreSQL:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health/db
```

If you need to inspect the tables in Cloud SQL, open `Cloud SQL Studio`, connect to database `letsgo`, and query `information_schema.tables` for schema `public`.

### Cloud Run workflow

Use the backend deployment guide in [docs/backend-cloud-run.md](/c:/Users/l/Documents/letsgosa/docs/backend-cloud-run.md). It covers the Cloud Run service name, region, Cloud SQL attachment, secret-backed database URL, and post-deploy verification for public and admin routes.
That guide also now documents the SMTP Secret Manager and Cloud Run setup required for the `/api/contact` pipeline.

## Frontend setup

1. Copy [frontend/.env.example](/c:/Users/l/Documents/letsgosa/frontend/.env.example) to `frontend/.env`.
2. Install frontend dependencies:

```powershell
cd frontend
npm install
```

3. Start the Vite dev server:

```powershell
npm run dev
```

The frontend reads `VITE_API_BASE_URL` for production and still accepts `VITE_LETSGO_API_BASE_URL` as a legacy alias for local overrides.

## Frontend environment

```env
VITE_API_BASE_URL=https://your-cloud-run-url
```

GitHub Actions injects `VITE_API_BASE_URL` from the repository secret `VITE_API_BASE_URL` during Firebase Hosting deployments. Firebase Hosting config lives in [frontend/firebase.json](/c:/Users/l/Documents/letsgosa/frontend/firebase.json) and [frontend/.firebaserc](/c:/Users/l/Documents/letsgosa/frontend/.firebaserc).

## Frontend hosting

Build and deploy the frontend from the `frontend` directory:

```powershell
npm run build
npx firebase-tools deploy --only hosting --project letsgodb --config firebase.json
```

GitHub Actions workflow [deploy-frontend.yml](/c:/Users/l/Documents/letsgosa/.github/workflows/deploy-frontend.yml) builds the frontend before deploying it to Firebase Hosting. Configure these repository secrets before relying on CI/CD:

- `FIREBASE_SERVICE_ACCOUNT_LETSGODB`
- `VITE_API_BASE_URL`

## Notes

- The backend now allows cross-origin requests from `http://localhost:5173` and `http://127.0.0.1:5173` by default.
- The backend production example includes `https://letsgodb.web.app` and `https://letsgodb.firebaseapp.com` in `CORS_ORIGINS` so the hosted frontend can call Cloud Run.
- `LETSGOSA_CORS_ALLOW_ORIGINS` remains supported as a legacy alias, but `CORS_ORIGINS` is now the preferred variable.
- Run database migrations with `uv run alembic upgrade head` before starting a non-SQLite environment.
- Production should keep the database password in a secret store, not in `.env.example`, the repo, or Cloud Run command history.
