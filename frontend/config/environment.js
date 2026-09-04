const DEVELOPMENT_API_BASE_URL = "http://localhost:8000";

export const PUBLIC_ENVIRONMENT_KEYS = Object.freeze([
  "VITE_API_BASE_URL",
  "VITE_CLERK_PUBLISHABLE_KEY",
  "VITE_CLERK_SIGN_IN_URL",
  "VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL",
  "VITE_CLERK_SIGN_OUT_FALLBACK_REDIRECT_URL",
  "VITE_CLERK_ADMIN_CLAIM",
]);

function requiredValue(environment, name) {
  // Read a required public value and reject blank strings.
  const value = environment[name]?.trim();
  if (!value) {
    throw new Error(`${name} is required.`);
  }
  return value;
}

function validateAbsoluteUrl(name, value, { requireHttps }) {
  // Accept only origin-style HTTP URLs that are safe for browser requests.
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name} must be a valid absolute URL.`);
  }

  const allowedProtocols = requireHttps ? ["https:"] : ["http:", "https:"];
  if (
    !allowedProtocols.includes(parsed.protocol) ||
    !parsed.hostname ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(
      `${name} must be an absolute ${requireHttps ? "HTTPS" : "HTTP(S)"} origin without credentials, a path, query, or fragment.`
    );
  }
  if (value.endsWith("/")) {
    throw new Error(`${name} must not have a trailing slash.`);
  }
  return value;
}

function validateRoute(name, value) {
  // Keep Clerk redirects inside this frontend application.
  if (!value.startsWith("/") || value.startsWith("//")) {
    throw new Error(`${name} must be an application-relative path.`);
  }
  return value;
}

export function resolveFrontendEnvironment(mode, environment) {
  // Validate the complete public build configuration before Vite bundles it.
  const isDevelopment = mode === "development";
  const unexpectedPublicKeys = Object.keys(environment).filter(
    (name) => name.startsWith("VITE_") && !PUBLIC_ENVIRONMENT_KEYS.includes(name)
  );
  if (unexpectedPublicKeys.length > 0) {
    throw new Error(
      `Unsupported public frontend configuration: ${unexpectedPublicKeys.sort().join(", ")}.`
    );
  }

  const configuredApiBaseUrl = environment.VITE_API_BASE_URL?.trim();
  const apiBaseUrl = configuredApiBaseUrl || (isDevelopment ? DEVELOPMENT_API_BASE_URL : "");
  if (!apiBaseUrl) {
    throw new Error(
      "VITE_API_BASE_URL is required for non-development frontend builds."
    );
  }
  validateAbsoluteUrl("VITE_API_BASE_URL", apiBaseUrl, {
    requireHttps: !isDevelopment,
  });

  const publishableKey = requiredValue(environment, "VITE_CLERK_PUBLISHABLE_KEY");
  if (!/^pk_(test|live)_/.test(publishableKey)) {
    throw new Error("VITE_CLERK_PUBLISHABLE_KEY has an invalid format.");
  }

  const adminClaim = requiredValue(environment, "VITE_CLERK_ADMIN_CLAIM");
  if (!/^[A-Za-z_][A-Za-z0-9_.-]*$/.test(adminClaim)) {
    throw new Error("VITE_CLERK_ADMIN_CLAIM must be a valid claim name.");
  }

  return Object.freeze({
    apiBaseUrl,
    clerkPublishableKey: publishableKey,
    clerkSignInUrl: validateRoute(
      "VITE_CLERK_SIGN_IN_URL",
      requiredValue(environment, "VITE_CLERK_SIGN_IN_URL")
    ),
    clerkSignInFallbackRedirectUrl: validateRoute(
      "VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL",
      requiredValue(environment, "VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL")
    ),
    clerkSignOutFallbackRedirectUrl: validateRoute(
      "VITE_CLERK_SIGN_OUT_FALLBACK_REDIRECT_URL",
      requiredValue(environment, "VITE_CLERK_SIGN_OUT_FALLBACK_REDIRECT_URL")
    ),
    clerkAdminClaim: adminClaim,
  });
}
