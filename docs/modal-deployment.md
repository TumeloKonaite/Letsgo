# Modal staging deployment

Install the deployment CLI separately from application dependencies:

```sh
uv pip install --python .venv/bin/python 'modal>=1.0,<2'
.venv/bin/modal deploy --env staging modal_app.py
```

The app is `letsgosa-backend-staging`; the ASGI function is `web`.
The entrypoint packages Python source and five explicit content resources only.
Local .env files, conversation records and credentials are not uploaded. It uses
one container maximum and scales to zero when idle.

Create the `staging` Modal environment and these Secrets in it before deploying:

| Secret | Contents |
| --- | --- |
| `letsgosa-runtime-staging` | `CORS_ORIGINS` with approved HTTPS frontend origins; optional app settings |
| `letsgosa-database-staging-runtime` | `LETSGOSA_DATABASE_URL` for migrated PostgreSQL with verified TLS |
| `letsgosa-clerk-staging` | `CLERK_SECRET_KEY`, `CLERK_JWT_KEY`, `CLERK_ISSUER_URL`, `CLERK_AUTHORIZED_PARTIES`, `CLERK_ADMIN_CLAIM` |
| `letsgosa-gcs-staging` | Keyless GCS configuration below |
| `letsgosa-openai-staging` | `OPENAI_API_KEY` and optional model settings |
| `letsgosa-smtp-staging` | SMTP host, port, from email, contact destination, TLS flag and optional username/password |

The backend validates settings at startup and checks the existing database schema.
Run database migrations separately with the migration identity. No migrations
or database creation are performed by this entrypoint.

GCS configuration (non-secret values confirmed from the user's GCP screenshots):

```dotenv
STORAGE_PROVIDER=gcs
GCS_PROJECT_ID=letsgodb-507711
GCS_BUCKET_NAME=letsgobucket
GCS_OBJECT_PREFIX=staging/
GCS_CREDENTIALS_SECRET_NAME=letsgosa-gcs-staging
GCS_WIF_AUDIENCE=//iam.googleapis.com/projects/362439895302/locations/global/workloadIdentityPools/modal-staging/providers/modal
GCS_SERVICE_ACCOUNT_EMAIL=modal-storage-staging@letsgodb-507711.iam.gserviceaccount.com
```

Do not set key JSON or GOOGLE_APPLICATION_CREDENTIALS alongside federation.
The provider currently has condition `false`; after deployment, restrict it to
this function's actual workspace/environment/app IDs and function name. Map
`google.subject=assertion.container_id` (the full Modal subject can be too long)
and `attribute.workload='modal-storage-staging'`. Finish service-account
impersonation and self signBlob bindings as described in the storage runbook.
Never log or share the Modal identity token.

Deployment creation alone does not prove startup works. Request `/health` and
`/health/db`, then complete the image lifecycle and negative authorization tests.
Storage remains blocked until the federation condition and bindings are completed.

Chat currently uses an ephemeral local file store under `/tmp`; do not treat
staging chat history as durable. No existing conversation records are packaged.
The storage integration issue does not implement durable conversation storage.

## Deployment attempt

The Modal CLI authenticated successfully and the `staging` environment was
created. Deployment was attempted with the command above but stopped because
`letsgosa-runtime-staging` did not exist. The user confirmed no application
Secrets had been configured. No working endpoint or successful health check is
claimed. Entrypoint import, compilation, Ruff and diff checks passed locally.
