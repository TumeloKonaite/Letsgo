# Backend Cloud Run Deployment

This document covers the backend production deploy path for:

- project `letsgodb`
- region `us-central1`
- service `letsgosa-backend`
- Artifact Registry repository `letsgosa`

The repo now deploys the backend through GitHub Actions in [.github/workflows/deploy-backend.yml](/c:/Users/l/Documents/letsgosa/.github/workflows/deploy-backend.yml). The workflow authenticates with Workload Identity Federation, builds the repo-root [Dockerfile](/c:/Users/l/Documents/letsgosa/Dockerfile), pushes the image to Artifact Registry, deploys that image to Cloud Run, and verifies `GET /health`.

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

Create the deployment service account if it does not already exist:

```text
github-deployer@letsgodb.iam.gserviceaccount.com
```

Grant the GitHub deployment service account at least:

- `roles/run.admin`
- `roles/artifactregistry.writer`
- `roles/iam.serviceAccountUser` on the Cloud Run runtime service account
- `roles/cloudbuild.builds.editor`

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
- `roles/storage.objectAdmin` for `gs://letsgosa-package-images`
- `roles/cloudsql.client` if the service connects through Cloud SQL

## Workflow behavior

On every push to `main`, the deploy workflow:

1. Authenticates to Google Cloud with Workload Identity Federation.
2. Builds the backend image from the repo-root Dockerfile.
3. Pushes two tags to Artifact Registry: `${GITHUB_SHA}` and `latest`.
4. Deploys the `${GITHUB_SHA}` image to Cloud Run.
5. Reads the service URL from Cloud Run and retries `GET /health` until it passes or times out.

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

If the database schema is behind, run `alembic upgrade head` against the production database before deploying or shifting traffic.
