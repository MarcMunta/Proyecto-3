import { useEffect, useState } from "react";
import metaJson from "./provincias.json";
import type { GeoContexto, GeoProvincias, ProvinciaMeta, Viabilidad } from "./types";
import { desdeDemo, normalizarReal, type Prediccion } from "./prediccion";

const BASE = import.meta.env.BASE_URL;
const META = metaJson as ProvinciaMeta[];

export interface Datos {
  /** Modelo de demostración por municipio (siempre disponible; se usa como respaldo). */
  viabilidad: Viabilidad;
  /** Lo que pinta el mapa: la predicción real si existe, si no la demostración. */
  prediccion: Prediccion;
  geo: GeoProvincias;
  contexto: GeoContexto | null;
}

async function json<T>(ruta: string): Promise<T> {
  const r = await fetch(`${BASE}${ruta}`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`No se pudo cargar ${ruta} (${r.status})`);
  return (await r.json()) as T;
}

/**
 * Orden de preferencia para la capa provincial:
 *  1. data/curated/predicciones_provincia.json (predicción del modelo; lo sirve el plugin de vite.config.ts),
 *  2. public/data/provincias_simuladas.json (simulación con datos reales de las 52 provincias, npm run data),
 *  3. la demostración sintética (desdeDemo).
 */
async function prediccionReal(): Promise<Prediccion | null> {
  for (const [ruta, tipo] of [
    ["data/predicciones_provincia.json", "real"],
    ["data/provincias_simuladas.json", "simulacion"],
  ] as const) {
    try {
      const p = normalizarReal(await json<unknown>(ruta), META, tipo);
      if (p) return p;
    } catch {
      /* no existe o no es válido: probar la siguiente fuente */
    }
  }
  return null;
}

/** Carga los ficheros estáticos generados por scripts/export_data.py y scripts/build_geo.mjs. */
export function useDatos(): { datos: Datos | null; error: string | null } {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let vivo = true;
    Promise.all([
      json<Viabilidad>("data/viabilidad.json"),
      json<GeoProvincias>("data/provincias.geojson"),
      json<GeoContexto>("data/contexto.geojson").catch(() => null),
      prediccionReal(),
    ])
      .then(([viabilidad, geo, contexto, real]) => {
        if (vivo) setDatos({ viabilidad, geo, contexto, prediccion: real ?? desdeDemo(viabilidad, META) });
      })
      .catch((e: unknown) => vivo && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      vivo = false;
    };
  }, []);
  return { datos, error };
}
