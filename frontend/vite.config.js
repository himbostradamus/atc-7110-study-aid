import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

function pruneStaticDeployAssets() {
  return {
    name: "prune-static-deploy-assets",
    closeBundle() {
      if (!["1", "true"].includes(String(process.env.VITE_ATC_STATIC_DEPLOY || "").toLowerCase())) return;
      rmSync(resolve(process.cwd(), "dist", "aircraft-images"), { recursive: true, force: true });
    },
  };
}

function stampServiceWorker() {
  return {
    name: "stamp-service-worker",
    closeBundle() {
      const path = resolve(process.cwd(), "dist", "sw.js");
      const buildId = process.env.GITHUB_SHA || Date.now().toString(36);
      const content = readFileSync(path, "utf8").replaceAll("__BUILD_ID__", buildId);
      writeFileSync(path, content);
    },
  };
}

export default defineConfig({
  base: process.env.VITE_BASE || "./",
  plugins: [react(), stampServiceWorker(), pruneStaticDeployAssets()],
});
