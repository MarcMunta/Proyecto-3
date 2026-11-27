/** Contrato de la publicación atómica generada por el exportador de Python. */
export interface PunteroPublicacion {
  schema_version: 1;
  version: string;
  generado_en: string;
  origen_modelos?: "regenerados" | "importados";
  fecha_panel?: string;
  avisos?: string[];
}

/** La edad de la publicación se muestra sin cambiar el lote activo. */
export const EDAD_MAXIMA_PUBLICACION_MS = 7 * 24 * 60 * 60 * 1_000;

/** Solo se aceptan nombres de versión que no pueden salir de `data/versiones/`. */
export function esVersionSegura(version: unknown): version is string {
  return typeof version === "string" && /^(?!\.{1,2}$)[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(version);
}

/** Valida el puntero antes de interpolar la versión en una ruta de carga. */
export function validarPunteroPublicacion(json: unknown): PunteroPublicacion | null {
  if (!json || typeof json !== "object" || Array.isArray(json)) return null;
  const p = json as Record<string, unknown>;
  if (p.schema_version !== 1 || !esVersionSegura(p.version) || typeof p.generado_en !== "string" || !Number.isFinite(Date.parse(p.generado_en))) return null;
  const origen = p.origen_modelos;
  const fecha = p.fecha_panel;
  const avisos = Array.isArray(p.avisos) ? p.avisos.filter((v): v is string => typeof v === "string" && v.trim() !== "") : [];
  return {
    schema_version: 1,
    version: p.version,
    generado_en: p.generado_en.trim(),
    ...(avisos.length ? { avisos } : {}),
    ...(origen === "regenerados" || origen === "importados" ? { origen_modelos: origen } : {}),
    ...(typeof fecha === "string" && /^\d{4}-\d{2}$/.test(fecha) ? { fecha_panel: fecha } : {}),
  };
}

/** Los dos ficheros publicados deben pertenecer exactamente a la versión anunciada. */
export function validarFicheroPublicado(json: unknown, version: string): boolean {
  if (!json || typeof json !== "object" || Array.isArray(json)) return false;
  const cabecera = json as Record<string, unknown>;
  return cabecera.schema_version === 1 && cabecera.version === version;
}

/** Determina si el puntero no puede considerarse actual según su marca de generación UTC. */
export function punteroObsoleto(puntero: PunteroPublicacion, ahora = Date.now()): boolean {
  const generado = Date.parse(puntero.generado_en);
  return !Number.isFinite(generado) || generado > ahora + 5 * 60_000 || ahora - generado > EDAD_MAXIMA_PUBLICACION_MS;
}
