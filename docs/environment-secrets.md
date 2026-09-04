# Environment and secret matrix

Status: authoritative clean-start configuration input. Repository alignment reviewed 2026-09-04. Infrastructure owners must complete the review gate at the end of this document before provisioning.

This document defines configuration ownership for the React/Vite frontend on Vercel, the FastAPI web service and jobs on Modal, Clerk authentication, Azure Database for PostgreSQL, GitHub Actions, Google Cloud Storage (GCS), OpenAI, and SMTP. It does not provision infrastructure. All values shown are names, fixed non-secret defaults, URL shapes, or placeholders. Do not copy credentials or values from the retired Firebase/Cloud Run/Cloud SQL deployment.

## Rules and environment boundaries

- `D`, `S`, and `P` mean development, staging, and production. Local development belongs to `D`; it must never use `S` or `P` credentials.
- Create independent Modal environments, Vercel targets, Clerk applications/instances, Azure databases and roles, GCS buckets and service identities, OpenAI keys, SMTP credentials, and GitHub environments for `D`, `S`, and `P`. A compromised credential must be revocable in one environment without affecting another.
- A value is stored only where it is consumed. Azure and providers remain the credential systems of record; a runtime copy is placed only in the matching Modal Secret. GitHub does not receive application runtime secrets. Vercel does not receive backend secrets.
- Every `VITE_*` value is compiled into JavaScript and is public. `VITE_` is permitted only for browser-safe values. This static frontend has no Vercel server runtime, so it has no Vercel server secrets.
- Database URLs, private keys, API keys, tokens, passwords, webhook signing secrets, SMTP credentials, and service-account documents are server-only secrets even when a hostname or identifier inside them is public.
- Use fresh, least-privilege credentials. Prefer workload identity and short-lived tokens when a supported trust path exists. The initial GCS design permits an environment-specific service-account key in Modal only because Modal-to-GCP federation is not yet part of the approved design.
- Never print secret values. Do not enable shell tracing around secrets. GitHub workflows must use the `secrets` context and `::add-mask::` for any derived secret. Application errors and health checks report presence/connectivity, never values.

## Ownership model

| Platform | Stores and manages | Must not store |
| --- | --- | --- |
| Vercel | Browser-safe frontend build configuration, scoped to Development, stable Staging custom environment/branch, and Production; future server-runtime secrets only if a Vercel Function is introduced | Database URLs, Clerk secret keys, GCS credentials, OpenAI/SMTP credentials, or any secret under `VITE_*` |
| Modal | FastAPI and job configuration; matching environment-scoped Secrets for database, Clerk, GCS, OpenAI, SMTP, and optional webhook verification | Frontend publishable configuration not consumed by Modal; credentials for another environment |
| Clerk | User/session configuration, Clerk signing material, Google OAuth credentials, domain/origin controls, and any webhook endpoint/signing secret | Database, storage, OpenAI, SMTP, Vercel, or Modal deployment credentials |
| Azure | PostgreSQL server/database configuration, network/TLS policy, database roles and their source credentials | Assembled URLs for unrelated services |
| GitHub | Environment-scoped Modal deployment credentials and, only if native Vercel Git deployment cannot be used, Vercel CLI credentials | Application runtime secrets, database URLs, GCS keys, Clerk runtime keys, or frontend build values owned by Vercel |
| GCP/GCS | Buckets, IAM, CORS/lifecycle policy, service accounts, and source key material | Application or database credentials |
| Local development | Developer-specific copies in ignored `.env`/`.env.local` files or the developer's credential manager | Any staging/production value or committed environment file |

Modal Secret groups are `letsgosa-database-{env}-runtime`, `letsgosa-database-{env}-migration`, `letsgosa-clerk-{env}`, `letsgosa-gcs-{env}`, `letsgosa-openai-{env}`, `letsgosa-smtp-{env}`, and, only if enabled, `letsgosa-clerk-webhook-{env}`. `{env}` is one of `development`, `staging`, or `production`. Functions attach only the groups they need.

