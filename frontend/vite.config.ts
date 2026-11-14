import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

/**
 * Predicción real por provincia: data/curated/predicciones_provincia.json (raíz del repositorio).
 * En desarrollo se sirve tal cual en /data/predicciones_provincia.json; al compilar se copia a dist/data/.
 * Si el fichero no existe, la petición da 404 y la app usa la demostración (con su sello).
 * PREDICCIONES_JSON permite apuntar a otro fichero.
 */
function prediccionesReales(): Plugin {
  const ruta = process.env.PREDICCIONES_JSON ?? fileURLToPath(new URL("../data/curated/predicciones_provincia.json", import.meta.url));
  return {
    name: "predicciones-reales",
    configureServer(server) {
      server.middlewares.use("/data/predicciones_provincia.json", (_req, res) => {
        res.setHeader("Cache-Control", "no-store");
        if (!existsSync(ruta)) {
          // 204 en vez de 404: la app usa la demostración sin ensuciar la consola.
          res.statusCode = 204;
          res.end();
          return;
        }
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(readFileSync(ruta));
      });
    },
    generateBundle() {
      if (existsSync(ruta)) {
        this.emitFile({ type: "asset", fileName: "data/predicciones_provincia.json", source: readFileSync(ruta) });
      }
    },
  };
}

// Las APIs en vivo (REData de Red Eléctrica y Open-Meteo) envían
// Access-Control-Allow-Origin: *, así que no hace falta proxy.
export default defineConfig({
  plugins: [react(), prediccionesReales()],
  base: "./",
  server: { port: 5173, strictPort: false },
  // MapLibre (~1,1 MB) y su web worker (~0,5 MB) son la mayor parte del paquete; es esperado.
  build: { chunkSizeWarningLimit: 2000 },
  test: { environment: "node" },
});
