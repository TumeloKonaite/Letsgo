import assert from "node:assert/strict";
import test from "node:test";

import { resolveFrontendEnvironment } from "../config/environment.js";

const clerkEnvironment = Object.freeze({
  VITE_CLERK_PUBLISHABLE_KEY: "pk_test_synthetic",
  VITE_CLERK_SIGN_IN_URL: "/admin/login",
  VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL: "/admin/dashboard",
  VITE_CLERK_SIGN_OUT_FALLBACK_REDIRECT_URL: "/admin/login",
  VITE_CLERK_ADMIN_CLAIM: "admin",
});

test("production build fails without VITE_API_BASE_URL", () => {
  assert.throws(
    () => resolveFrontendEnvironment("production", clerkEnvironment),
    /VITE_API_BASE_URL is required/
  );
});

test("production build fails with an invalid or insecure API URL", () => {
  for (const value of ["not-a-url", "http://api.example.invalid", "https://api.example.invalid/path"]) {
    assert.throws(() =>
      resolveFrontendEnvironment("production", {
        ...clerkEnvironment,
        VITE_API_BASE_URL: value,
      })
    );
  }
});

test("production build accepts an explicit HTTPS API origin", () => {
  const environment = resolveFrontendEnvironment("production", {
    ...clerkEnvironment,
    VITE_API_BASE_URL: "https://api.example.invalid",
  });

  assert.equal(environment.apiBaseUrl, "https://api.example.invalid");
});

test("the localhost API default is development-only", () => {
  assert.equal(
    resolveFrontendEnvironment("development", clerkEnvironment).apiBaseUrl,
    "http://localhost:8000"
  );
  assert.throws(() => resolveFrontendEnvironment("staging", clerkEnvironment));
});

test("legacy and secret-looking VITE variables are rejected", () => {
  assert.throws(
    () =>
      resolveFrontendEnvironment("production", {
        ...clerkEnvironment,
        VITE_API_BASE_URL: "https://api.example.invalid",
        VITE_LETSGO_API_BASE_URL: "https://legacy.example.invalid",
      }),
    /Unsupported public frontend configuration: VITE_LETSGO_API_BASE_URL/
  );
  assert.throws(
    () =>
      resolveFrontendEnvironment("production", {
        ...clerkEnvironment,
        VITE_API_BASE_URL: "https://api.example.invalid",
        VITE_CLERK_SECRET_KEY: "must-never-be-public",
      }),
    /Unsupported public frontend configuration: VITE_CLERK_SECRET_KEY/
  );
});
