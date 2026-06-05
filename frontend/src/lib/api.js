const DEFAULT_API_BASE_URL = "http://localhost:8000";

const configuredBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.trim() ||
  import.meta.env.VITE_LETSGO_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;

export const apiBaseUrl = configuredBaseUrl.replace(/\/+$/, "");

async function request(path) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let message = "Something went wrong while loading data.";

    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string" && payload.detail.trim()) {
        message = payload.detail;
      }
    } catch {
      message = response.statusText || message;
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return response.json();
}

export function getPackages() {
  return request("/api/packages");
}

export function getPackageBySlug(slug) {
  return request(`/api/packages/${encodeURIComponent(slug)}`);
}