## Key matrix

Sensitivity is `Public` (safe in a browser), `Internal` (not a credential but server/operations only), `Confidential` (personal or operational data), or `Secret`. Requirement is for a fully functional clean-start environment; `Conditional` means provision only when the named feature or authentication method is enabled. Rotation references point to the runbook below.

### Vercel frontend build and browser runtime

| Variable | Purpose / value shape | Envs | Exposure and runtime | Owner / consumer | Provisioned by | Req. | Rotation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `VITE_API_BASE_URL` | Absolute HTTPS Modal API origin, no `/api` and no trailing slash; local D may use `http://localhost:8000` | D/S/P | Public; Vercel build -> browser API client | Vercel / frontend API client | Matching Modal web endpoint output | Required | R1 |
| `VITE_CLERK_PUBLISHABLE_KEY` | Publishable key for the matching Clerk application | D/S/P | Public; Vercel build -> Clerk browser SDK | Vercel / auth provider | Clerk | Required | R2 |
| `VITE_CLERK_SIGN_IN_URL` | Application sign-in route; `/admin/login` | D/S/P | Public; browser router/Clerk | Vercel / auth provider | Application owner | Required | R1 |
| `VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL` | Safe post-sign-in fallback; `/admin/dashboard` | D/S/P | Public; browser Clerk flow | Vercel / auth provider | Application owner | Required | R1 |
| `VITE_CLERK_SIGN_OUT_FALLBACK_REDIRECT_URL` | Safe post-sign-out fallback; `/admin/login` | D/S/P | Public; browser Clerk flow | Vercel / auth provider | Application owner | Required | R1 |
| `VITE_CLERK_ADMIN_CLAIM` | UI hint naming the `admin` claim; server authorization remains authoritative | D/S/P | Public; browser protected-route UI | Vercel / frontend auth | Application owner | Required | R1 |

No other frontend key is approved. In particular, private/admin Clerk keys and all database, storage, OpenAI, SMTP, CI, signing, and OAuth secrets are forbidden in `VITE_*` variables.

### Modal FastAPI service and jobs

