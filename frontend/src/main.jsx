import React from "react";
import ReactDOM from "react-dom/client";
import { ClerkProvider } from "@clerk/clerk-react";
import { BrowserRouter } from "react-router-dom";

import { resolveFrontendEnvironment } from "../config/environment.js";
import App from "./App.jsx";
import { AuthProvider } from "./auth/AuthProvider.jsx";
import "./index.css";

const frontendConfig = resolveFrontendEnvironment(import.meta.env.MODE, import.meta.env);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ClerkProvider
      publishableKey={frontendConfig.clerkPublishableKey}
      signInUrl={frontendConfig.clerkSignInUrl}
      signInFallbackRedirectUrl={frontendConfig.clerkSignInFallbackRedirectUrl}
      signOutFallbackRedirectUrl={frontendConfig.clerkSignOutFallbackRedirectUrl}
    >
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </ClerkProvider>
  </React.StrictMode>
);
