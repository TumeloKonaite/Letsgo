import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  buildUserFromToken,
  ensureFreshToken,
  getKeycloak,
  getKeycloakConfigError,
  initializeKeycloak,
  isKeycloakConfigured,
} from "../lib/keycloak";

const AuthContext = createContext(null);

function normalizeErrorMessage(error, fallbackMessage) {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallbackMessage;
}

export function AuthProvider({ children }) {
  const [isReady, setIsReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    if (!isKeycloakConfigured()) {
      setIsReady(true);
      return undefined;
    }

    async function bootstrapAuth() {
      try {
        const keycloak = await initializeKeycloak();

        keycloak.onAuthSuccess = async () => {
          try {
            const nextToken = await ensureFreshToken();
            if (!isMounted) {
              return;
            }
            setToken(nextToken);
            setUser(buildUserFromToken(keycloak));
            setIsAuthenticated(Boolean(keycloak.authenticated));
            setError("");
          } catch (refreshError) {
            if (!isMounted) {
              return;
            }
            setError(
              normalizeErrorMessage(
                refreshError,
                "Your admin session could not be refreshed."
              )
            );
          }
        };

        keycloak.onAuthLogout = () => {
          if (!isMounted) {
            return;
          }
          setToken(null);
          setUser(null);
          setIsAuthenticated(false);
        };

        keycloak.onTokenExpired = () => {
          ensureFreshToken().catch(() => {
            if (!isMounted) {
              return;
            }
            setError("Your admin session expired. Please sign in again.");
            setToken(null);
            setUser(null);
            setIsAuthenticated(false);
          });
        };

        if (!isMounted) {
          return;
        }

        setToken(keycloak.token ?? null);
        setUser(buildUserFromToken(keycloak));
        setIsAuthenticated(Boolean(keycloak.authenticated));
        setError("");
      } catch (authError) {
        if (!isMounted) {
          return;
        }
        setError(
          normalizeErrorMessage(
            authError,
            "Unable to initialize the admin login flow."
          )
        );
      } finally {
        if (isMounted) {
          setIsReady(true);
        }
      }
    }

    bootstrapAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const value = useMemo(
    () => ({
      isReady,
      isAuthenticated,
      user,
      token,
      error,
      isConfigured: isKeycloakConfigured(),
      async login(redirectPath = "/admin/dashboard") {
        if (!isKeycloakConfigured()) {
          setError(getKeycloakConfigError().message);
          return;
        }

        try {
          const keycloak = await initializeKeycloak({ checkSso: false });
          setError("");
          await keycloak.login({
            redirectUri: new URL(redirectPath, window.location.origin).toString(),
            scope: "openid profile email",
          });
        } catch (loginError) {
          setError(
            normalizeErrorMessage(
              loginError,
              "Unable to start Keycloak login. Check the frontend client configuration."
            )
          );
        }
      },
      async logout(redirectPath = "/admin/login") {
        if (!isKeycloakConfigured()) {
          setToken(null);
          setUser(null);
          setIsAuthenticated(false);
          return;
        }

        const keycloak = getKeycloak();
        setToken(null);
        setUser(null);
        setIsAuthenticated(false);
        setError("");
        await keycloak.logout({
          redirectUri: new URL(redirectPath, window.location.origin).toString(),
        });
      },
      async getAccessToken() {
        if (!isKeycloakConfigured()) {
          throw getKeycloakConfigError();
        }

        const nextToken = await ensureFreshToken();
        const keycloak = getKeycloak();

        if (!nextToken || !keycloak.authenticated) {
          setToken(null);
          setUser(null);
          setIsAuthenticated(false);
          throw new Error("Your admin session is no longer valid. Please sign in again.");
        }

        setToken(nextToken);
        return nextToken;
      },
      clearError() {
        setError("");
      },
    }),
    [error, isAuthenticated, isReady, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
}