| Variable | Purpose / value shape | Envs | Exposure and runtime | Owner / consumer | Provisioned by | Req. | Rotation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `LETSGOSA_ENV` | Exact deployed tier name: `development`, `staging`, or `production`; `test` is accepted only for explicit automated-test fixtures | D/S/P | Internal; web and jobs | Modal config / application settings | Deployment owner | Required | R1 |
| `LETSGOSA_DATABASE_URL` | Complete `postgresql+psycopg://...` URL with Azure host, database, role and certificate-verifying TLS options | D/S/P | Secret; web or job, never browser | Modal database Secret / SQLAlchemy and Alembic | Azure creates role credential; deployment owner assembles URL | Required | R3 |
| `CORS_ORIGINS` | Comma-separated exact frontend origins; never `*` | D/S/P | Internal; FastAPI web only | Modal config / CORS middleware | Vercel domain output plus security owner | Required | R1 |
| `CLERK_SECRET_KEY` | Environment-specific Clerk Backend API/verification credential | D/S/P | Secret; FastAPI web only | Modal Clerk Secret / backend auth adapter | Clerk | Required | R2 |
| `CLERK_JWT_KEY` | Public PEM used for local JWT signature verification; multiline value | D/S/P | Internal, server-only; FastAPI web | Modal Clerk Secret / backend auth adapter | Clerk JWKS/signing-key output | Required | R2 |
| `CLERK_ISSUER_URL` | Exact matching Clerk token issuer URL | D/S/P | Internal; FastAPI web | Modal config / backend auth adapter | Clerk | Required | R1 |
| `CLERK_AUTHORIZED_PARTIES` | Comma-separated exact allowed token `azp` origins; same frontend set as CORS | D/S/P | Internal; FastAPI web | Modal config / backend auth adapter | Vercel domain output plus Clerk owner | Required | R1 |
| `CLERK_ADMIN_CLAIM` | Server-authoritative boolean claim name; `admin` | D/S/P | Internal; FastAPI web | Modal config / admin dependency | Application/Clerk owner | Required | R1 |
| `CLERK_WEBHOOK_SIGNING_SECRET` | Verifies Svix signatures at the reserved Clerk webhook route | D/S/P | Secret; webhook handler only | Modal webhook Secret / webhook handler | Clerk endpoint | Conditional; **do not provision now** because no webhook is implemented | R4 |
| `STORAGE_PROVIDER` | Selected provider; fixed to `gcs` | D/S/P | Internal; web and storage jobs | Modal config / storage factory | Architecture owner | Required | R1 |
| `GCP_PROJECT_ID` | GCP project that owns the matching buckets and identity | D/S/P | Internal; web and storage jobs | Modal config / GCS client | GCP | Required | R1 |
| `GCS_BUCKET_NAME` | Matching public package-image bucket name | D/S/P | Internal; web and image-cleanup job | Modal config / package storage adapter | GCP/GCS | Required | R1 |
| `GCS_PUBLIC_BASE_URL` | HTTPS public/CDN base, no trailing slash | D/S/P | Public data but server-configured; web URL builder | Modal config / package storage adapter | GCP/GCS or CDN | Required | R1 |
| `GCS_CONVERSATION_BUCKET_NAME` | Matching private conversation bucket | D/S/P | Internal; web and retention job | Modal config / planned GCS conversation store | GCP/GCS | Required before deployed chat persistence | R1 |
| `GCP_SERVICE_ACCOUNT_JSON` | New least-privilege JSON credential for only the matching buckets | D/S/P | Secret; web and GCS jobs | Modal GCS Secret / storage adapter | GCP IAM | Required unless an explicit credential file is used | R5 |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to an explicitly supplied credential file | D/S/P | Internal path; web/jobs | Runtime environment / Google client library | Deployment owner | Alternative to the JSON variable; absolute path in S/P | R5 |
| `PACKAGE_IMAGE_MAX_UPLOAD_BYTES` | Maximum accepted image bytes; default `5242880` | D/S/P | Internal; FastAPI web | Modal config / upload validation | Application owner | Optional | R1 |
| `OPENAI_API_KEY` | Environment/project-scoped key for chatbot inference | D/S/P | Secret; FastAPI web only | Modal OpenAI Secret / LLM client | OpenAI project owner | Required for chat | R6 |
| `OPENAI_MODEL` | Approved model identifier; current default `gpt-4o-mini` | D/S/P | Internal; FastAPI web | Modal config / LLM client | Application owner | Optional | R1 |
| `OPENAI_TIMEOUT_SECONDS` | Client timeout; current default `30` | D/S/P | Internal; FastAPI web | Modal config / LLM client | Application owner | Optional | R1 |
| `OPENAI_MAX_RETRIES` | Retry count; current default `2` | D/S/P | Internal; FastAPI web | Modal config / LLM client | Application owner | Optional | R1 |
| `SMTP_HOST` | Relay hostname | D/S/P | Internal; FastAPI contact flow | Modal SMTP Secret / email sender | SMTP provider | Required for contact email | R7 |
| `SMTP_PORT` | Relay port; normally `587` | D/S/P | Internal; FastAPI contact flow | Modal SMTP Secret / email sender | SMTP provider | Required for contact email | R7 |
| `SMTP_USERNAME` | Environment-specific relay login | D/S/P | Confidential credential identifier; FastAPI contact flow | Modal SMTP Secret / email sender | SMTP provider | Conditional if relay authenticates | R7 |
| `SMTP_PASSWORD` | Relay password/token | D/S/P | Secret; FastAPI contact flow | Modal SMTP Secret / email sender | SMTP provider | Conditional if relay authenticates | R7 |
| `SMTP_FROM_EMAIL` | Approved sender address | D/S/P | Confidential; FastAPI contact flow | Modal SMTP Secret / email sender | SMTP/domain owner | Required for contact email | R7 |
| `CONTACT_TO_EMAIL` | Destination mailbox | D/S/P | Confidential; FastAPI contact flow | Modal SMTP Secret / email sender | Business owner | Required for contact email | R7 |
| `SMTP_USE_TLS` | Whether to start TLS; set explicitly (`true` unless the provider requires another secure mode) | D/S/P | Internal; FastAPI contact flow | Modal SMTP Secret / email sender | SMTP provider | Required for contact email | R7 |
| `CONTENT_DATA_DIR` | Read-only path to image-baked chatbot resources, such as `/app/data` | D/S/P | Internal; FastAPI web | Modal config / resource loader | Backend image | Required | R1 |
| `CONVERSATION_STORAGE_DIR` | Local file fallback, such as `data/conversations` | D only | Internal; local FastAPI only | Ignored local `.env` / file conversation store | Developer | Optional transition setting; forbidden on deployed Modal | R1 |
| `LETSGOSA_APP_NAME` | API display name; code default is sufficient | D/S/P | Internal; FastAPI metadata | Modal config / FastAPI | Application owner | Optional | R1 |
| `LETSGOSA_DEBUG` | Debug behavior; must be `false` in S/P | D/S/P | Internal; FastAPI | Modal config / application settings | Application owner | Optional | R1 |
| `LETSGOSA_API_PREFIX` | API prefix; current default `/api` | D/S/P | Internal; FastAPI routing | Modal config / application settings | Application owner | Optional; change only with frontend coordination | R1 |
| `LETSGOSA_API_VERSION` | API metadata version | D/S/P | Internal; FastAPI metadata | Modal config / application settings | Release process | Optional | R1 |

