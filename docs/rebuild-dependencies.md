# Clean-start rebuild dependencies

Status: dependency definition for a clean deployment. This document does not provision or deploy infrastructure.

## Scope and decisions

- Build a new Modal + Vercel + Clerk + Azure Database for PostgreSQL deployment. Do not reproduce the legacy Cloud Run, Firebase Hosting/Auth, or Cloud SQL configuration.
- Start Azure PostgreSQL with an empty application schema. Cloud SQL rows, legacy package images, chatbot conversations, bookings, and contact submissions are explicitly excluded.
- Do not collect performance baselines or perform DNS cutover/decommissioning as part of this work.
- **Object-storage decision: retain Google Cloud Storage (GCS).** Use clean, environment-specific buckets and the existing storage adapter for package images. GCS was selected because `GcsStorageService` already implements the package-image contract; changing providers adds application work without being required for this rebuild. The legacy bucket is not a data-migration source.
- Secrets and complete connection strings must exist only in the platform stores named below. Examples and committed configuration contain names/placeholders only.

## Application/runtime dependencies

- Backend: Python 3.12 plus the locked FastAPI/Uvicorn, SQLAlchemy/Alembic, `psycopg`, Google Cloud Storage, OpenAI, PyPDF and multipart dependencies. Add the Modal SDK/deployment entrypoint and a maintained Clerk backend/JWT verifier; remove `firebase-admin` after the Clerk adapter lands.
- Frontend: Node 20 build runtime with the existing React 18/Vite stack. Add `@clerk/react` and remove the Firebase browser SDK after the auth provider is replaced.
- SMTP uses Python’s standard library and needs no extra package. GCS remains the only package-media provider, so the unused `MINIO_*` example settings are not dependencies.
- Keep `uv.lock` and `frontend/package-lock.json` as the reproducible dependency sources for image and frontend builds. Any dependency change required by the Clerk/Modal work must update the appropriate lockfile.

## Platform responsibilities

