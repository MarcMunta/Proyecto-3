import { useEffect, useState } from "react";
import metaJson from "./provincias.json";
import type { GeoContexto, GeoProvincias, ProvinciaMeta, Viabilidad } from "./types";
import { desdeDemo, normalizarReal, type Prediccion } from "./prediccion";
import { normalizarPrevisiones, type Previsiones } from "./previsiones";
import { validarFicheroPublicado, validarPunteroPublicacion, type PunteroPublicacion } from "./publicacion";

const BASE = import.meta.env.BASE_URL;
const META = metaJson as ProvinciaMeta[];

export interface Datos {
  /** Modelo de demostración por municipio (siempre disponible; se usa como respaldo). */
  viabilidad: Viabilidad;
  /** Lo que pinta el mapa: la predicción real si existe, si no la demostración. */
  prediccion: Prediccion;
  geo: GeoProvincias;
  contexto: GeoContexto | null;
  /** Origen de la pareja provincias/previsiones, visible para no ocultar una degradación. */
  publicacion: EstadoPublicacion;
}

export type EstadoPublicacion =
  | { tipo: "versionada"; puntero: PunteroPublicacion }
  | { tipo: "respaldo"; motivo: string };

async function json<T>(ruta: string): Promise<T> {
  const r = await fetch(BASE + ruta, {
    cache: ruta.startsWith("data/versiones/") ? "default" : "no-cache",
    signal: AbortSignal.timeout(10_000),
  });
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

/** Comprueba la cabecera de los datos necesarios para pintar el ranking. */
async function capaConRespaldo(): Promise<{ prediccion: Prediccion | null; publicacion: EstadoPublicacion }> {
  try {
    const puntero = validarPunteroPublicacion(await json<unknown>("data/publicacion.json"));
    if (!puntero) throw new Error("El puntero de publicación no cumple el contrato esperado.");
    const provincias = await json<unknown>("data/versiones/" + puntero.version + "/provincias_simuladas.json");
    if (!validarFicheroPublicado(provincias, puntero.version)) {
      throw new Error("Las provincias no pertenecen a la versión anunciada.");
    }
    const prediccion = normalizarReal(provincias, META, "simulacion", "publicacion_versionada");
    if (!prediccion) throw new Error("La publicación versionada no contiene provincias utilizables.");
    return { prediccion, publicacion: { tipo: "versionada", puntero } };
  } catch (causa) {
    const motivo = causa instanceof Error ? causa.message : "No se pudo leer la publicación versionada.";
    return {
      prediccion: await prediccionReal(),
      publicacion: { tipo: "respaldo", motivo: motivo + " Se usa la fuente de respaldo." },
    };
  }
}

/** Descarga las series al abrir una ficha y conserva la misma versión que el ranking. */
export function usePrevisiones(publicacion: EstadoPublicacion | undefined, solicitud: boolean): {
  datos: Previsiones | null;
  estado: "cargando" | "disponible" | "sin_datos";
} {
  const version = publicacion?.tipo === "versionada" ? publicacion.puntero.version : null;
  const ruta = version ? "data/versiones/" + version + "/previsiones.json" : "data/previsiones.json";
  const [carga, setCarga] = useState<{ ruta: string; datos: Previsiones | null } | null>(null);
  const vigente = carga?.ruta === ruta ? carga : null;

  useEffect(() => {
    if (!publicacion || !solicitud || vigente) return;
    let activo = true;
    json<unknown>(ruta)
      .then((contenido) => {
        if (version && !validarFicheroPublicado(contenido, version)) throw new Error("Versión de previsiones incompatible");
        if (activo) setCarga({ ruta, datos: normalizarPrevisiones(contenido) });
      })
      .catch(() => {
        if (activo) setCarga({ ruta, datos: null });
      });
    return () => { activo = false; };
  }, [publicacion, ruta, solicitud, version, vigente]);

  return { datos: vigente?.datos ?? null, estado: !vigente ? "cargando" : vigente.datos ? "disponible" : "sin_datos" };
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
      capaConRespaldo(),
    ])
      .then(([viabilidad, geo, contexto, capa]) => {
        if (!vivo) return;
        const prediccion = capa.prediccion ?? desdeDemo(viabilidad, META);
        setDatos({ viabilidad, geo, contexto, prediccion, publicacion: capa.publicacion });
      })
      .catch((e: unknown) => vivo && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      vivo = false;
    };
  }, []);
  return { datos, error };
}