The following code-recognized keys are deliberately excluded from the clean-start configuration. They remain documented so an operator does not mistake them for missing inputs.

| Key(s) | Classification and action |
| --- | --- |
| `LETSGOSA_HOST`, `LETSGOSA_PORT`, `PORT` | Process/platform settings; Modal's ASGI serving owns these, so do not configure them |
| `ENVIRONMENT`, `DATABASE_URL`, `LETSGOSA_CORS_ALLOW_ORIGINS`, `GOOGLE_CLOUD_PROJECT` | Retired aliases; the application intentionally ignores them |
| `CLOUD_SQL_CONNECTION_NAME` | Retired Cloud SQL setting; never configure for Azure |
| `FIREBASE_PROJECT_ID`, `FIREBASE_ADMIN_ROLE` | Retired backend settings; the application intentionally ignores them |
| `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID`, `VITE_FIREBASE_STORAGE_BUCKET`, `VITE_FIREBASE_MESSAGING_SENDER_ID`, `VITE_FIREBASE_ADMIN_CLAIM` | Retired browser settings; the frontend build rejects them |
| `VITE_LETSGO_API_BASE_URL` | Retired frontend API URL alias; use `VITE_API_BASE_URL` |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` | Unused object-storage alternative; GCS is selected |

The application consumes the canonical keys above and validates them before backend startup or frontend build. Local defaults are restricted to development; staging and production fail closed.

Use two Modal database Secrets containing the same environment-variable name but different Azure roles. Bind `letsgosa-database-{env}-runtime` only to the web service and data-maintenance jobs; bind `letsgosa-database-{env}-migration` only to the one-off Alembic release job. Never attach both to one function. Scheduled GCS retention/orphan cleanup receives only the runtime database group and GCS group. No job receives Clerk, OpenAI, or SMTP secrets unless its code directly consumes them.

### GitHub Actions deployment configuration

CI tests use committed synthetic values such as `example.invalid` and SQLite; they do not use deployed-environment secrets. Deployment jobs use protected GitHub Environments named `development`, `staging`, and `production`, each with reviewers appropriate to the tier.

| Variable | Purpose / value shape | Envs | Exposure and runtime | Owner / consumer | Provisioned by | Req. | Rotation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `MODAL_TOKEN_ID` | ID half of a Modal service-user token for exactly one Modal environment | D/S/P | Secret credential component; GitHub deploy job | GitHub Environment secret / Modal CLI | Modal | Required for Actions-driven Modal deploy | R8 |
| `MODAL_TOKEN_SECRET` | Secret half of the same Modal token | D/S/P | Secret; GitHub deploy job | GitHub Environment secret / Modal CLI | Modal | Required for Actions-driven Modal deploy | R8 |
| `MODAL_ENVIRONMENT` | Exact target `development`, `staging`, or `production` | D/S/P | Internal; GitHub deploy job | GitHub Environment variable / Modal CLI | Modal/deployment owner | Required | R1 |
| `GITHUB_TOKEN` | Per-job token supplied automatically by Actions | D/S/P | Ephemeral secret; workflow actions/API | GitHub / workflow | GitHub Actions | Required, platform-generated; do not create a repository secret | R9 |
| `VERCEL_TOKEN` | Vercel CLI token if native Git integration cannot be used | D/S/P | Secret; GitHub frontend deploy job | GitHub Environment secret / Vercel CLI | Vercel account/team | Conditional fallback; native Vercel Git integration is preferred | R10 |
| `VERCEL_ORG_ID` | Vercel team identifier for CLI deploy | D/S/P | Internal; GitHub frontend deploy job | GitHub Environment variable / Vercel CLI | Vercel | Conditional with `VERCEL_TOKEN` | R1 |
| `VERCEL_PROJECT_ID` | Vercel project identifier for CLI deploy | D/S/P | Internal; GitHub frontend deploy job | GitHub Environment variable / Vercel CLI | Vercel | Conditional with `VERCEL_TOKEN` | R1 |

Grant each Modal service user Contributor access to only its matching environment. Use three service users/tokens; do not give a development token access to production. Vercel's native GitHub integration should build/deploy the frontend and read build variables directly from Vercel, eliminating GitHub copies. Legacy deployment workflows were removed; replacement deployment automation is separate work.

### Provider-managed settings without application environment variables

| Setting | Purpose | Envs | Sensitivity / owner | Consumer | Provisioned by | Req. | Rotation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Clerk application/instance | Isolates users, sessions, keys, claims and domains | D/S/P | Internal / Clerk | Clerk and application auth | Clerk owner | Required | R2 |
| Clerk session claim template | Emits boolean `admin` from explicitly managed public metadata | D/S/P | Internal / Clerk | Clerk tokens and backend authorization | Clerk owner | Required | R1 |
| Google OAuth client ID | Identifies the Google sign-in app | S/P; D may use Clerk shared dev credentials | Internal / Clerk stores configured value | Clerk social connection | Google Cloud OAuth owner | Required for independent S/P Google sign-in | R11 |
| Google OAuth client secret | Authenticates Clerk to Google | S/P; D may use Clerk shared dev credentials | Secret / Clerk only | Clerk social connection | Google Cloud OAuth owner | Required for independent S/P Google sign-in | R11 |
| Clerk webhook endpoint and event subscriptions | Sends only selected identity events to the application | D/S/P | Internal / Clerk | Reserved backend webhook handler | Clerk owner | Conditional; disabled now | R4 |
| Azure PostgreSQL runtime role/password | Least-privilege DML identity | D/S/P | Secret / Azure is source; URL copy in Modal only | FastAPI and data jobs | Azure DBA | Required | R3 |
| Azure PostgreSQL migration role/password | DDL identity, separate from runtime | D/S/P | Secret / Azure is source; URL copy in Modal only | Alembic release job | Azure DBA | Required | R3 |
| Azure host/database/TLS/network policy | Isolated database endpoint, TLS enforcement and Modal egress allowlist/private path | D/S/P | Internal / Azure | Web and migration connections | Azure owner | Required | R1/R3 |
| GCS bucket IAM and service account | Grants object operations only on matching image/conversation buckets | D/S/P | Secret key source and internal IAM / GCP | Modal GCS client | GCP IAM owner | Required | R5 |
| GCS image-bucket CORS | Exact frontend origins; anonymous `GET`/`HEAD` only | D/S/P | Public policy / GCP | Browser image reads | GCS owner | Required for cross-origin image reads | R1 |
| GCS lifecycle/versioning policy | Retention and cleanup without cross-environment impact | D/S/P | Internal / GCP | GCS operations | Data owner | Required before P; policy choice may differ by tier | R1 |

## Authorized domains, redirects, callbacks, and webhooks

Replace bracketed placeholders during provisioning. Do not place wildcard production origins in CORS or Clerk authorized parties.

| Tier | Frontend origins authorized in Modal CORS and Clerk `authorizedParties` | Clerk/Vercel routes | OAuth callback | Clerk webhook |
| --- | --- | --- | --- | --- |
| Development | `http://localhost:5173`, `http://127.0.0.1:5173`, and `[stable-development-vercel-origin]` if remote D is used | Sign-in `[frontend-origin]/admin/login`; fallback `[frontend-origin]/admin/dashboard`; sign-out `[frontend-origin]/admin/login` | Exact Clerk-hosted callback displayed by the D Clerk/Google connection; never guess it | Disabled. For future testing, use an approved ephemeral HTTPS tunnel plus `/api/webhooks/clerk`; never reuse S/P secret |
| Staging | `[exact-staging-frontend-origin]` only | Same paths on the staging origin | Exact callback displayed by the S Clerk application and registered only in the staging Google OAuth client | Disabled until handler exists; then `[staging-modal-api-origin]/api/webhooks/clerk` |
| Production | `[exact-production-frontend-origin]` and an explicitly approved canonical alias only | Same paths on the production origin; redirect aliases to the canonical host before auth | Exact callback displayed by the P Clerk application and registered only in the production Google OAuth client | Disabled until handler exists; then `[production-modal-api-origin]/api/webhooks/clerk` |

