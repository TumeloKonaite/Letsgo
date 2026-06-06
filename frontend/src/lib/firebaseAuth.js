import {
  onIdTokenChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth";

import {
  getFirebaseAdminClaimName as getConfiguredFirebaseAdminClaimName,
  getFirebaseAuth as getConfiguredFirebaseAuth,
  getFirebaseConfigError as getConfiguredFirebaseConfigError,
  getGoogleProvider,
  isFirebaseConfigured as isConfiguredFirebase,
} from "./firebase";

function buildUserFromFirebase(firebaseUser, claims) {
  return {
    id: firebaseUser.uid,
    username: firebaseUser.displayName ?? firebaseUser.email ?? "Admin",
    email: firebaseUser.email ?? "",
    claims,
  };
}

export function getFirebaseAdminClaimName() {
  return getConfiguredFirebaseAdminClaimName();
}

export function getFirebaseAuth() {
  return getConfiguredFirebaseAuth();
}

export function getFirebaseConfigError() {
  return getConfiguredFirebaseConfigError();
}

export function isFirebaseConfigured() {
  return isConfiguredFirebase();
}

async function buildSession(firebaseUser, forceRefresh = false) {
  if (!firebaseUser) {
    return {
      token: null,
      user: null,
      isAuthenticated: false,
      isAdmin: false,
    };
  }

  const token = await firebaseUser.getIdToken(forceRefresh);
  const tokenResult = await firebaseUser.getIdTokenResult(forceRefresh);
  const claims = tokenResult.claims ?? {};
  const adminClaimName = getConfiguredFirebaseAdminClaimName();
  return {
    token,
    user: buildUserFromFirebase(firebaseUser, claims),
    isAuthenticated: true,
    isAdmin: claims[adminClaimName] === true,
  };
}

export function subscribeToAuthChanges(onSessionChange, onError) {
  return onIdTokenChanged(
    getConfiguredFirebaseAuth(),
    async (firebaseUser) => {
      try {
        onSessionChange(await buildSession(firebaseUser, true));
      } catch (error) {
        onError?.(error);
      }
    },
    onError
  );
}

export async function loginWithGoogle() {
  await signInWithPopup(getConfiguredFirebaseAuth(), getGoogleProvider());
}

export async function logoutFromFirebase() {
  await signOut(getConfiguredFirebaseAuth());
}

export async function getFreshIdToken(forceRefresh = false) {
  const auth = getConfiguredFirebaseAuth();
  if (!auth.currentUser) {
    return null;
  }

  return auth.currentUser.getIdToken(forceRefresh);
}

export async function getCurrentSession(forceRefresh = false) {
  return buildSession(getConfiguredFirebaseAuth().currentUser, forceRefresh);
}
