# Backend Cloud Run Deployment

This document covers the backend production deploy path for:

- project `letsgodb`
- region `us-central1`
- service `letsgosa-backend`
- Artifact Registry repository `letsgosa`

The repo now deploys the backend through GitHub Actions in [.github/workflows/deploy-backend.yml](/c:/Users/l/Documents/letsgosa/.github/workflows/deploy-backend.yml). The workflow authenticates with Workload Identity Federation, reads the production database URL from Secret Manager, runs `alembic upgrade head`, builds the repo-root [Dockerfile](/c:/Users/l/Documents/letsgosa/Dockerfile), pushes the image to Artifact Registry, deploys that image to Cloud Run, and verifies `GET /health`.

## GitHub configuration

Set these repository variables:

```env
GCP_PROJECT_ID=letsgodb
GCP_REGION=us-central1
CLOUD_RUN_SERVICE=letsgosa-backend
ARTIFACT_REGISTRY_REPOSITORY=letsgosa
```

Set these repository secrets:

```env
WORKLOAD_IDENTITY_PROVIDER=projects/458140268449/locations/global/workloadIdentityPools/github-pool/providers/github-provider
GCP_SERVICE_ACCOUNT=github-deployer@letsgodb.iam.gserviceaccount.com
```

The workflow uses GitHub configuration only for deployment metadata. Runtime application configuration must stay on the Cloud Run service or in Secret Manager.

## Runtime configuration

Do not keep backend runtime environment values in GitHub or in this repo.

Configure non-secret environment variables directly on the Cloud Run service, either in the Cloud Run console or with `gcloud run services update`. Example values for this service:

```env
GCP_PROJECT_ID=letsgodb
FIREBASE_PROJECT_ID=letsgodb
FIREBASE_ADMIN_ROLE=admin
ENVIRONMENT=production
CLOUD_SQL_CONNECTION_NAME=letsgodb:us-central1:free-trial-first-project
GCS_BUCKET_NAME=letsgosa-package-images
GCS_PUBLIC_BASE_URL=https://storage.googleapis.com/letsgosa-package-images
LETSGOSA_CORS_ALLOW_ORIGINS=https://letsgodb.web.app,https://letsgodb.firebaseapp.com
```

Example update command:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run services update letsgosa-backend `
  --region us-central1 `
  --project letsgodb `
  --update-env-vars "GCP_PROJECT_ID=letsgodb,FIREBASE_PROJECT_ID=letsgodb,FIREBASE_ADMIN_ROLE=admin,ENVIRONMENT=production,CLOUD_SQL_CONNECTION_NAME=letsgodb:us-central1:free-trial-first-project,GCS_BUCKET_NAME=letsgosa-package-images,GCS_PUBLIC_BASE_URL=https://storage.googleapis.com/letsgosa-package-images,LETSGOSA_CORS_ALLOW_ORIGINS=https://letsgodb.web.app,https://letsgodb.firebaseapp.com"
```

Store secrets in Secret Manager and attach them to the Cloud Run service, not to the workflow. Example secret value:

```env
LETSGOSA_DATABASE_URL=postgresql+psycopg://letsgodev:<DB_PASSWORD>@/letsgo?host=/cloudsql/letsgodb:us-central1:free-trial-first-project
```

The contact submission pipeline also needs SMTP runtime configuration. The backend reads these environment variable names:

```env
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM_EMAIL
CONTACT_TO_EMAIL
SMTP_USE_TLS
```

## One-time GCP setup

Enable the required APIs:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' services enable `
  artifactregistry.googleapis.com `
  run.googleapis.com `
  secretmanager.googleapis.com `
  iamcredentials.googleapis.com `
  --project letsgodb
```

Create the Artifact Registry repository once:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' artifacts repositories create letsgosa `
  --project letsgodb `
  --location us-central1 `
  --repository-format docker
```

The backend image path used by the workflow is:

```text
us-central1-docker.pkg.dev/letsgodb/letsgosa/backend
```

Create the database secret if it does not exist:

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

Attach the secret to Cloud Run:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run services update letsgosa-backend `
  --region us-central1 `
  --project letsgodb `
  --update-secrets LETSGOSA_DATABASE_URL=letsgosa-database-url:latest
```

Create the SMTP secrets used by the contact form. Example values for Gmail SMTP:

```powershell
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="your-account@gmail.com"
$env:SMTP_PASSWORD="your-app-password"
$env:SMTP_FROM_EMAIL="your-account@gmail.com"
$env:CONTACT_TO_EMAIL="hedoneafrika@gmail.com"
$env:SMTP_USE_TLS="true"

$env:SMTP_HOST | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create SMTP_HOST `
  --project letsgodb `
  --data-file=-
$env:SMTP_PORT | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create SMTP_PORT `
  --project letsgodb `
  --data-file=-
$env:SMTP_USERNAME | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create SMTP_USERNAME `
  --project letsgodb `
  --data-file=-
$env:SMTP_PASSWORD | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create SMTP_PASSWORD `
  --project letsgodb `
  --data-file=-
$env:SMTP_FROM_EMAIL | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create SMTP_FROM_EMAIL `
  --project letsgodb `
  --data-file=-
$env:CONTACT_TO_EMAIL | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create CONTACT_TO_EMAIL `
  --project letsgodb `
  --data-file=-
$env:SMTP_USE_TLS | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets create SMTP_USE_TLS `
  --project letsgodb `
  --data-file=-
```

If those secrets already exist, add a new version instead:

```powershell
$env:SMTP_HOST | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add SMTP_HOST `
  --project letsgodb `
  --data-file=-
