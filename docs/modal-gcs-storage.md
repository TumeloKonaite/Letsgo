# Private GCS storage for Modal

## Inventory and completion status

The retained bucket recorded in `rebuild-dependencies.md` is
`letsgosa-package-images`. Its owning project, current IAM/public-access policy,
location, and retention policy have **not been verified against GCP**. Obtain
Issue 1 owner confirmation before changing its policy. Do not move or delete
existing objects. The application requires only package images; conversation
persistence is not implemented by this adapter.

Set `GCS_OBJECT_PREFIX=staging/` for the proposed staging namespace. New names
are `staging/packages/<sanitized-slug>/<sanitized-name>-<uuid>.<jpg|png|webp>`.
Confirm this namespace is unused before provisioning. Other environments need
separate identities and disjoint prefixes. No list or bucket metadata access is
needed at runtime. Existing objects outside the configured prefix are not managed.

Implemented locally: explicit credential selection, prefix checks, create-only
uploads, private signed reads, deletion, sanitized provider/authentication errors,
and automated tests. Pending external access: bucket confirmation, dedicated
identity creation, actual federation exchange, Modal Secret attachment, staging
lifecycle, negative IAM tests, CORS review and deployed artifact/log inspection.
No service-account key has been issued, and no fallback decision has been made.
The local gcloud wrapper failed to list active credentials and no Modal CLI or
deployment entrypoint was available. This is an execution blocker, not evidence
that federation is unsupported.

## Configuration and Modal attachment

Required: `STORAGE_PROVIDER=gcs`, `GCS_PROJECT_ID`, `GCS_BUCKET_NAME`, and
`GCS_OBJECT_PREFIX` (safe path segments ending in `/`). `GCP_PROJECT_ID` remains
a compatibility alias; prefer `GCS_PROJECT_ID`. `GCS_PUBLIC_BASE_URL` is obsolete.
The runtime never searches metadata servers or implicit default credentials.

Choose exactly one explicit credential source:

- Preferred: `GCS_WIF_AUDIENCE=//iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER`
  and `GCS_SERVICE_ACCOUNT_EMAIL=modal-storage-staging@PROJECT_ID.iam.gserviceaccount.com`.
  The subject token comes from `MODAL_IDENTITY_TOKEN` only.
- Conditional fallback: `GCP_SERVICE_ACCOUNT_JSON` supplied in memory by Modal
  Secrets. Clear WIF variables, including the service-account email (local signing
  then uses the key). No credential file or build-time materialization is needed.
- Explicit mounted credential file: `GOOGLE_APPLICATION_CREDENTIALS` (absolute
  path in deployed environments). Never package the file in an image.

`GCS_CREDENTIALS_SECRET_NAME=letsgosa-gcs-staging` is deployment metadata, not
credential material. The Modal entrypoint must resolve and attach it explicitly:

```python
storage_secret = modal.Secret.from_name(
    os.environ["GCS_CREDENTIALS_SECRET_NAME"], environment_name="staging"
)
# Add storage_secret to the ASGI function's secrets=[...] alongside its existing
# runtime groups. Never pass os.environ or credential values to Image.env/build.
```

The Secret contains the storage configuration above. WIF needs no stored private
key. Settings validate before serving requests; the first operation constructs
the explicitly authenticated client. A missing/expired Modal token fails closed.
The deployment must run the existing full application startup validation too.

## Federation evaluation and provisioning

