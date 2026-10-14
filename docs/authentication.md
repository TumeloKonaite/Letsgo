# Authentication boundary

`AuthenticationProvider` in `app.domain.auth.provider` verifies an opaque bearer
credential and returns `AuthenticatedUser`, or raises `AuthenticationError`.
FastAPI's `get_bearer_token` extracts credentials, `get_current_user` invokes the
provider, and `require_admin` separately applies the application's admin role rule.
Missing, malformed, expired and invalid credentials receive the same sanitized
401 response with `WWW-Authenticate: Bearer`. Authenticated users without the
admin role receive 403. Providers must never log tokens or raw claims.

## Identity contract

The immutable user contains `subject`, `provider`, optional `internal_user_id`,
`username`, `email`, and immutable application `roles`. `subject` remains the
provider's stable subject, not an internal database ID. `user_identities` has a
unique `(provider, subject)` key and points to an `application_users` row. On the
first valid Clerk request, the backend provisions both rows and returns the new
application UUID as `internal_user_id`; later requests resolve the same UUID.
Verified profile fields are refreshed on sign-in. Email and username are mutable
display data and are never automatic link keys. Linking another provider to an
existing user requires a future explicit, authenticated account-linking workflow.
Never equate subjects from different providers even when their strings match.

Raw claims have been removed. `/api/admin/auth/me` preserves `sub`, `username`
and `email`, and replaces `claims` with `roles`, `provider`, and
`internal_user_id`. Consumers of the old `claims` response must use normalized
roles instead. The endpoint requires authentication; administration routes
additionally require the admin role.

## Provider wiring

This checkout already used Clerk before this refactor and has no Firebase auth
adapter or Firebase identity migration to preserve. Clerk remains configured;
this change does not activate a new production provider. Its adapter lives in
`app.auth.clerk_auth`, an authentication infrastructure module. It uses Clerk's
official Python backend SDK `authenticate_request` in networkless mode with the
configured PEM key. The SDK restricts accepted credentials to session tokens,
RS256 signatures, expiry and the configured authorized browser parties (`azp`);
the adapter additionally requires `sub`, `iss`, `azp`, `iat`, and `exp` and checks
the issuer exactly. The existing configuration uses no JWT audience, so tokens
declaring an audience are rejected. A deployment using audience-bearing tokens
must explicitly configure and validate the intended audience before accepting them.
Only the configured boolean admin claim equal to `True` maps to the application's
`admin` role. Arbitrary `roles` or internal ID claims are not trusted.

To introduce another provider (including Firebase, or another Clerk integration):

1. Implement `AuthenticationProvider` in authentication infrastructure. Delegate
   signature, issuer, audience, expiry and other provider trust validation to its
   SDK or verifier. Convert validation failures to `AuthenticationError`.
2. Normalize validated claims inside that adapter. Define explicit mappings to
   application roles; do not pass SDK objects or raw claims to services or routes.
3. Validate its configuration at startup and inject the instance into
   `app.state.authentication_provider` in the composition root (`app.main`).
   Update startup configuration validation for the selected provider as needed.
4. Test signature and trust failures, claim normalization, and identifier
   semantics. Override `get_authentication_provider` in route tests to exercise
   provider-independent behavior. Existing route and service code need no changes.

Historical Firebase identity migration and user-initiated cross-provider linking
remain outside this change.