$env:SMTP_PORT | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add SMTP_PORT `
  --project letsgodb `
  --data-file=-
$env:SMTP_USERNAME | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add SMTP_USERNAME `
  --project letsgodb `
  --data-file=-
$env:SMTP_PASSWORD | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add SMTP_PASSWORD `
  --project letsgodb `
  --data-file=-
$env:SMTP_FROM_EMAIL | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add SMTP_FROM_EMAIL `
  --project letsgodb `
  --data-file=-
$env:CONTACT_TO_EMAIL | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add CONTACT_TO_EMAIL `
  --project letsgodb `
  --data-file=-
$env:SMTP_USE_TLS | & 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' secrets versions add SMTP_USE_TLS `
  --project letsgodb `
  --data-file=-
```

Attach the SMTP secrets to Cloud Run:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run services update letsgosa-backend `
  --region us-central1 `
  --project letsgodb `
  --update-secrets SMTP_HOST=SMTP_HOST:latest,SMTP_PORT=SMTP_PORT:latest,SMTP_USERNAME=SMTP_USERNAME:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest,SMTP_FROM_EMAIL=SMTP_FROM_EMAIL:latest,CONTACT_TO_EMAIL=CONTACT_TO_EMAIL:latest,SMTP_USE_TLS=SMTP_USE_TLS:latest
```

If the service already has SMTP variables configured as plain environment values, remove them first:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run services update letsgosa-backend `
  --region us-central1 `
  --project letsgodb `
  --remove-env-vars SMTP_HOST,SMTP_PORT,SMTP_USERNAME,SMTP_PASSWORD,SMTP_FROM_EMAIL,CONTACT_TO_EMAIL,SMTP_USE_TLS
```

If the service still contains an old secret reference such as `your-smtp-password-secret`, remove that secret-backed environment variable first:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' run services update letsgosa-backend `
  --region us-central1 `
  --project letsgodb `
  --remove-secrets SMTP_PASSWORD
```

Create the deployment service account if it does not already exist:

```text
github-deployer@letsgodb.iam.gserviceaccount.com
```

Grant the GitHub deployment service account at least:

- `roles/run.admin`
- `roles/artifactregistry.writer`
- `roles/iam.serviceAccountUser` on the Cloud Run runtime service account
- `roles/cloudbuild.builds.editor`
- `roles/cloudsql.client`
- `roles/secretmanager.secretAccessor` for `letsgosa-database-url`

Grant GitHub access to impersonate that service account:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' iam service-accounts add-iam-policy-binding `
  'github-deployer@letsgodb.iam.gserviceaccount.com' `
  --project='letsgodb' `
  --role='roles/iam.workloadIdentityUser' `
  --member='principalSet://iam.googleapis.com/projects/458140268449/locations/global/workloadIdentityPools/github-pool/attribute.repository/letsgosa/web_backend'
```

Equivalent console path:

1. IAM & Admin
2. Service Accounts
3. `github-deployer`
4. Permissions
5. Grant Access
6. Principal:

```text
principalSet://iam.googleapis.com/projects/458140268449/locations/global/workloadIdentityPools/github-pool/attribute.repository/letsgosa/web_backend
```

Role:

```text
Workload Identity User
```

Grant the Cloud Run runtime service account at least:

- `roles/secretmanager.secretAccessor` for `letsgosa-database-url`
- `roles/secretmanager.secretAccessor` for the SMTP secrets attached to the service
- `roles/storage.objectAdmin` for `gs://letsgosa-package-images`
- `roles/cloudsql.client` if the service connects through Cloud SQL

## Workflow behavior

On every push to `main`, the deploy workflow:

1. Authenticates to Google Cloud with Workload Identity Federation.
2. Reads the latest `letsgosa-database-url` value from Secret Manager.
3. Runs `alembic upgrade head` against the production database. If the URL uses the Cloud Run Unix socket form, the workflow starts a Cloud SQL Auth Proxy and rewrites the URL to `127.0.0.1:5432` for the migration step.
4. Builds the backend image from the repo-root Dockerfile.
5. Pushes two tags to Artifact Registry: `${GITHUB_SHA}` and `latest`.
6. Deploys the `${GITHUB_SHA}` image to Cloud Run.
7. Reads the service URL from Cloud Run and retries `GET /health` until it passes or times out.

Because the workflow updates only the image, existing Cloud Run environment variables, secrets, traffic settings, and previous revisions remain in place for rollback.

## Manual verification

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

Verify the contact route is registered in OpenAPI:

```powershell
Invoke-WebRequest "$serviceUrl/openapi.json"
```

Test a contact submission:

```powershell
Invoke-WebRequest `
  -Uri "$serviceUrl/api/contact" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"first_name":"Jane","last_name":"Doe","email":"jane@example.com","phone":"+27 82 123 4567","subject":"Testing contact flow","message":"This is a production contact flow verification."}'
```

If the contact route returns `500`, check Cloud Run logs for SMTP failures:

```powershell
& 'C:\Users\l\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd' logging read `
  "resource.type=cloud_run_revision AND resource.labels.service_name=letsgosa-backend" `
  --project letsgodb `
  --limit 50 `
  --format json
```

Common causes are:

- `SMTP_PORT` secret is not a number such as `587`
- `SMTP_USE_TLS` is not `true` or `false`
- `SMTP_FROM_EMAIL` does not match the authenticated SMTP account
- the SMTP provider requires an app password instead of the normal account password

If you need to apply schema changes outside GitHub Actions, run `alembic upgrade head` against the production database before deploying or shifting traffic.
