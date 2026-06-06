import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { StatusPanel } from "./StatusPanel";

export function ProtectedAdminRoute({ children }) {
  const { isAdmin, adminClaimName, logout } = useAuth();

  return (
    <ProtectedRoute>
      {isAdmin ? (
        children
      ) : (
        <main className="page">
          <div className="container">
            <StatusPanel
              title="Admin claim required"
              message={`Your account is signed in, but the Firebase custom claim "${adminClaimName}" is missing or false.`}
              tone="error"
              action={(
                <>
                  <button className="button" type="button" onClick={() => logout("/admin/login")}>
                    Sign out
                  </button>
                  <Link className="button-secondary" to="/">
                    Back to public site
                  </Link>
                </>
              )}
            />
          </div>
        </main>
      )}
    </ProtectedRoute>
  );
}