The application currently has no user/organization mirror and no Clerk webhook handler, so no webhook endpoint, event subscription, or signing secret is provisioned. If synchronization is approved later, implement `POST /api/webhooks/clerk`, verify the raw request and Svix headers before parsing, subscribe only to required events, make handlers idempotent, and then activate the conditional row. Clerk owns the endpoint and signing secret; Modal stores the one runtime copy.

For Clerk production domains, configure the exact root/custom domain and restrict the subdomain allowlist. Google OAuth JavaScript origins are the matching frontend origins. Its authorized redirect URI is the exact Clerk-hosted value shown in the Clerk Dashboard, not an application route. GCS image-bucket CORS uses the same frontend origin set with `GET` and `HEAD`; browsers never write directly to GCS.

## Per-environment setup

Perform these steps independently in D, then S, then P. Do not promote secret values between tiers.

1. Record the tier's canonical frontend and API origins in the review worksheet. Create the Vercel target, Modal environment, protected GitHub Environment, Clerk application/instance, Azure database and roles, GCP project/service identity and two empty buckets.
2. Generate new Azure runtime and migration credentials. Assemble two TLS-verifying `LETSGOSA_DATABASE_URL` values locally without logging them, store each in its matching Modal Secret, clear shell history/environment, and bind each Secret only to its intended function.
3. Configure Clerk domains, Google connection, redirect paths, session claim, and an environment-specific admin. Copy only the publishable key to Vercel. Put the secret key and public JWT material in the matching Modal configuration. Keep Google OAuth secrets in Clerk. Leave webhooks disabled.
4. Configure GCS IAM, public-image access/CORS, private-conversation public-access prevention, and lifecycle policy. Generate a new service-account key only if the approved deployment cannot use workload identity; store the sole runtime copy in Modal and retain the source under GCP IAM controls.
5. Create fresh environment-scoped OpenAI and SMTP credentials and put them only in the matching Modal Secrets. Set non-secret Modal variables from the matrix.
6. Set the six approved `VITE_*` variables in the matching Vercel scope. Development maps to Vercel Development, staging to a stable custom environment or dedicated staging branch/domain, and production to Production. Redeploy because build-time variable changes do not alter old deployments.
7. Prefer the Vercel GitHub integration. For Modal, create a separate service user/token per tier, restrict it to the matching Modal environment, and store the pair in that protected GitHub Environment. Require manual approval for production.
8. Run the Alembic job with only the migration database Secret, deploy web/jobs with their minimum Secret groups, and verify health/auth/storage/contact/chat without exposing values. Inspect the built frontend for forbidden names and credential patterns.

