import { apiBaseUrl } from "./api";

async function adminRequest(path, getAccessToken, options = {}) {
  const accessToken = await getAccessToken();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = "Admin request failed.";

    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string" && payload.detail.trim()) {
        message = payload.detail;
      }
    } catch {
      message = response.statusText || message;
    }

    if (response.status === 401) {
      message = "Your admin session is no longer valid. Please sign in again.";
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function getCurrentAdmin(getAccessToken) {
  return adminRequest("/api/admin/auth/me", getAccessToken);
}

export function getAdminPackages(getAccessToken) {
  return adminRequest("/api/admin/packages", getAccessToken);
}
