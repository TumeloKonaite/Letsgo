import { Navigate, Outlet, useLocation } from "react-router-dom";

import { StatusPanel } from "../components/StatusPanel";
import { useAuth } from "./AuthProvider";

export function ProtectedRoute({ children }) {
  const location = useLocation();
  const { isReady, isAuthenticated, error, isConfigured } = useAuth();

  if (!isReady) {
    return (
      <main className="page">
        <div className="container">
          <StatusPanel
            title="Checking admin session"
            message="Validating your Firebase login before opening protected pages."
          />
        </div>
      </main>
    );
  }

  if (!isConfigured) {
    return (
      <main className="page">
        <div className="container">
          <StatusPanel
            title="Admin login unavailable"
            message="Set the frontend Firebase environment variables before opening admin pages."
            tone="error"
          />
        </div>
      </main>
    );
  }

  if (!isAuthenticated) {
    const redirectTo = `${location.pathname}${location.search}${location.hash}`;
    return (
      <Navigate
        to={`/admin/login?redirectTo=${encodeURIComponent(redirectTo)}`}
        replace
        state={error ? { error } : undefined}
      />
    );
  }

  return children ?? <Outlet />;
}
