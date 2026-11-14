import type { Estado, Municipio, ProvinciaMeta, Viabilidad } from "./types";

export type ClaseRentabilidad = "alta" | "media" | "baja" | "no_rentable";

const CLASES: readonly ClaseRentabilidad[] = ["alta", "media", "baja", "no_rentable"];
const ESTADOS: readonly Estado[] = ["Viable", "Viable con condiciones", "No viable"];

/** Una provincia tal como la pinta el mapa (formato de data/curated/predicciones_provincia.json). */
export interface ProvinciaPrediccion {
  codigo: string;
  nombre: string;
  ccaa: string | null;
  clase: ClaseRentabilidad | null;
  score: number | null;
  estado: Estado | null;
  van_eur: number | null;
  roi: number | null;
  payback_anos: number | null;
  capex_eur: number | null;
  opex_eur_anual: number | null;
  precio_luz_actual_eur_mwh: number | null;
  precio_luz_previsto_eur_mwh: number | null;
  temp_media_anual_c: number | null;
  horas_free_cooling_anual: number | null;
  reserva_hidrica_pct: number | null;
  estres_hidrico: number | null;
  prob_cpd: number | null;
  cpd_existentes: number | null;
  motivos: string[];
  generado_en: string | null;
  /** Simulación: precio de la luz con el que se ha calculado (media spot de 12 meses). */
  precio_luz_usado_eur_mwh?: number | null;
  pue?: number | null;
  latencia_rtt_ms?: number | null;
  /** Entradas que faltan para esta provincia (se dice en la ficha). */
  faltan?: string[];
  /** Solo en la demostración: municipios analizados de la provincia (el mejor primero). */
  municipios?: string[];
}

export interface Prediccion {
  /**
   * "real" = predicción del modelo (data/curated/predicciones_provincia.json);
   * "simulacion" = modelo determinista del proyecto con datos reales por provincia (provincias_simuladas.json);
   * "demo" = modelo sobre municipios sintéticos.
   */
  tipo: "real" | "simulacion" | "demo";
  generado: string | null;
  /** Momento de la última actualización de los datos de entrada. */
  actualizado?: string | null;
  /** Último mes completo de clima, agua y precios (AAAA-MM). */
  mesReferencia?: string | null;
  /** Lo que el modelo no puede evaluar a escala provincial. */
  noEvaluado?: string[];
  provincias: Map<string, ProvinciaPrediccion>;
  /** Solo en la demostración: clase de cada municipio analizado. */
  clasesMunicipio: Map<string, ClaseRentabilidad>;
}

const numero = (v: unknown): number | null => {
  if (v == null || v === "") return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
};
const texto = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.trim() : null);

/**
 * Valida y normaliza el array de data/curated/predicciones_provincia.json. Descarta filas sin un código
 * de provincia válido; cualquier valor ausente o no numérico queda en null (nunca se rellena).
 * Devuelve null si no queda ninguna provincia utilizable.
 */
export function normalizarReal(json: unknown, meta: ProvinciaMeta[], tipo: "real" | "simulacion" = "real"): Prediccion | null {
  // Acepta la lista sola (contrato de predicciones) o un objeto { provincias: [...], ...metadatos } (simulación).
  const cabecera = json && typeof json === "object" && !Array.isArray(json) ? (json as Record<string, unknown>) : null;
  if (cabecera) json = cabecera.provincias;
  if (!Array.isArray(json)) return null;
  const nombres = new Map(meta.map((m) => [m.codigo, m.nombre]));
  const provincias = new Map<string, ProvinciaPrediccion>();
  let generado: string | null = null;
  for (const fila of json as Record<string, unknown>[]) {
    if (!fila || typeof fila !== "object") continue;
    const crudo = texto(fila.codigo_provincia) ?? (typeof fila.codigo_provincia === "number" ? String(fila.codigo_provincia) : null);
    const codigo = crudo?.padStart(2, "0");
    if (!codigo || !nombres.has(codigo)) continue;
    const clase = CLASES.includes(fila.rentabilidad_clase as ClaseRentabilidad) ? (fila.rentabilidad_clase as ClaseRentabilidad) : null;
    const estado = ESTADOS.includes(fila.estado as Estado) ? (fila.estado as Estado) : null;
    const gen = texto(fila.generado_en);
    if (gen && (!generado || gen > generado)) generado = gen;
    provincias.set(codigo, {
      codigo,
      nombre: texto(fila.provincia) ?? nombres.get(codigo)!,
      ccaa: texto(fila.ccaa),
      clase,
      score: numero(fila.score_viabilidad),
      estado,
      van_eur: numero(fila.van_eur),
      roi: numero(fila.roi),
      payback_anos: numero(fila.payback_anos),
      capex_eur: numero(fila.capex_eur),
      opex_eur_anual: numero(fila.opex_eur_anual),
      precio_luz_actual_eur_mwh: numero(fila.precio_luz_actual_eur_mwh),
      precio_luz_previsto_eur_mwh: numero(fila.precio_luz_previsto_eur_mwh),
      temp_media_anual_c: numero(fila.temp_media_anual_c),
      horas_free_cooling_anual: numero(fila.horas_free_cooling_anual),
      reserva_hidrica_pct: numero(fila.reserva_hidrica_pct),
      estres_hidrico: numero(fila.estres_hidrico),
      prob_cpd: numero(fila.prob_cpd),
      cpd_existentes: numero(fila.cpd_existentes),
      motivos: Array.isArray(fila.motivos) ? fila.motivos.filter((m): m is string => typeof m === "string") : [],
      generado_en: gen,
      precio_luz_usado_eur_mwh: numero(fila.precio_luz_usado_eur_mwh),
      pue: numero(fila.pue),
      latencia_rtt_ms: numero(fila.latencia_rtt_ms),
      faltan: Array.isArray(fila.faltan) ? fila.faltan.filter((m): m is string => typeof m === "string") : [],
    });
  }
  if (!provincias.size) return null;
  return {
    tipo,
    generado: texto(cabecera?.generado) ?? generado,
    actualizado: texto(cabecera?.actualizado) ?? generado,
    mesReferencia: texto(cabecera?.mes_referencia),
    noEvaluado: Array.isArray(cabecera?.no_evaluado_a_escala_provincial)
      ? (cabecera!.no_evaluado_a_escala_provincial as unknown[]).filter((m): m is string => typeof m === "string")
      : [],
    provincias,
    clasesMunicipio: new Map(),
  };
}

