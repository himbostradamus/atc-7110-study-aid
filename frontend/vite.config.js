import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { rmSync } from "node:fs";
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

export default defineConfig({
  base: process.env.VITE_BASE || "./",
  plugins: [react(), pruneStaticDeployAssets()],
});
