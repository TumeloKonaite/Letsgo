// Wrap protected package and image endpoints for the admin screens.

import { authenticatedRequest } from "./client";

function adminPackagesRequest(path, options = {}) {
  return authenticatedRequest(path, options, "Admin package request failed.");
}

export function getAdminPackages() {
  return adminPackagesRequest("/api/admin/packages");
}

export function getAdminPackage(id) {
  return adminPackagesRequest(`/api/admin/packages/${id}`);
}

export function createPackage(payload) {
  return adminPackagesRequest("/api/admin/packages", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updatePackage(id, payload) {
  return adminPackagesRequest(`/api/admin/packages/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAdminPackageImages(packageId) {
  return adminPackagesRequest(`/api/admin/packages/${packageId}/images`);
}

export function uploadAdminPackageImage(packageId, formData) {
  return adminPackagesRequest(`/api/admin/packages/${packageId}/images`, {
    method: "POST",
    body: formData,
  });
}

export function deleteAdminPackageImage(packageId, imageId) {
  return adminPackagesRequest(`/api/admin/packages/${packageId}/images/${imageId}`, {
    method: "DELETE",
  });
}

export function deletePackage(id) {
  return adminPackagesRequest(`/api/admin/packages/${id}`, {
    method: "DELETE",
  });
}

export function publishPackage(id) {
  return adminPackagesRequest(`/api/admin/packages/${id}/publish`, {
    method: "PATCH",
  });
}

export function unpublishPackage(id) {
  return adminPackagesRequest(`/api/admin/packages/${id}/unpublish`, {
    method: "PATCH",
  });
}
