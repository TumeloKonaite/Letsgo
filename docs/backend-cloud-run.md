# Backend Cloud Run Deployment

This document deploys the FastAPI backend to Cloud Run with:

- project `letsgodb`
- region `us-central1`
- service `letsgosa-backend`
- Cloud SQL instance `letsgodb:us-central1:free-trial-first-project`

The repo includes a root [Dockerfile](/c:/Users/l/Documents/letsgosa/Dockerfile) for Cloud Run source builds. It mirrors [backend/Dockerfile](/c:/Users/l/Documents/letsgosa/backend/Dockerfile), because `gcloud run deploy --source .` only reads a `Dockerfile` from the source root.

## Required runtime configuration

Non-secret runtime variables live in [deploy/cloudrun/backend.env.yaml](/c:/Users/l/Documents/letsgosa/deploy/cloudrun/backend.env.yaml):

```yaml
GOOGLE_CLOUD_PROJECT: letsgodb
FIREBASE_PROJECT_ID: letsgodb
FIREBASE_ADMIN_ROLE: admin
ENVIRONMENT: production
CLOUD_SQL_CONNECTION_NAME: letsgodb:us-central1:free-trial-first-project
```

Store the database URL as a secret, not in Git:

```env
LETSGOSA_DATABASE_URL=postgresql+psycopg://letsgodev:<DB_PASSWORD>@/letsgo?host=/cloudsql/letsgodb:us-central1:free-trial-first-project
```

## One-time secret setup

Create or update the secret that Cloud Run will expose as `LETSGOSA_DATABASE_URL`:

```powershell
$env:LETSGOSA_DATABASE_URL="postgresql+psycopg://letsgodev:<DB_PASSWORD>@/letsgo?host=/cloudsql/letsgodb:us-central1:free-trial-first-project"
$env:LETSGOSA_DATABASE_URL | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create letsgosa-database-url `
  --project letsgodb `
  --data-file=-
```

If the secret already exists, add a new version instead:

```powershell
$env:LETSGOSA_DATABASE_URL | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add letsgosa-database-url `
  --project letsgodb `
  --data-file=-
```

Grant the Cloud Run runtime service account access to the secret before deploying.

## Deploy

Deploy from the repository root:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run deploy letsgosa-backend `
  --source . `
  --region us-central1 `
  --project letsgodb `
  --allow-unauthenticated `
  --port 8080 `
  --add-cloudsql-instances letsgodb:us-central1:free-trial-first-project `
  --env-vars-file deploy/cloudrun/backend.env.yaml `
  --set-secrets LETSGOSA_DATABASE_URL=letsgosa-database-url:latest
```

This deploy uses:

- the repo-root [Dockerfile](/c:/Users/l/Documents/letsgosa/Dockerfile) for the build
- Cloud Run port `8080`
- Cloud SQL Unix socket mounting at `/cloudsql/letsgodb:us-central1:free-trial-first-project`

## Post-deploy verification

Fetch the public service URL:

```powershell
$serviceUrl = & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run services describe letsgosa-backend `
  --region us-central1 `
  --project letsgodb `
  --format="value(status.url)"
```

Verify health:

```powershell
Invoke-WebRequest "$serviceUrl/health"
Invoke-WebRequest "$serviceUrl/health/db"
```

Verify public package routes:

```powershell
Invoke-WebRequest "$serviceUrl/api/packages"
```

Verify admin auth rejects missing or invalid Firebase bearer tokens:

```powershell
Invoke-WebRequest "$serviceUrl/api/admin/packages" -Method GET
Invoke-WebRequest "$serviceUrl/api/admin/packages" -Method GET -Headers @{ Authorization = "Bearer invalid-token" }
```

Verify admin auth accepts a valid Firebase admin token:

```powershell
$headers = @{ Authorization = "Bearer <FIREBASE_ADMIN_ID_TOKEN>" }
Invoke-WebRequest "$serviceUrl/api/admin/auth/me" -Headers $headers
Invoke-WebRequest "$serviceUrl/api/admin/packages" -Headers $headers
```

Expected results:

- `GET /health` returns `200`
- `GET /health/db` returns `200`
- `GET /api/packages` returns `200`
- missing bearer token returns `401`
- invalid token returns `401`
- valid Firebase admin token returns `200`

## Notes

- Do not commit the database password, secret values, or Firebase admin tokens.
- The backend accepts `ENVIRONMENT=production` for Cloud Run and still supports the legacy `LETSGOSA_ENV` name for local compatibility.
- If the database schema is behind, run `alembic upgrade head` against the production database before switching traffic.
