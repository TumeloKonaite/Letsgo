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
provider's stable subject, not an internal database ID. Identity must be keyed by
`(provider, subject)` when supporting multiple providers. Never equate a Firebase
UID and a Clerk subject, even if their strings match. No identity migration or
internal ID lookup is introduced here; `internal_user_id` remains `None` until an
application-owned mapping is available.

Raw claims have been removed. `/api/admin/auth/me` preserves `sub`, `username`
and `email`, and replaces `claims` with `roles`, `provider`, and
`internal_user_id`. Consumers of the old `claims` response must use normalized
roles instead. The endpoint requires authentication; administration routes
additionally require the admin role.

## Provider wiring

This checkout already used Clerk before this refactor and has no Firebase auth
adapter or Firebase identity migration to preserve. Clerk remains configured;
this change does not activate a new production provider. Its adapter lives in
`app.auth.clerk_auth`, an authentication infrastructure module. It verifies RS256
signatures, issuer, expiry and the configured authorized browser parties (`azp`).
The existing configuration uses no JWT audience; tokens declaring an audience
are rejected by PyJWT. A deployment using audience-bearing tokens must explicitly
configure and validate the intended audience in the adapter before accepting them.
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

Switching providers still requires a separate identity-linking/migration design
for records owned by existing subjects. It is outside this change.
