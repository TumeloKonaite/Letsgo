import { useMemo } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { StatusPanel } from "../../components/StatusPanel";

export function Login() {
  // Start Clerk sign-in and preserve the originally requested admin route.
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
              Admin pages use Clerk authentication. Public pages remain open, but
              package-management routes require a valid Clerk session token.
            </p>

            {!isReady ? (
              <StatusPanel
                title="Preparing login"
                message="Checking for an existing Clerk admin session."
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
                title="Missing Clerk configuration"
                message="Add the public Vite Clerk configuration before opening admin pages."
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
                Sign in with Google
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
