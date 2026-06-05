import { useMemo } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { StatusPanel } from "../../components/StatusPanel";

export function Login() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { isReady, isAuthenticated, login, error, clearError, isConfigured } = useAuth();

  const redirectTo = searchParams.get("redirectTo") || "/admin/dashboard";
  const visibleError = useMemo(() => {
    if (typeof location.state?.error === "string" && location.state.error.trim()) {
      return location.state.error;
    }
    return error;
  }, [error, location.state]);

  if (isReady && isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return (
    <main className="page">
      <div className="container">
        <section className="page-hero fade-up">
          <div className="page-hero__panel admin-login-panel">
            <span className="eyebrow-dark">Admin access</span>
            <h1>Sign in to manage packages</h1>
            <p>
              Admin pages use Keycloak authentication. Public pages remain open,
              but package-management routes require a valid bearer token.
            </p>

            {!isReady ? (
              <StatusPanel
                title="Preparing login"
                message="Loading the Keycloak client and checking for an existing admin session."
              />
            ) : null}

            {visibleError ? (
              <StatusPanel
                title="Login failed"
                message={visibleError}
                tone="error"
              />
            ) : null}

            {!isConfigured ? (
              <StatusPanel
                title="Missing Keycloak configuration"
                message="Add VITE_KEYCLOAK_URL, VITE_KEYCLOAK_REALM, and VITE_KEYCLOAK_CLIENT_ID to the frontend environment."
                tone="error"
              />
            ) : null}

            <div className="hero__actions">
              <button
                className="button"
                type="button"
                onClick={() => {
                  clearError();
                  login(redirectTo);
                }}
                disabled={!isReady || !isConfigured}
              >
                Log in with Keycloak
              </button>
              <Link className="button-secondary" to="/">
                Back to public site
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
