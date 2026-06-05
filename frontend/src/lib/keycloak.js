import Keycloak from "keycloak-js";

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL?.trim() || "",
  realm: import.meta.env.VITE_KEYCLOAK_REALM?.trim() || "",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID?.trim() || "",
};

const hasCompleteConfig = Object.values(keycloakConfig).every(Boolean);

let keycloakInstance = null;
let initPromise = null;
const KEYCLOAK_INIT_TIMEOUT_MS = 8000;

function getMissingConfigError() {
  return new Error(
    "Keycloak is not configured. Set VITE_KEYCLOAK_URL, VITE_KEYCLOAK_REALM, and VITE_KEYCLOAK_CLIENT_ID."
  );
}

export function isKeycloakConfigured() {
  return hasCompleteConfig;
}

export function getKeycloak() {
  if (!hasCompleteConfig) {
    throw getMissingConfigError();
  }

  if (!keycloakInstance) {
    keycloakInstance = new Keycloak(keycloakConfig);
  }

  return keycloakInstance;
}

function resetKeycloak() {
  keycloakInstance = null;
  initPromise = null;
}

function withInitTimeout(promise, message) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      window.setTimeout(() => {
        reject(new Error(message));
      }, KEYCLOAK_INIT_TIMEOUT_MS);
    }),
  ]);
}

export async function initializeKeycloak({ checkSso = false } = {}) {
  const keycloak = getKeycloak();

  if (!initPromise) {
    const initOptions = {
      pkceMethod: "S256",
      checkLoginIframe: false,
      ...(checkSso
        ? {
            onLoad: "check-sso",
            silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
          }
        : {}),
    };

    initPromise = keycloak
      .init(initOptions)
      .catch((error) => {
        resetKeycloak();
        throw error;
      });
  }

  try {
    await withInitTimeout(
      initPromise,
      checkSso
        ? "Keycloak session check timed out. Verify the Keycloak URL and frontend origin configuration in Keycloak."
        : "Keycloak login initialization timed out. Verify the Keycloak URL and frontend client redirect URIs."
    );
  } catch (error) {
    resetKeycloak();
    throw error;
  }

  return keycloak;
}

export async function ensureFreshToken(minValidity = 30) {
  const keycloak = getKeycloak();

  if (!keycloak.authenticated) {
    return null;
  }

  await keycloak.updateToken(minValidity);
  return keycloak.token ?? null;
}

export function buildUserFromToken(keycloak) {
  if (!keycloak?.tokenParsed) {
    return null;
  }

  const realmRoles = keycloak.tokenParsed.realm_access?.roles ?? [];
  const clientRoles = Object.values(keycloak.tokenParsed.resource_access ?? {}).flatMap(
    (resource) => resource.roles ?? []
  );
  const roles = Array.from(new Set([...realmRoles, ...clientRoles])).sort();

  return {
    id: keycloak.tokenParsed.sub ?? "",
    username:
      keycloak.tokenParsed.preferred_username ??
      keycloak.tokenParsed.name ??
      keycloak.tokenParsed.email ??
      "Admin",
    email: keycloak.tokenParsed.email ?? "",
    roles,
  };
}

export function getKeycloakConfigError() {
  return getMissingConfigError();
}
