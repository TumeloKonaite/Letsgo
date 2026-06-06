import { authenticatedRequest } from "../api/client";

export function getCurrentAdmin() {
  return authenticatedRequest("/api/admin/auth/me", {}, "Admin request failed.");
}
