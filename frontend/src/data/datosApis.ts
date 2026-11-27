import { useEffect, useState } from "react";
import { validarFicheroPublicado } from "./publicacion";
import type { EstadoPublicacion } from "./useDatos";

/** Panel «Datos»: lo genera Python (cpd.capas.exportar_web) desde la capa Gold del almacén DuckDB. */
export interface ApiFuente {
  fuente: string;
  descargas: number;
  ficheros: number;
  dominio: string | null;
  url_ejemplo: string | null;
  megabytes: number;
  primera_descarga: string | null;
  ultima_descarga: string | null;
  modulo: string;
  acceso: string;
  naturaleza: string;
  estrategia_cache: string;
}

export interface Capa {
  capa: string;
  rutas: string;
  que_es: string;
  formatos: string;
  ficheros: number;
  megabytes: number;
}

export interface TablaAlmacen {
  esquema: string;
  tabla: string;
  capa: string;
  filas: number;
  columnas: number;
  formato: string;
  columna: string | null;
  watermark: string | null;
  dias_desde: number | null;
}

export interface Watermark {
  esquema: string;
  tabla: string;
  columna: string;
  watermark: string;
  filas: number;
  avanza: boolean;
  dias_desde: number | null;
}

export interface ObjetoBbdd {
  esquema: string;
  tabla: string;
  tipo: "tabla" | "vista";
  filas: number;
  columnas: number;
}

export interface Formato {
  formato: string;
  motor: string;
  operacion: string;
  megabytes: number;
  segundos: number;
  tabla: string;
  columna: string;
}

export interface DatosApis {
  generado_en: string;
  kpis: {
    fuentes: number;
    descargas: number;
    ultima_descarga: string | null;
    tablas: number;
    filas: number;
    megabytes_bronze: number;
    construido_en: string | null;
  };
  capas: Capa[];
  apis: ApiFuente[];
  descargas_dia: { dia: string; fuente: string; descargas: number; megabytes: number }[];
  tablas: TablaAlmacen[];
  watermarks: Watermark[];
  bronze: { carpeta: string; ficheros: number; megabytes: number; formatos: string }[];
  formatos: Formato[];
  bbdd: { fichero: string; motor: string; megabytes: number; objetos: ObjetoBbdd[] };
}

const BASE = import.meta.env.BASE_URL;
const LISTAS = ["capas", "apis", "descargas_dia", "tablas", "watermarks", "bronze", "formatos"] as const;

/** Comprueba la forma mínima del JSON; devuelve null si no se puede pintar. */
export function normalizarDatosApis(json: unknown): DatosApis | null {
  if (!json || typeof json !== "object" || Array.isArray(json)) return null;
  const d = json as Record<string, unknown>;
  if (!d.kpis || typeof d.kpis !== "object" || Array.isArray(d.kpis)) return null;
  if (!LISTAS.every((clave) => Array.isArray(d[clave]))) return null;
  const bbdd = d.bbdd as Record<string, unknown> | undefined;
  if (!bbdd || typeof bbdd !== "object" || !Array.isArray(bbdd.objetos)) return null;
  return d as unknown as DatosApis;
}

async function leer(ruta: string): Promise<unknown> {
  const r = await fetch(BASE + ruta, { cache: "no-cache", signal: AbortSignal.timeout(10_000) });
  if (!r.ok) throw new Error(`No se pudo cargar ${ruta} (${r.status})`);
  return r.json();
}

/** Carga el panel de la versión publicada; si esa versión no lo trae, usa la copia de data/datos.json. */
export function useDatosApis(publicacion: EstadoPublicacion | undefined, solicitud: boolean): {
  datos: DatosApis | null;
  estado: "cargando" | "disponible" | "sin_datos";
} {
  const version = publicacion?.tipo === "versionada" ? publicacion.puntero.version : null;
  const clave = version ?? "respaldo";
  const [carga, setCarga] = useState<{ clave: string; datos: DatosApis | null } | null>(null);
  const vigente = carga?.clave === clave ? carga : null;

  useEffect(() => {
    if (!publicacion || !solicitud || vigente) return;
    let activo = true;
    const versionada = version
      ? leer("data/versiones/" + version + "/datos.json").then((json) => {
          if (!validarFicheroPublicado(json, version)) throw new Error("Versión del panel de datos incompatible");
          return json;
        })
      : Promise.reject(new Error("Sin versión publicada"));
    versionada
      .catch(() => leer("data/datos.json"))
      .then((json) => { if (activo) setCarga({ clave, datos: normalizarDatosApis(json) }); })
      .catch(() => { if (activo) setCarga({ clave, datos: null }); });
    return () => { activo = false; };
  }, [publicacion, solicitud, version, clave, vigente]);

  return { datos: vigente?.datos ?? null, estado: !vigente ? "cargando" : vigente.datos ? "disponible" : "sin_datos" };
}