Local D setup uses `frontend/.env.example` copied to `frontend/.env.local` and `backend/.env.example` copied to the repository-root `.env`. Replace placeholders with D-only values. The backend currently loads the root `.env`. Keep files mode-restricted, do not share them in tickets/chat, and use a local credential helper where practical.

## Rotation and revocation runbook

For all rotations, work in one tier at a time, note every consumer from the matrix, test the new credential before revoking the old one when dual-key overlap is supported, and review logs for abuse. An emergency compromise skips the normal schedule: revoke/disable first when continued use presents greater risk, then restore with a new credential. Never expose old/new values in commands captured by logs.

- **R1 — non-secret configuration:** change the owning platform setting, redeploy/restart every listed consumer, verify exact origins/routes/connectivity, and roll back the configuration if validation fails. Removing a domain or endpoint is the revocation action. This never requires rotating unrelated credentials.
- **R2 — Clerk API/JWT/publishable material:** create a new key in the affected Clerk application, update Modal and/or Vercel, redeploy and validate sign-in plus backend token verification, then delete the old key and revoke active sessions if compromise scope warrants it. Refresh `CLERK_JWT_KEY` when Clerk signing keys change. Never rotate another tier's application.
- **R3 — Azure database:** create or alter only the affected runtime or migration role credential; update the corresponding Modal Secret, deploy/test that consumer, terminate old-role sessions, then revoke/drop the old credential/role. Runtime rotation must not alter the migration role and vice versa. For compromise, block the principal/network path first. Prefer short-lived Microsoft Entra tokens in a future design once Modal-to-Azure identity federation is approved.
- **R4 — Clerk webhook:** because it is disabled today, revoke by deleting/disable the Clerk endpoint. Once enabled, create a parallel endpoint with the same URL/events, store its new signing secret in the one Modal webhook Secret, deploy and verify a test event, then delete the old endpoint. Deduplicate deliveries during overlap.
- **R5 — GCS identity:** create a new key for only the affected service account (or a new least-privilege service account), update its Modal Secret, deploy/test object operations, then disable/delete the old key. If compromised, disable the key immediately and inspect audit logs. Revoking one identity must not change other tier buckets.
- **R6 — OpenAI:** create a replacement key in the matching OpenAI project, update the one Modal Secret, deploy/test chat, then revoke the old key and review usage/budget limits. Delete immediately on confirmed compromise.
- **R7 — SMTP:** issue a replacement password/API token for the matching sender, update the Modal SMTP Secret, deploy/test delivery, then revoke the old credential. If the sender identity or recipient changes, re-verify it with the provider; do not rotate other tiers.
- **R8 — Modal CI:** create a replacement environment-restricted service-user token, update only the matching GitHub Environment secrets, run a deployment, then delete the old token/service user. On compromise, revoke first and pause that tier's deploy workflow.
- **R9 — GitHub token:** `GITHUB_TOKEN` is created per job and expires automatically. Revoke a run by cancelling it; restrict workflow `permissions` to the minimum. Never persist or copy the token.
- **R10 — Vercel CLI fallback:** create a replacement token scoped to the deployment owner/team, update only the matching GitHub Environment, verify a deployment, then revoke the old token. If compromised, revoke immediately. Remove all three CLI settings when native Git deployment is restored.
- **R11 — Google OAuth:** create/rotate credentials in the matching Google OAuth project, update only the matching Clerk connection, validate sign-in with Clerk's exact callback, then delete the old secret/client as supported. Revoke the OAuth client immediately on compromise; this does not alter Clerk keys in another tier.

