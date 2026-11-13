import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Las APIs en vivo (REData de Red Eléctrica y Open-Meteo) envían
// Access-Control-Allow-Origin: *, así que no hace falta proxy.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 5173, strictPort: false },
  // MapLibre (~1,1 MB) y su web worker (~0,5 MB) son la mayor parte del paquete; es esperado.
  build: { chunkSizeWarningLimit: 2000 },
  test: { environment: "node" },
});
