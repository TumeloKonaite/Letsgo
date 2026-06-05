import { apiBaseUrl } from "../lib/api";

async function adminPackagesRequest(path, getAccessToken, options = {}) {
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
    let message = "Admin package request failed.";

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

export function getAdminPackages(getAccessToken) {
  return adminPackagesRequest("/api/admin/packages", getAccessToken);
}

export function deletePackage(id, getAccessToken) {
  return adminPackagesRequest(`/api/admin/packages/${id}`, getAccessToken, {
    method: "DELETE",
  });
}

export function publishPackage(id, getAccessToken) {
  return adminPackagesRequest(`/api/admin/packages/${id}/publish`, getAccessToken, {
    method: "PATCH",
  });
}

export function unpublishPackage(id, getAccessToken) {
  return adminPackagesRequest(`/api/admin/packages/${id}/unpublish`, getAccessToken, {
    method: "PATCH",
  });
}
