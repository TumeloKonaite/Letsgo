const DEFAULT_API_BASE_URL = "http://localhost:8000";

const configuredBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.trim() ||
  import.meta.env.VITE_LETSGO_API_BASE_URL?.trim() ||
  DEFAULT_API_BASE_URL;

export const apiBaseUrl = configuredBaseUrl.replace(/\/+$/, "");

let getAccessToken = null;
let handleUnauthorized = null;

function isJsonResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json");
}

async function parseResponsePayload(response) {
  if (response.status === 204) {
    return null;
  }

  if (isJsonResponse(response)) {
    return response.json();
  }

  const text = await response.text();
  return text ? { detail: text } : null;
}

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

function buildErrorMessage(response, payload, fallbackMessage) {
  if (response.status === 401) {
    return "Your admin session is no longer valid. Please sign in again.";
  }

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

  return response.statusText || fallbackMessage;
}

function buildHeaders(optionsHeaders, body, token) {
  const isMultipartBody =
    typeof FormData !== "undefined" && body instanceof FormData;

  return {
    Accept: "application/json",
    ...(body && !isMultipartBody ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...optionsHeaders,
  };
}

export function configureApiClient({
  getAccessToken: nextGetAccessToken = null,
  onUnauthorized: nextOnUnauthorized = null,
} = {}) {
  getAccessToken = nextGetAccessToken;
  handleUnauthorized = nextOnUnauthorized;
}

async function executeRequest(path, options = {}, fallbackMessage = "Request failed.") {
  const { requiresAuth = false, headers, body, ...requestOptions } = options;
  const accessToken = requiresAuth ? await getAccessToken?.() : null;

  if (requiresAuth && !accessToken) {
    const error = new Error("Your admin session is no longer valid. Please sign in again.");
    error.status = 401;
    throw error;
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...requestOptions,
    body,
    headers: buildHeaders(headers, body, accessToken),
  });

  const payload = await parseResponsePayload(response);

  if (!response.ok) {
    const error = new Error(buildErrorMessage(response, payload, fallbackMessage));
    error.status = response.status;
    error.payload = payload;
    error.fieldErrors = normalizeValidationErrors(payload?.detail);

    if (response.status === 401 && handleUnauthorized) {
      try {
        await handleUnauthorized(error);
      } catch {
        // Preserve the original request failure.
      }
    }

    throw error;
  }

  return payload;
}

export function request(path, options = {}, fallbackMessage) {
  return executeRequest(path, options, fallbackMessage);
}

export function authenticatedRequest(path, options = {}, fallbackMessage) {
  return executeRequest(path, { ...options, requiresAuth: true }, fallbackMessage);
}
