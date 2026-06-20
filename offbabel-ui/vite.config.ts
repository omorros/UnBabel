import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// base: "./" -> relative asset URLs so FastAPI can serve the built bundle from any path.
// The app talks to the Python backend over ws://<host>/ws (contract unchanged).
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  build: { outDir: "dist" },
  // Dev only: proxy the WebSocket + Reachy camera stream to the Python backend on :8500.
  // The UI works standalone without it (screens are navigable; interactions simulate locally).
  server: {
    proxy: {
      "/ws": { target: "ws://127.0.0.1:8500", ws: true },
      "/reachy-media": { target: "http://127.0.0.1:8500", changeOrigin: true },
    },
  },
})
