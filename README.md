# LetsGoSouth

LetsGoSouth is a FastAPI backend with a React/Vite public frontend for browsing published South African travel packages.

## Backend setup

1. Copy [.env.example](/c:/Users/l/Documents/letsgosa/.env.example) to `.env` and adjust the backend settings for your environment.
2. Start the API from the repository root:

```powershell
uv run python -m uvicorn app.main:app --app-dir backend/src --reload
```

The API is served at `http://localhost:8000`, and public package routes are available under `/api/packages`.

SQLite remains the default local fallback when `LETSGOSA_DATABASE_URL` is not set. Production must use PostgreSQL through `LETSGOSA_DATABASE_URL`; see [docs/production-database.md](/c:/Users/l/Documents/letsgosa/docs/production-database.md).

## Managed PostgreSQL

This project uses Google Cloud SQL PostgreSQL for the managed production database. If you are looking for "RDS" setup notes here, use this Cloud SQL flow instead.

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
Invoke-WebRequest http://127.0.0.1:8000/api/packages
```

If you need to inspect the tables in Cloud SQL, open `Cloud SQL Studio`, connect to database `letsgo`, and query `information_schema.tables` for schema `public`.

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

The frontend reads `VITE_LETSGO_API_BASE_URL` and defaults to `http://localhost:8000` in the example file.

## Frontend environment

```env
VITE_LETSGO_API_BASE_URL=http://localhost:8000
```

## Notes

- The backend now allows cross-origin requests from `http://localhost:5173` and `http://127.0.0.1:5173` by default.
- Change `LETSGOSA_CORS_ALLOW_ORIGINS` in the root `.env` if you need different frontend origins.
- Run database migrations with `uv run alembic upgrade head` before starting a non-SQLite environment.
