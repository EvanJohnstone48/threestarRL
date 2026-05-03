import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    fs: {
      // Allow vite dev server to serve replays from app/experiments/runs/
      allow: [path.resolve(__dirname, ".."), path.resolve(__dirname, "../..")],
    },
  },
});
