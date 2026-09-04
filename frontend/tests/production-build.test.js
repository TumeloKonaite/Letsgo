import assert from "node:assert/strict";
import { mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const viteCli = path.join(frontendDirectory, "node_modules", "vite", "bin", "vite.js");
const clerkEnvironment = {
  VITE_CLERK_PUBLISHABLE_KEY: "pk_test_synthetic",
  VITE_CLERK_SIGN_IN_URL: "/admin/login",
  VITE_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL: "/admin/dashboard",
  VITE_CLERK_SIGN_OUT_FALLBACK_REDIRECT_URL: "/admin/login",
  VITE_CLERK_ADMIN_CLAIM: "admin",
};

function cleanProcessEnvironment() {
  return Object.fromEntries(
    Object.entries(process.env).filter(([name]) => !name.startsWith("VITE_"))
  );
}

function runProductionBuild(extraEnvironment = {}) {
  const outputDirectory = mkdtempSync(path.join(tmpdir(), "letsgosa-build-test-"));
  const result = spawnSync(
    process.execPath,
    [viteCli, "build", "--outDir", outputDirectory, "--emptyOutDir"],
    {
      cwd: frontendDirectory,
      encoding: "utf8",
      env: {
        ...cleanProcessEnvironment(),
        ...clerkEnvironment,
        ...extraEnvironment,
      },
    }
  );
  const assetsDirectory = path.join(outputDirectory, "assets");
  const bundleText =
    result.status === 0
      ? readdirSync(assetsDirectory)
          .filter((name) => name.endsWith(".js"))
          .map((name) => readFileSync(path.join(assetsDirectory, name), "utf8"))
          .join("\n")
      : "";
  rmSync(outputDirectory, { recursive: true, force: true });
  return { ...result, bundleText };
}

test("production Vite build fails clearly without VITE_API_BASE_URL", () => {
  const result = runProductionBuild();

  assert.notEqual(result.status, 0);
  assert.match(
    `${result.stdout}\n${result.stderr}`,
    /VITE_API_BASE_URL is required for non-development frontend builds/
  );
});

test("production Vite build succeeds with a valid API origin", () => {
  const result = runProductionBuild({
    VITE_API_BASE_URL: "https://api.example.invalid",
  });

  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.doesNotMatch(result.bundleText, /run\.app|VITE_LETSGO_API_BASE_URL/);
});