/**
 * Regla de la DEMOSTRACIÓN para dar una clase de rentabilidad a datos sintéticos:
 * "No viable" → no rentable; el resto se reparte en tercios según su VAN
 * (tercio superior = alta, medio = media, inferior = baja). Es relativa a la tabla de demostración,
 * no un umbral económico; la predicción real trae su propia clase.
 */
export function clasesDemo<T>(items: T[], estado: (x: T) => Estado, van: (x: T) => number | null): Map<T, ClaseRentabilidad> {
  const salida = new Map<T, ClaseRentabilidad>();
  const viables = items.filter((x) => estado(x) !== "No viable" && van(x) != null).sort((a, b) => van(b)! - van(a)!);
  const n = viables.length;
  viables.forEach((x, i) => salida.set(x, i < n / 3 ? "alta" : i < (2 * n) / 3 ? "media" : "baja"));
  for (const x of items) if (estado(x) === "No viable") salida.set(x, "no_rentable");
  return salida;
}

/** Construye la vista por provincia a partir del modelo de demostración (viabilidad.json). */
export function desdeDemo(v: Viabilidad, meta: ProvinciaMeta[]): Prediccion {
  const porIne = new Map(v.municipios.map((m) => [m.codigo_ine, m]));
  const nombres = new Map(meta.map((m) => [m.codigo, m]));
  const mejores = Object.values(v.provincias)
    .map((r) => ({ r, m: porIne.get(r.mejor) }))
    .filter((x): x is { r: (typeof x)["r"]; m: Municipio } => Boolean(x.m));
  const claseProv = clasesDemo(mejores, (x) => x.m.estado, (x) => x.m.salidas.van_eur);
  const claseMun = clasesDemo(v.municipios, (m) => m.estado, (m) => m.salidas.van_eur);

  const provincias = new Map<string, ProvinciaPrediccion>();
  for (const x of mejores) {
    const { r, m } = x;
    provincias.set(r.codigo, {
      codigo: r.codigo,
      nombre: nombres.get(r.codigo)?.nombre ?? m.provincia ?? r.codigo,
      ccaa: m.ccaa,
      clase: claseProv.get(x) ?? null,
      score: m.score_global,
      estado: m.estado,
      van_eur: m.salidas.van_eur,
      roi: m.salidas.roi,
      payback_anos: m.salidas.payback_anos,
      capex_eur: m.salidas.capex_total_eur,
      opex_eur_anual: m.salidas.opex_eur,
      precio_luz_actual_eur_mwh: v.precios.precio_electricidad_eur_mwh,
      precio_luz_previsto_eur_mwh: null,
      temp_media_anual_c: m.entradas.temp_media_c ?? null,
      horas_free_cooling_anual: null,
      reserva_hidrica_pct: null,
      estres_hidrico: m.entradas.estres_hidrico_idx ?? null,
      prob_cpd: null,
      cpd_existentes: null,
      motivos: m.motivos,
      generado_en: v.generado,
      municipios: r.municipios,
    });
  }
  return {
    tipo: "demo",
    generado: v.generado,
    provincias,
    clasesMunicipio: new Map(v.municipios.map((m) => [m.codigo_ine, claseMun.get(m)!])),
  };
}
