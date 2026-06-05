import { ProtectedRoute } from "./ProtectedRoute";

export function ProtectedAdminRoute({ children }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
