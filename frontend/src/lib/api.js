// Provide public package, enquiry, and chat requests through the shared HTTP client.

import { apiBaseUrl, request } from "../api/client";

export function getPackages() {
  return request("/api/packages", {}, "Something went wrong while loading data.");
}

export function getPackageBySlug(slug) {
  return request(
    `/api/packages/${encodeURIComponent(slug)}`,
    {},
    "Something went wrong while loading data."
  );
}

export function submitContactRequest(payload) {
  return request(
    "/api/contact",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Unable to send contact request."
  );
}

export function submitChatMessage(payload, options = {}) {
  return request(
    "/chat",
    {
      method: "POST",
      body: JSON.stringify(payload),
      ...options,
    },
    "Unable to reach the travel assistant."
  );
}
