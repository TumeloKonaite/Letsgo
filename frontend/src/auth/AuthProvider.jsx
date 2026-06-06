import {
  useCallback,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { configureApiClient } from "../api/client";
import {
  getCurrentSession,
  getFirebaseAdminClaimName,
  getFirebaseAuth,
  getFirebaseConfigError,
  getFreshIdToken,
  isFirebaseConfigured,
  loginWithGoogle,
  logoutFromFirebase,
  subscribeToAuthChanges,
} from "../lib/firebaseAuth";

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
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [error, setError] = useState("");
  const adminClaimName = getFirebaseAdminClaimName();

  const applySession = useCallback((session) => {
    setToken(session.token);
    setUser(session.user);
    setIsAuthenticated(session.isAuthenticated);
    setIsAdmin(session.isAdmin);
  }, []);

  const clearSession = useCallback(() => {
    applySession({
      token: null,
      user: null,
      isAuthenticated: false,
      isAdmin: false,
    });
  }, [applySession]);

  useEffect(() => {
    let isMounted = true;
    let unsubscribe = () => {};

    if (!isFirebaseConfigured()) {
      setIsReady(true);
      return undefined;
    }

    try {
      unsubscribe = subscribeToAuthChanges(
        (session) => {
          if (!isMounted) {
            return;
          }
          applySession(session);
          setError("");
          setIsReady(true);
        },
        (authError) => {
          if (!isMounted) {
            return;
          }
          clearSession();
          setError(
            normalizeErrorMessage(
              authError,
              "Unable to initialize the admin login flow."
            )
          );
          setIsReady(true);
        }
      );
    } catch (authError) {
      setError(
        normalizeErrorMessage(
          authError,
          "Unable to initialize the admin login flow."
        )
      );
      setIsReady(true);
    }

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [applySession, clearSession]);

  const login = useCallback(async () => {
    if (!isFirebaseConfigured()) {
      setError(getFirebaseConfigError().message);
      return;
    }

    try {
      setError("");
      await loginWithGoogle();
    } catch (loginError) {
      setError(
        normalizeErrorMessage(
          loginError,
          "Unable to start Google sign-in. Check the Firebase Auth configuration."
        )
      );
    }
  }, []);

  const logout = useCallback(async (redirectPath = "/admin/login") => {
    if (!isFirebaseConfigured()) {
      clearSession();
      return;
    }

    try {
      await logoutFromFirebase();
    } finally {
      clearSession();
      setError("");
      if (redirectPath) {
        window.location.assign(new URL(redirectPath, window.location.origin).toString());
      }
    }
  }, [clearSession]);

  const getAccessToken = useCallback(async () => {
    if (!isFirebaseConfigured()) {
      throw getFirebaseConfigError();
    }

    const auth = getFirebaseAuth();
    if (!auth.currentUser) {
      clearSession();
      throw new Error("Your admin session is no longer valid. Please sign in again.");
    }

    await getFreshIdToken(true);
    const session = await getCurrentSession(true);
    applySession(session);
    return session.token;
  }, [applySession, clearSession]);

  useEffect(() => {
    configureApiClient({
      getAccessToken,
      onUnauthorized: async () => {
        await logout("/admin/login");
      },
    });

    return () => {
      configureApiClient();
    };
  }, [getAccessToken, logout]);

  const clearError = useCallback(() => {
    setError("");
  }, []);

  const value = useMemo(
    () => ({
      isReady,
      isAuthenticated,
      isAdmin,
      user,
      token,
      error,
      adminClaimName,
      isConfigured: isFirebaseConfigured(),
      login,
      logout,
      getAccessToken,
      clearError,
    }),
    [adminClaimName, clearError, error, getAccessToken, isAdmin, isAuthenticated, isReady, login, logout, token, user]
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