Recommended review intervals are 90 days for long-lived service credentials and after any owner/permission change; provider-enforced shorter lifetimes take precedence. Rotate immediately after suspected disclosure, staff/vendor offboarding, accidental logging, or use outside its intended tier.

## Repository and CI safeguards

- `.gitignore` excludes `.env`, `.env.*` at every project level (while allowing `.env.example`), private-key/certificate containers, and credential/service-account JSON filename patterns. Examples contain placeholders and fixed public-safe defaults only.
- Secret scanning must run on pull requests and protected branches. Block pushes containing private keys, common token formats, database URLs with credentials, or newly tracked environment files. Review staged changes with a scanner before commit.
- CI fixtures must be synthetic and non-routable. Tests must never require provider secrets. Do not dump `env`, request authorization headers, database URLs, SMTP exceptions containing credentials, or credential JSON.
- Production GitHub Environments require reviewer approval and branch protection. Pin third-party Actions to reviewed immutable SHAs when deployment workflows are rebuilt, and keep job `permissions` minimal.
- If a secret is committed, removing the line is insufficient: revoke it immediately, rotate the affected credential, assess access/logs, and use an approved history-rewrite incident procedure if required. Notify collaborators to discard affected clones. Do not reuse the replacement value during history cleanup.

## Review gate before provisioning

