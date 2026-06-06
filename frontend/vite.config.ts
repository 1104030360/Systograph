import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

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
  },
});
