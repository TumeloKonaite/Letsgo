# Production Database

LetsGoSA uses:

- PostgreSQL in production
- SQLite only for local development and automated tests when `LETSGOSA_DATABASE_URL` is not set

If `LETSGOSA_ENV` is `production` or `prod`, the backend now rejects SQLite and requires a PostgreSQL `LETSGOSA_DATABASE_URL`.

## Cloud SQL provisioning

Replace the placeholder values before running these commands:

```powershell
$env:PROJECT_ID="your-gcp-project"
$env:REGION="your-gcp-region"
$env:INSTANCE_NAME="letsgosa-prod-pg"
$env:DB_VERSION="POSTGRES_16"
$env:TIER="db-custom-1-3840"
$env:DB_NAME="letsgosa_prod"
$env:DB_USER="letsgosa_app"
```

Create the Cloud SQL PostgreSQL instance:

```powershell
gcloud sql instances create $env:INSTANCE_NAME `
  --project $env:PROJECT_ID `
  --database-version $env:DB_VERSION `
  --cpu 1 `
  --memory 3840MiB `
  --region $env:REGION `
  --storage-size 20GB `
  --storage-type SSD `
  --availability-type zonal `
  --backup-start-time 02:00
```

Create the production database:

```powershell
gcloud sql databases create $env:DB_NAME `
  --project $env:PROJECT_ID `
  --instance $env:INSTANCE_NAME
```

Create the application database user and let Google generate a password:

```powershell
gcloud sql users create $env:DB_USER `
  --project $env:PROJECT_ID `
  --instance $env:INSTANCE_NAME `
  --password "$(openssl rand -base64 24)"
```

If `openssl` is not available, generate a password with your normal secret-management workflow instead. Do not commit it to the repository.

Fetch the instance connection name and public IP when wiring deployment:

```powershell
gcloud sql instances describe $env:INSTANCE_NAME `
  --project $env:PROJECT_ID `
  --format="value(connectionName,ipAddresses[0].ipAddress)"
```

## Application configuration

Production deployments must set:

```env
LETSGOSA_ENV=production
LETSGOSA_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/letsgosa_prod
```

The backend accepts SQLAlchemy PostgreSQL URLs using the `psycopg` driver, including the standard Cloud SQL host form above.

## Migrations

Install dependencies and run Alembic before starting the API in any non-SQLite environment:

```powershell
uv sync
$env:LETSGOSA_ENV="production"
$env:LETSGOSA_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:5432/letsgosa_prod"
uv run alembic upgrade head
```

The initial Alembic revision creates these tables:

- `packages`
- `package_images`
- `package_itinerary_items`
- `package_availability`
- `bookings`

If those tables are missing, the backend now fails fast at startup and tells you to run `alembic upgrade head`.

## Verification

Verify the schema directly:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'packages',
    'package_images',
    'package_itinerary_items',
    'package_availability',
    'bookings'
  )
ORDER BY table_name;
```

Start the backend with the production URL after migrations:

```powershell
uv run python -m uvicorn app.main:app --app-dir backend/src --host 0.0.0.0 --port 8000
```

Then verify:

- `GET /api/packages` reads published package data from PostgreSQL
- `POST /api/admin/packages`, `PATCH /api/admin/packages/{id}`, and `DELETE /api/admin/packages/{id}` create, update, and delete PostgreSQL-backed data

Use deployment secrets or your platform secret manager for `LETSGOSA_DATABASE_URL`. Do not store database credentials in Git.
