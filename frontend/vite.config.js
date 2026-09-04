import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

import { resolveFrontendEnvironment } from "./config/environment.js";

export default defineConfig(({ mode }) => {
  // Fail the build before bundling when public runtime settings are invalid.
  const fileEnvironment = loadEnv(mode, process.cwd(), "VITE_");
  resolveFrontendEnvironment(mode, { ...fileEnvironment, ...process.env });

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
    },
  };
});
