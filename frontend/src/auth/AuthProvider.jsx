import { useAuth as useClerkAuth, useClerk, useUser } from "@clerk/clerk-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { resolveFrontendEnvironment } from "../../config/environment";
import { configureApiClient } from "../api/client";

const AuthContext = createContext(null);
const frontendConfig = resolveFrontendEnvironment(import.meta.env.MODE, import.meta.env);

function publicUser(user) {
  // Expose only the Clerk user fields consumed by the application UI.
  if (!user) {
    return null;
  }
  return {
    id: user.id,
    username: user.fullName || user.username || user.primaryEmailAddress?.emailAddress || "Admin",
    email: user.primaryEmailAddress?.emailAddress || "",
  };
}

export function AuthProvider({ children }) {
  // Adapt Clerk hooks to the stable authentication interface used by the app.
  const { isLoaded: isAuthLoaded, isSignedIn, getToken, sessionClaims } = useClerkAuth();
  const { isLoaded: isUserLoaded, user } = useUser();
  const { openSignIn, signOut } = useClerk();
  const [error, setError] = useState("");
  const isReady = isAuthLoaded && isUserLoaded;
  const isAuthenticated = isReady && Boolean(isSignedIn);
  const isAdmin = sessionClaims?.[frontendConfig.clerkAdminClaim] === true;

  const login = useCallback(
    async (redirectPath = frontendConfig.clerkSignInFallbackRedirectUrl) => {
      // Open Clerk's sign-in flow and surface a readable failure to the UI.
      try {
        setError("");
        await openSignIn({ fallbackRedirectUrl: redirectPath });
      } catch (loginError) {
        setError(
          loginError instanceof Error && loginError.message
            ? loginError.message
            : "Unable to start the Clerk sign-in flow."
        );
      }
    },
    [openSignIn]
  );

  const logout = useCallback(
    async (redirectPath = frontendConfig.clerkSignOutFallbackRedirectUrl) => {
      // End the Clerk session and return the user to a safe local route.
      setError("");
      await signOut({ redirectUrl: redirectPath });
    },
    [signOut]
  );

  const getAccessToken = useCallback(async () => {
    // Fetch a fresh session token for each protected API request.
    const token = await getToken();
    if (!token) {
      throw new Error("Your admin session is no longer valid. Please sign in again.");
    }
    return token;
  }, [getToken]);

  useEffect(() => {
    // Keep the shared API client synchronized with the active Clerk session.
    configureApiClient({
      getAccessToken,
      onUnauthorized: async () => logout(),
    });
    return () => configureApiClient();
  }, [getAccessToken, logout]);

  const clearError = useCallback(() => setError(""), []);
  const value = useMemo(
    () => ({
      isReady,
      isAuthenticated,
      isAdmin,
      user: publicUser(user),
      token: null,
      error,
      adminClaimName: frontendConfig.clerkAdminClaim,
      isConfigured: true,
      login,
      logout,
      getAccessToken,
      clearError,
    }),
    [clearError, error, getAccessToken, isAdmin, isAuthenticated, isReady, login, logout, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  // Require consumers to read authentication state inside AuthProvider.
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
