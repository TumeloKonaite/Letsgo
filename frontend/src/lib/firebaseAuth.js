import { initializeApp } from "firebase/app";
import {
  GoogleAuthProvider,
  getAuth,
  onIdTokenChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth";

const FIREBASE_ADMIN_CLAIM = import.meta.env.VITE_FIREBASE_ADMIN_CLAIM?.trim() || "admin";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY?.trim() || "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.trim() || "",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim() || "",
  appId: import.meta.env.VITE_FIREBASE_APP_ID?.trim() || "",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET?.trim() || undefined,
  messagingSenderId:
    import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID?.trim() || undefined,
};

const hasCompleteConfig = [
  firebaseConfig.apiKey,
  firebaseConfig.authDomain,
  firebaseConfig.projectId,
  firebaseConfig.appId,
].every(Boolean);

let firebaseApp = null;
let firebaseAuth = null;
let googleProvider = null;

function getMissingConfigError() {
  return new Error(
    "Firebase Auth is not configured. Set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID, and VITE_FIREBASE_APP_ID."
  );
}

function buildUserFromFirebase(firebaseUser, claims) {
  return {
    id: firebaseUser.uid,
    username: firebaseUser.displayName ?? firebaseUser.email ?? "Admin",
    email: firebaseUser.email ?? "",
    claims,
  };
}

export function getFirebaseAdminClaimName() {
  return FIREBASE_ADMIN_CLAIM;
}

export function isFirebaseConfigured() {
  return hasCompleteConfig;
}

export function getFirebaseConfigError() {
  return getMissingConfigError();
}

export function getFirebaseApp() {
  if (!hasCompleteConfig) {
    throw getMissingConfigError();
  }

  if (!firebaseApp) {
    firebaseApp = initializeApp(firebaseConfig);
  }

  return firebaseApp;
}

export function getFirebaseAuth() {
  if (!firebaseAuth) {
    firebaseAuth = getAuth(getFirebaseApp());
  }

  return firebaseAuth;
}

function getGoogleProvider() {
  if (!googleProvider) {
    googleProvider = new GoogleAuthProvider();
    googleProvider.setCustomParameters({ prompt: "select_account" });
  }

  return googleProvider;
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
  return {
    token,
    user: buildUserFromFirebase(firebaseUser, claims),
    isAuthenticated: true,
    isAdmin: claims[FIREBASE_ADMIN_CLAIM] === true,
  };
}

export function subscribeToAuthChanges(onSessionChange, onError) {
  return onIdTokenChanged(
    getFirebaseAuth(),
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
  await signInWithPopup(getFirebaseAuth(), getGoogleProvider());
}

export async function logoutFromFirebase() {
  await signOut(getFirebaseAuth());
}

export async function getFreshIdToken(forceRefresh = false) {
  const auth = getFirebaseAuth();
  if (!auth.currentUser) {
    return null;
  }

  return auth.currentUser.getIdToken(forceRefresh);
}

export async function getCurrentSession(forceRefresh = false) {
  return buildSession(getFirebaseAuth().currentUser, forceRefresh);
}