| Platform | Development | Production | Responsibility |
| --- | --- | --- | --- |
| Modal | `dev` environment and dev app/secrets | `prod` environment and prod app/secrets | Build the Python 3.12 image, expose the FastAPI app with `modal.asgi_app`, attach runtime secrets, reach Azure/GCS/Clerk/OpenAI/SMTP, and expose `/health` and `/health/db`. Modal environments isolate apps and secrets ([Modal environments](https://modal.com/docs/guide/environments), [secrets](https://modal.com/docs/guide/secrets)). |
| Vercel | Local plus Preview deployments | Production deployment/custom domain | Build `frontend` with `npm ci && npm run build`, serve `frontend/dist`, provide public build variables, and rewrite SPA routes to `/index.html`. Vercel variables are environment-scoped and Vite-visible names require the `VITE_` prefix ([Vercel environments](https://vercel.com/docs/environment-variables), [Vite](https://vercel.com/docs/frameworks/frontend/vite)). |
| Clerk | Separate development instance | Separate production instance | Own users, Google sign-in, sessions, application identity, allowed origins/redirects, and the `admin` session claim. No application user table is required. |
| Azure | Separate dev database/server (or isolated dev database and role) | Dedicated production database and role | Run managed PostgreSQL, enforce TLS/network access, back up the database, and provide a DDL-capable migration identity and DML runtime identity. |
| GCS | Clean dev image and conversation buckets | Clean prod image and conversation buckets | Persist package media and chatbot conversations. Do not copy legacy objects. Keep public images and private conversations in different buckets. |

Use a stable Vercel development/preview hostname when possible. Commit-specific preview origins are unsuitable for a fixed production CORS and Clerk `authorizedParties` allowlist. No development component may use production database, storage, Clerk, or runtime secrets.

## Configuration and secret matrix

“Required” means required for an empty, fully functional deployment, even where current code has a fallback that leaves a feature unavailable. Modal Secret names are containers/groups; the keys shown are injected environment variables.

### Modal backend

| Key | Consuming component | Required/value shape | Target store |
| --- | --- | --- | --- |
| `LETSGOSA_ENV` | `Settings`, production guards | Required: `development` or `production` | Modal app config |
| `LETSGOSA_DATABASE_URL` | SQLAlchemy and Alembic | Required secret: `postgresql+psycopg://...` with Azure hostname, database and `sslmode=verify-full` (or approved `verify-ca`) plus trusted root CA; migrations specifically read this name, not `DATABASE_URL` | Modal Secret `letsgosa-database-{env}` |
| `CORS_ORIGINS` | FastAPI CORS middleware | Required comma-separated exact Vercel/local origins; do not use `*` | Modal app config |
| `CLERK_SECRET_KEY` | Replacement Clerk backend auth adapter | Required secret; production and development values must differ | Modal Secret `letsgosa-clerk-{env}` |
| `CLERK_JWT_KEY` | Clerk token verifier | Recommended non-secret public PEM for networkless verification; otherwise the adapter retrieves Clerk JWKS with `CLERK_SECRET_KEY` | Modal Secret `letsgosa-clerk-{env}` (convenient multiline injection; not confidential) |
| `CLERK_AUTHORIZED_PARTIES` | Clerk token verifier (`azp`) | Required comma-separated exact frontend origins, equal to the CORS frontend set | Modal app config |
| `CLERK_ADMIN_CLAIM` | `require_admin` replacement | Required, fixed to `admin` | Modal app config |
| `STORAGE_PROVIDER` | storage factory | Required, fixed to `gcs` | Modal app config |
| `GCP_PROJECT_ID` | GCS client | Required project identifier (non-secret) | Modal app config |
| `GCS_BUCKET_NAME` | package-image adapter | Required dev/prod public-image bucket name | Modal app config |
| `GCS_PUBLIC_BASE_URL` | package-image URL builder/parser | Required HTTPS public/CDN base URL with no trailing slash | Modal app config |
| `GCS_CONVERSATION_BUCKET_NAME` | new conversation-store adapter | Required dev/prod private bucket name; **not consumed until the file store is replaced** | Modal app config |
| `GCP_SERVICE_ACCOUNT_JSON` | Modal startup/credential materialization | Required secret unless keyless GCP federation is implemented. Materialize it to an ephemeral file and point `GOOGLE_APPLICATION_CREDENTIALS` at that file; never commit it | Modal Secret `letsgosa-gcs-{env}` |
| `PACKAGE_IMAGE_MAX_UPLOAD_BYTES` | image upload validation | Optional; default `5242880` (5 MiB) | Modal app config |
| `OPENAI_API_KEY` | chatbot LLM client | Required secret for working chat; absence intentionally makes chat return 503 | Modal Secret `letsgosa-openai-{env}` |
| `OPENAI_MODEL` | chatbot LLM client | Optional; current default `gpt-4o-mini` | Modal app config |
| `OPENAI_TIMEOUT_SECONDS` | chatbot LLM client | Optional; current default `30` | Modal app config |
| `OPENAI_MAX_RETRIES` | chatbot LLM client | Optional; current default `2` | Modal app config |
| `CONTENT_DATA_DIR` | chatbot resource loaders | Required deployment value pointing to image-baked data, e.g. `/app/data` | Modal app config |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL`, `CONTACT_TO_EMAIL` | contact-email sender | Required for working contact form; port is an integer and TLS is normally `true` | Modal Secret `letsgosa-smtp-{env}` (grouped with SMTP credentials) |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | contact-email sender | Conditional pair: set both when the SMTP relay authenticates; password is secret | Modal Secret `letsgosa-smtp-{env}` |

The current defaults for `LETSGOSA_APP_NAME`, `LETSGOSA_API_PREFIX`, `LETSGOSA_API_VERSION`, host, port and debug are sufficient; Modal ASGI serving does not need the legacy Cloud Run `PORT` setting. `DATABASE_URL` and `LETSGOSA_CORS_ALLOW_ORIGINS` remain aliases in application code but must not be used in the rebuild. `CLOUD_SQL_CONNECTION_NAME`, `FIREBASE_*`, `MINIO_*`, and `CONVERSATION_STORAGE_DIR` are legacy/non-target settings.

The GCS credential variable above requires a small Modal entrypoint step because Google ADC consumes a credential **file path**, not raw JSON. A keyless workload identity is preferable later but is not a minimum dependency.

### Vercel frontend

| Key | Consuming component | Required/value shape | Target store |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | API client | Required absolute HTTPS Modal base URL, without `/api` and without trailing slash | Vercel Development/Preview/Production variable |
| `VITE_CLERK_PUBLISHABLE_KEY` | `@clerk/react` provider | Required public Clerk key; use the development instance outside production | Vercel variable (public by design) |
| `VITE_CLERK_SIGN_IN_URL` | Clerk provider/router | Required: `/admin/login` | Vercel variable |
| `VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL` | Clerk provider | Required: `/admin/dashboard` | Vercel variable |
| `VITE_CLERK_ADMIN_CLAIM` | protected-admin UI | Required, fixed to `admin`; server enforcement remains authoritative | Vercel variable |

Every `VITE_*` value is embedded in browser JavaScript and is therefore public. Never put `CLERK_SECRET_KEY`, database credentials, SMTP credentials, OpenAI credentials, or GCP private keys in Vercel `VITE_*` variables. The Clerk React quickstart uses `VITE_CLERK_PUBLISHABLE_KEY` ([Clerk React](https://clerk.com/docs/react/getting-started/quickstart)).

Replace the hard-coded Cloud Run production fallback in `frontend/src/api/client.js`; production must fail the build or startup if `VITE_API_BASE_URL` is missing. Add a Vercel SPA rewrite because React Router owns `/packages/*` and `/admin/*`.

### Secrets owned outside the runtimes

- Clerk stores its Google OAuth client ID/secret and Clerk signing private key. Only Clerk’s publishable key is sent to the browser; its backend secret/JWT verification material is copied to the appropriate Modal Secret.
- Azure owns the PostgreSQL administrator/runtime passwords. The assembled connection URL is copied only to the matching Modal database Secret and to the controlled migration job.
- GCP owns the GCS service account and key (if key-based access is used). The key JSON is copied only to the matching Modal GCS Secret.
- The SMTP/OpenAI providers own their credentials; copies live only in matching Modal Secrets.

## Database initialization

### Schema and migration procedure

- Target database: Azure Database for PostgreSQL Flexible Server, `public` schema on the role's search path, UTF-8, UTC application timestamps, accessed with `psycopg` and TLS. Azure recommends certificate-verifying TLS modes ([Azure TLS](https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls-how-to-connect)).
- Run `LETSGOSA_DATABASE_URL=<secret> alembic upgrade head` as a one-off release/migration job before starting a new backend revision. The normal backend startup verifies tables and deliberately does not migrate PostgreSQL.
- Use a migration role with create/alter/drop/index privileges on the target schema. The runtime role needs connect/usage and CRUD/sequence privileges only. The minimum setup may use one role, but separate roles are preferred.
- Current linear history: `20260606_000001` -> `20260608_000002` -> `20260610_000003`.
- Verification on 2026-09-04: the complete history was rendered for the PostgreSQL dialect and applied with `ON_ERROR_STOP` to a newly created empty PostgreSQL 18 database. It reached `20260610_000003` and created `alembic_version` plus all seven application tables. The temporary database was then removed.
- No application PostgreSQL extensions or `CREATE EXTENSION` statements are required. The migrations use ordinary tables, check constraints, indexes and SQL window functions. Therefore Azure extension allowlisting is not applicable; `plpgsql` is platform-provided and not an application dependency. If an extension is added later, verify it with `SHOW azure.extensions` before adding its migration ([Azure extensions](https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-create-extensions)).

### Required tables, constraints and indexes

SQLAlchemy enums are implemented as `VARCHAR` plus check constraints (`native_enum=False`), not PostgreSQL enum types.

| Table | Required content and relationships | Required constraints/indexes at current Alembic head |
| --- | --- | --- |
| `packages` | Package identity, descriptions, destination, duration, price/currency, publication/display flags and timestamps | PK `id`; unique index `slug`; checks: positive days, non-negative nights/price/display order, publication status in `draft,published,archived`; indexes on destination, featured, published and status |
| `package_images` | Image URL, optional GCS `storage_key`, alt text, order/cover flag; belongs to package | PK; FK `package_id -> packages` cascade delete; non-negative order; indexes on package and `(package_id, sort_order)` |
| `package_itinerary_items` | Day/title/description/duration/order/timestamps; belongs to package | PK; FK cascade; positive day and non-negative order; index on package; current migration also has unique `(package_id, day_number, sort_order)` |
| `package_inclusions` | Included/excluded item and display order; belongs to package | PK; FK cascade; non-negative order; type check `included,excluded`; indexes on package, type and `(package_id,type,display_order)` |
| `package_availability` | Date range, capacity/spots, status and timestamps; belongs to package | PK; FK cascade; checks for positive capacity, `0 <= spots <= capacity`, valid date range, status in `available,sold_out,cancelled,closed`; indexes on package, status and `(package_id,start_date)` |
| `bookings` | Customer/contact/party/request/status fields and timestamps | PK; package FK cascade; optional availability FK set null; status check `new,contacted,confirmed,cancelled,closed`; indexes on package, availability, status and `(package_id,status)` |
| `contact_submissions` | Contact message and email-delivery status/error/timestamps | PK; email-status check `pending,sent,failed`; index on email status |

`alembic_version` is Alembic-owned. There are no triggers, views, functions, additional schemas, or sequences authored outside Alembic (integer PK sequences are database/SQLAlchemy-generated).

Known metadata drift is documented rather than hidden: `alembic check` reports that the ORM expects `ix_package_itinerary_items_package_id_sort_order` and no longer declares the migration-created unique `(package_id, day_number, sort_order)` constraint. Before production content entry, add a new forward-only Alembic revision that removes that unique constraint and creates the composite index, or explicitly accept the migration schema and change the ORM metadata to match. Do not edit an applied revision. The SQLite-only startup compatibility helpers are not part of the Azure schema.

## Bootstrap data

An empty set of application rows is valid. No database seed script exists or is required: packages can be created through the authenticated admin UI, and bookings/contact submissions arise from application use. Legacy Cloud SQL rows are historical/user-generated data and must not be loaded.

Essential non-database bootstrap data is:

- `data/twin_profile.json` (must contain `name` and `full_name`), `data/summary.txt`, `data/style.txt`, and `data/fallback_personality.txt` for chatbot operation;
- `data/linkedin.pdf` is optional to the loader but is currently included in the runtime image;
- static frontend assets under `frontend/public` and one authorized Clerk administrator.

Repeatable initialization procedure:

1. Build the backend image from the pinned repository revision and copy only the five chatbot resource files already named by the Docker build; never copy `data/conversations/*.json`.
2. Run `alembic upgrade head` against the empty Azure database and verify `/health/db` after backend startup.
3. In the matching Clerk instance, invite/create the nominated administrator, set that user’s public metadata field `admin` to `true`, and configure the session-token custom claim `"admin": "{{user.public_metadata.admin}}"`. Force a fresh session and verify `/api/admin/auth/me` reports the boolean claim. Clerk supports custom session claims, with a short refresh delay ([Clerk custom claims](https://clerk.com/docs/guides/sessions/customize-session-tokens)).
4. Optionally create package/catalog content through the admin UI. This is business content, not bootstrap data.

The Clerk user/bootstrap identity is environment-specific and must be supplied operationally, not committed as an email address or password. Sample/test conversation JSON and test fixtures are never bootstrap inputs.

## Object storage

### Required buckets and access

Create two empty buckets per environment:

| Bucket purpose | Objects | Access and operations |
| --- | --- | --- |
| Public package images | `packages/{sanitized-slug}/{sanitized-name}-{uuid}.{jpg|png|webp}` | Backend: bucket metadata read/existence check and object create/delete. Browser: anonymous GET/HEAD only. Use uniform bucket-level access; the public-read decision means public access prevention cannot be enforced for this bucket. |
| Private chatbot conversations | `conversations/{validated-session-id}.json` | Backend only: object get/put/list (and delete for future retention tooling). Enforce public access prevention; no public or signed URL is returned. |

The current package upload endpoint buffers the whole file, detects content from magic bytes, permits JPEG/PNG/WebP only, and defaults to 5 MiB maximum. It writes through the backend; browsers do not upload directly to GCS. Configure image-bucket CORS for exact Vercel/local origins with `GET` and `HEAD` only (and only required response headers). No bucket CORS is needed for the private conversation bucket. GCS evaluates browser preflights against bucket CORS ([GCS CORS](https://docs.cloud.google.com/storage/docs/cross-origin)).

Signed URLs are **not required** by the selected current design: package images are public and conversations are private/backend-only. If public media is later rejected, changing `image_url` generation and expiry/cache behavior to signed URLs is a separate application change; signed URLs still work with public access prevention ([GCS public access prevention](https://docs.cloud.google.com/storage/docs/public-access-prevention)).

Before Modal deployment, replace `FileConversationStore` with a GCS-backed implementation. Modal containers cannot use `CONVERSATION_STORAGE_DIR` as durable shared state, and multiple containers would otherwise have inconsistent sessions. Also validate session IDs as UUIDs/opaque safe keys and authenticate or remove the currently public `GET /chat/sessions` endpoint before persisting real conversations.

Deleting an individual image already deletes its GCS object. Deleting a package currently cascades database rows but does **not** delete its objects; add package-delete object cleanup or an orphan lifecycle/reconciliation job before production. Versioning, retention period and lifecycle deletion are operational policies still to be set; they do not change the application contract.

## Authentication, origins and callbacks

The repository does not yet implement Clerk. Before deployment:

- frontend: replace `firebase` with `@clerk/react`, wrap the app in `ClerkProvider`, obtain a fresh session token, and continue sending it as `Authorization: Bearer <token>` for protected API calls;
- backend: replace `firebase-admin`/ADC verification with Clerk session-token verification; validate signature, algorithm, expiry/not-before, issuer and exact `azp`/authorized party, then map `sub`, name/email and claims into `AuthenticatedUser`;
- authorization: keep all `/api/admin/**` operations server-protected and require the boolean custom session claim `admin == true`. Hiding UI alone is not authorization. Clerk recommends checking `authorizedParties` for cross-origin bearer sessions ([manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification)).

Configure each Clerk instance with:

- application/instance identity and its matching publishable/secret keys;
- exact origins: `http://localhost:5173`, the stable Vercel development/preview origin, and only the production Vercel/custom origin in production;
- sign-in route `/admin/login`, post-sign-in fallback `/admin/dashboard`, and post-sign-out `/admin/login`;
- Google as the sign-in connection; self-service public sign-up disabled unless product requirements change;
- the `admin` custom session claim and at least one explicitly assigned admin user.

Clerk’s hosted OAuth callback URL shown in the Clerk Dashboard must be registered with the Google OAuth application; do not construct or guess it. The application itself has no OAuth callback route. No Clerk webhook is required because the application has no local users/organizations table and reads identity from the verified token. Consequently there is currently no webhook endpoint or signing secret. If user synchronization is added later, reserve `POST /api/webhooks/clerk`, subscribe only to required events, verify the Svix signature using a new `CLERK_WEBHOOK_SIGNING_SECRET`, and make processing idempotent ([Clerk webhooks](https://clerk.com/docs/guides/development/webhooks/overview)).

### Cross-origin contract

- Vercel calls the Modal HTTPS origin defined by `VITE_API_BASE_URL`; public calls use JSON, admin calls add the bearer token, and image upload uses multipart form data.
- Modal `CORS_ORIGINS` must list exact frontend origins, allow `Authorization` and `Content-Type`, and allow the API methods in use (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`). Current middleware sets `allow_credentials=False`, which is correct for bearer headers rather than cross-site Clerk cookies.
- `CLERK_AUTHORIZED_PARTIES` must contain the same frontend origins so a valid token minted for another origin is rejected.
- Health checks are `GET /health` and `GET /health/db`. The Modal app must expose the existing multi-route FastAPI app as ASGI ([Modal ASGI web apps](https://modal.com/docs/guide/webhooks)).

## External integrations and endpoint inventory

| Dependency | Direction | Application endpoint/callback | Requirement |
| --- | --- | --- | --- |
| Clerk/Google sign-in | Browser and backend -> Clerk; Clerk -> browser | `/admin/login` and `/admin/dashboard`; Clerk-hosted Google callback | Required for admin; no app webhook currently |
| OpenAI API | Modal -> OpenAI HTTPS | Public `POST /chat` and `POST /chat/stream` trigger calls | Required for chatbot; 30-second current client timeout |
| SMTP relay | Modal -> configured SMTP host/port | Public `POST /api/contact` triggers mail and records status | Required for contact flow; no callback/webhook |
| Azure PostgreSQL | Modal/migration runner -> Azure TCP 5432 | `/health/db` validates connectivity | TLS and Azure network rules must admit the chosen Modal egress path |
| GCS | Modal -> GCS HTTPS; browser -> public image base | Admin image routes upload/list/delete; public pages read image URLs | Required; no browser write and no signed URL in current design |
| Google Fonts | Browser -> `fonts.googleapis.com` | CSS import only | Existing optional presentation dependency; self-host if CSP/privacy policy disallows it |

There are no payment, analytics, booking-provider, SMS, or inbound integration callbacks in the current application.

## Temporary legacy resources

Keep only the legacy resources needed to operate and roll back the current site until the new deployment is validated and DNS/cutover is separately approved:

- current Cloud Run backend and its attached runtime secrets/build artifact;
- current Firebase Hosting site and Firebase Authentication application/admin identities;
- current Cloud SQL instance (known connection name `letsgodb:us-central1:free-trial-first-project`);
- current package-image GCS bucket (known as `letsgosa-package-images`) while the old frontend/backend can still reference it;
- current DNS records/domains.

This is a continuity list, not an infrastructure inventory. Do not copy Cloud SQL data or old GCS objects into the clean environment, and do not decommission anything under this issue.

## Assumptions and unresolved work

- Accepted: GCS is the final object-storage service for this rebuild; old objects are not migrated.
- Required application work: Modal deployment entrypoint, Clerk frontend/backend adapters, removal of hard-coded Firebase/Cloud Run fallbacks, Vercel SPA rewrite, GCS conversation store, and package-image orphan cleanup.
- Required schema follow-up: resolve the documented itinerary unique-constraint/composite-index metadata drift with a forward migration or matching ORM declaration before production content entry.
- Infrastructure decision still required: how Modal reaches Azure securely (approved public endpoint/firewall path versus a private networking design). Whatever is selected must support both runtime and migration jobs and preserve TLS hostname verification.
- Operational decisions still required: final domains, stable preview origin, Azure PostgreSQL version/SKU/networking, exact bucket names/regions, GCS retention/versioning, SMTP provider, and whether a custom Modal API domain is purchased. These are deliberately represented by configuration names, not guessed values.
- Assumption: public package images are acceptable. If policy requires all objects private, signed media delivery becomes a separate design and code change.