As of 2026-09-05, [Modal documents](https://modal.com/docs/guide/oidc-integration)
OIDC tokens injected into Functions. The issuer is `https://oidc.modal.com`,
audience `oidc.modal.com`, and claims identify workspace, environment, app and
function. [Google supports OIDC federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-other-providers).
This supports a keyless design, but does not prove this staging deployment works.

Use an authorized provisioning account for the following steps, never as the
runtime identity. Fill placeholders from verified inventory, not old secrets:

```sh
gcloud iam service-accounts create modal-storage-staging --project="$GCS_PROJECT_ID" --display-name="Modal staging image storage"
gcloud iam roles create modalImageObjects --project="$GCS_PROJECT_ID" --title="Application image objects" --permissions=storage.objects.create,storage.objects.get,storage.objects.delete --stage=GA
gcloud storage buckets add-iam-policy-binding "gs://$GCS_BUCKET_NAME" --member="serviceAccount:$GCS_SERVICE_ACCOUNT_EMAIL" --role="projects/$GCS_PROJECT_ID/roles/modalImageObjects" --condition="title=staging-images,expression=resource.name.startsWith('projects/_/buckets/$GCS_BUCKET_NAME/objects/${GCS_OBJECT_PREFIX}packages/')"
```

Do not grant Storage Admin or object list/update permissions. Uploads use
`if_generation_match=0`, so they cannot overwrite an existing name. Inspect
inherited IAM as well as bucket policy: a narrow binding cannot cancel a broad
inherited grant. Confirm uniform bucket-level access and public access prevention
before deployment. Do not blindly enable uniform access on a retained bucket
until existing ACL dependencies are reviewed. No public IAM bindings may be added.

Enable STS and IAM Credentials APIs. Create a dedicated workload identity pool
and OIDC provider with the issuer and allowed audience above. Map
`google.subject=assertion.sub` and `attribute.workload` to a fixed label such as
`modal-storage-staging`. Require **all** verified workspace_id, environment_id,
app_id and function_name values in the provider's attribute condition. Do not
trust the workspace alone or arbitrary app names. Bind
`roles/iam.workloadIdentityUser` on this service account only to
`principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/attribute.workload/modal-storage-staging`.

Signed URLs use IAM signBlob for WIF. Create a separate custom role containing
only `iam.serviceAccounts.signBlob` and bind it on the dedicated service account
to that same service account (self-signing after impersonation). Do not grant
project-wide Token Creator. The object role supplies permission to read the
signed object. [GCS signing documentation](https://docs.cloud.google.com/storage/docs/access-control/signing-urls-with-helpers)
describes this permission requirement.

Run the real ASGI function using this configuration. Verify exchange,
impersonation, upload, signing, read and deletion. Repeat after access-token
expiry and with an aged container: Modal subject-token refresh/lifetime must be
verified, not assumed. Test another app/function/environment to ensure its token
cannot impersonate the account. Record timestamps, revision and pass/fail only;
never print JWTs, access tokens or signed URLs.

If testing establishes a platform limitation, record the specific failed step,
sanitized error, runtime/SDK versions, attempts to resolve it, owner, expiry and
retest date before selecting a key fallback. Lack of local deployment access is
not such a limitation. Create a key only after this evaluation, deliver it directly
to the environment-scoped Modal Secret via a secure operator workflow, and
remove any temporary copy. Never put values in shell history or CLI arguments.

## Private browser reads and CORS

Database records hold unsigned canonical references and storage keys. API
responses generate 15-minute V4 GET signed URLs; refetch API data after expiry.
Possession of a signed URL authorizes its read until expiry. Package read APIs
currently distribute these capabilities to their existing audience, including
public catalog readers; this is not user-private media. If image visibility must
be restricted to authenticated users, an API authorization change is required.

Browsers upload/delete through authenticated backend APIs. Do not enable GCS
browser writes. Ordinary image display does not require CORS; if frontend fetch
or canvas use requires it, review existing bucket CORS and merge only exact
approved frontend origins with `GET`, `HEAD`, response header `Content-Type`, and
`maxAgeSeconds: 300`. Never use `*`. Apply a reviewed JSON file with
`gcloud storage buckets update gs://BUCKET --cors-file=FILE`. CORS is not IAM.
Approved staging origins have not been supplied, so no policy was applied.

## Staging validation and evidence

1. Authenticate as a staging application administrator. Upload a small JPEG,
   PNG or WebP through `/api/admin/packages/{package_id}/images` (verify the
   router's deployed prefix), recording only image ID and pass/fail.
2. Using the provisioning verifier, confirm the exact new object is inside
   `${GCS_OBJECT_PREFIX}packages/` in the retained bucket. Do not list unrelated
   names into logs.
3. Fetch fresh image data through the application API. GET the returned signed
   URL and compare bytes/content type in memory. Do not log the URL.
4. Delete through the image API; verify the exact object is absent using the
   verifier (or an authenticated read returning 404). An old signed URL must
   no longer retrieve live bytes; cached browser copies may remain.
5. With a separate identity having no relevant roles, attempt direct create,
   unsigned get and delete for a unique disposable name in the protected prefix.
   Expect denial for all three. Never negative-test deleting a retained object.
   Also confirm unauthenticated application upload/delete is denied. A leaked
   signed URL is a bearer capability, not an unsigned negative IAM test.
6. Confirm the dedicated account cannot operate outside its prefix, list objects,
   change IAM, or read bucket metadata. Test token exchange from the wrong Modal
   environment/function. Inspect inherited IAM and public/ACL grants.
7. Review application, Modal and HTTP access logs and built image layers for
   credential material; use detectors that report only file/location/count, never
   matching content. Check secrets were not passed as build args or frontend
   variables. Avoid debug HTTP logging and full request/exception dumps. Inspect
   signed-URL query logging at proxies as well. Local source exclusions alone do
   not establish deployed artifact safety.

Record each step's result, deployed revision, environment and date here after
execution. **No staging result has been recorded yet.** Clean up only the unique
validation objects created by this procedure.

## Rotation, revocation and troubleshooting

For WIF, revoke the workloadIdentityUser binding or disable the provider; disable
the dedicated service account and remove its bucket binding for an incident.
Already minted tokens can remain usable until expiry; remove data permissions
for prompt denial. Review issued signed URLs (15-minute maximum), caches and
Google IAM propagation delays. Rotate trust by creating a replacement provider,
testing it, switching the Modal configuration, then disabling the old provider.

For a fallback key, create a replacement for the same dedicated account, update
the Modal Secret, redeploy all consumers and validate the full lifecycle. Disable
the old key, confirm no active consumer depends on it, then delete it with
`gcloud iam service-accounts keys delete KEY_ID --iam-account=SERVICE_ACCOUNT`.
For compromise, disable the key immediately, remove object permissions/disable
the account, redeploy and inspect audit logs; do not wait for replacement tests.
Deleting only the Modal Secret does not revoke a GCP key or running containers.

Startup configuration failures identify variable names only. Exchange failures:
check issuer, audience, verified claim restrictions and clock. Impersonation
failure: check the exact principal binding and enabled API. Signing failure:
check self signBlob permission. Object failure: check prefix condition, retention
policy, bucket name and object permissions using the operator identity. Do not
"fix" errors by broadening roles. An expired signed URL requires fresh API data.
Provider details and credential contents must remain out of responses and logs.

## Local validation record (2026-09-05)

`pytest tests/infrastructure/storage tests/core/test_config.py tests/domain/packages`
passed: **61 tests**. Ruff checks and `git diff --check` passed. These tests use
synthetic credentials/mocks, not a live federation exchange. The full API suite
stalled without reporting a completed test after its fixture configuration was
updated and was interrupted; API integration validation is not claimed.