Repository review completed for this artifact: target keys are separated from legacy Firebase/Cloud Run/Cloud SQL inputs; D/S/P isolation is explicit; examples and ignore rules are aligned; no secret value is intentionally present in this change. The infrastructure/security review must record the following outside Git if names contain sensitive operational details:

- [ ] Application owner approves required/optional features, including SMTP and chat.
- [ ] Security owner approves tier boundaries, credential methods, IAM scopes, CORS and Clerk authorized parties.
- [ ] Azure owner approves runtime/migration roles, TLS mode, networking path, backup and revocation plan.
- [ ] GCS owner approves bucket access, CORS, lifecycle/versioning and service-account permissions.
- [ ] Clerk owner approves applications, domains, Google callbacks, claim template, administrator assignment and disabled-webhook decision.
- [ ] Delivery owner approves Vercel scopes, stable staging origin, GitHub Environment protection and Modal service-user permissions.
- [ ] Final D/S/P domain, API endpoint, bucket, database and provider identifiers have been substituted in platform configuration—not committed to this document.
- [ ] A dry-run confirms each workload receives only the Secret groups it consumes and CI logs mask derived values.

Provisioning must not begin until all boxes are approved. Any new integration or key requires a matrix update and another review first.

## Platform references

- Modal: [environments](https://modal.com/docs/guide/environments), [Secrets](https://modal.com/docs/guide/secrets), [service-user permissions](https://modal.com/docs/guide/service-users), and [GitHub Actions deployment](https://modal.com/docs/guide/useful-snippets)
- Vercel: [environment scopes](https://vercel.com/docs/environment-variables), [Vite variables](https://vercel.com/docs/frameworks/frontend/vite), and [Git deployments](https://vercel.com/docs/deployments/overview)
- Clerk: [production domains and authorized parties](https://clerk.com/docs/guides/development/deployment/production), [webhooks](https://clerk.com/docs/guides/development/webhooks/overview), [key rotation](https://clerk.com/docs/guides/secure/rotate-api-keys), and [Google sign-in](https://clerk.com/docs/guides/configure/auth-strategies/social-connections/google)
- Azure PostgreSQL: [TLS configuration](https://learn.microsoft.com/azure/postgresql/security/security-tls-how-to-connect) and [Microsoft Entra authentication](https://learn.microsoft.com/azure/postgresql/security/security-entra-concepts)
- GCS: [IAM](https://cloud.google.com/storage/docs/access-control/iam), [CORS](https://cloud.google.com/storage/docs/cross-origin), and [service-account key practices](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)
