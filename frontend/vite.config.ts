import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "@tanstack/react-query", "zustand"],
          graph: ["reactflow", "elkjs"],
          icons: ["lucide-react"],
        },
      },
    },
  },
  server: {
    port: 5173,
    fs: {
      allow: [repoRoot],
    },
  },
});
