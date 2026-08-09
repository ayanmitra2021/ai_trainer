import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // GitHub Pages serves the app at /ai_trainer/ (the repo name).
  // Setting base here makes Vite emit /ai_trainer/assets/... paths in the
  // built HTML so browsers can actually find the JS/CSS bundles.
  // In local dev (vite serve) this is overridden by the server config below,
  // which always serves from root, so the proxy still works.
  base: "/ai_trainer/",

  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the FastAPI backend during development
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
