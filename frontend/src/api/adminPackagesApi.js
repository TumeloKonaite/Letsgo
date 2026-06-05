import { apiBaseUrl } from "../lib/api";

function normalizeValidationErrors(detail) {
  if (!Array.isArray(detail)) {
    return {};
  }

  return detail.reduce((fieldErrors, item) => {
    const location = Array.isArray(item?.loc) ? item.loc : [];
    const fieldName = location[0] === "body" ? location.at(-1) : null;
    const message = typeof item?.msg === "string" ? item.msg.trim() : "";

    if (!fieldName || !message || fieldName in fieldErrors) {
      return fieldErrors;
    }

    fieldErrors[fieldName] = message;
    return fieldErrors;
  }, {});
}

function buildErrorMessage(payload, fallbackMessage) {
  if (typeof payload?.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }

  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail
      .map((item) => (typeof item?.msg === "string" ? item.msg.trim() : ""))
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return fallbackMessage;
}

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
    let payload = null;
    let message = "Admin package request failed.";
    let fieldErrors = {};

    try {
      payload = await response.json();
      message = buildErrorMessage(payload, message);
      fieldErrors = normalizeValidationErrors(payload?.detail);
    } catch {
      message = response.statusText || message;
    }

    if (response.status === 401) {
      message = "Your admin session is no longer valid. Please sign in again.";
    }

    const error = new Error(message);
    error.status = response.status;
    error.fieldErrors = fieldErrors;
    error.payload = payload;
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

export function getAdminPackage(id, getAccessToken) {
  return adminPackagesRequest(`/api/admin/packages/${id}`, getAccessToken);
}

export function createPackage(payload, getAccessToken) {
  return adminPackagesRequest("/api/admin/packages", getAccessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updatePackage(id, payload, getAccessToken) {
  return adminPackagesRequest(`/api/admin/packages/${id}`, getAccessToken, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
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
