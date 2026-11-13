import { useEffect, useState } from "react";
import type { GeoContexto, GeoProvincias, Viabilidad } from "./types";

const BASE = import.meta.env.BASE_URL;

export interface Datos {
  viabilidad: Viabilidad;
  geo: GeoProvincias;
  contexto: GeoContexto | null;
}

async function json<T>(ruta: string): Promise<T> {
  const r = await fetch(`${BASE}${ruta}`);
  if (!r.ok) throw new Error(`No se pudo cargar ${ruta} (${r.status})`);
  return (await r.json()) as T;
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
    ])
      .then(([viabilidad, geo, contexto]) => vivo && setDatos({ viabilidad, geo, contexto }))
      .catch((e: unknown) => vivo && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      vivo = false;
    };
  }, []);
  return { datos, error };
}
