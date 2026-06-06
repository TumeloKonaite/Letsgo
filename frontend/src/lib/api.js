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
