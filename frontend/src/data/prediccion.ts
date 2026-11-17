import type { Estado, Municipio, ProvinciaMeta, Viabilidad } from "./types";

export type ClaseRentabilidad = "alta" | "media" | "baja" | "no_rentable";

const CLASES: readonly ClaseRentabilidad[] = ["alta", "media", "baja", "no_rentable"];
const ESTADOS: readonly Estado[] = ["Viable", "Viable con condiciones", "No viable"];

/** Una provincia tal como la pinta el mapa (formato de data/curated/predicciones_provincia.json). */
export interface ProvinciaPrediccion {
  codigo: string;
  nombre: string;
  ccaa: string | null;
  /** Código INE de la comunidad (dos dígitos), para cruzar con la previsión de demanda. */
  codigo_ccaa?: string | null;
  /** Ámbito hidrográfico de la provincia (para cruzar con la previsión de reservas). */
  ambito_hidrografico?: string | null;
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
  /** Comunidad: generación renovable / demanda prevista para 12 meses (%) y capacidad de red de REE para demanda (MW):
   * otorgada a nuevos grandes consumos, pendiente de resolver y aún disponible. */
  cobertura_renovable_pct?: number | null;
  capacidad_demanda_otorgada_mw?: number | null;
  capacidad_demanda_pendiente_mw?: number | null;
  capacidad_acceso_disponible_mw?: number | null;
  /** Suelo urbano (€/m², mediana de 4 trimestres, Ministerio de Transportes) y latencia RTT al más lejano de los dos
   * grandes nodos de internet (ms). */
  precio_suelo_urbano_eur_m2?: number | null;
  latencia_hubs_rtt_ms?: number | null;
  /** Aceleración sísmica básica de la capital (g, norma NCSE-02; 0,04 = la norma da 0,04 o no la lista: ≤ 0,04). */
  aceleracion_sismica_g?: number | null;
  /** Demanda eléctrica de la comunidad (MWh): 12 últimos meses válidos y previsión de los 12 siguientes (cpd.modelos). */
  demanda_ccaa_ultimos_12m_mwh?: number | null;
  demanda_ccaa_prevision_12m_mwh?: number | null;
  demanda_ccaa_prevision_inferior_mwh?: number | null;
  demanda_ccaa_prevision_superior_mwh?: number | null;
  /** Último mes (AAAA-MM) de los 12 meses de demanda. */
  demanda_ccaa_hasta?: string | null;
  /** VAN (€) con el precio de la luz en el extremo bajo y alto de su rango probable y con el del último mes. */
  van_eur_precio_previsto?: number | null;
  van_eur_precio_inferior?: number | null;
  van_eur_precio_superior?: number | null;
  van_eur_precio_ultimo_mes?: number | null;
  /** Entradas que faltan para esta provincia (se dice en la ficha). */
  faltan?: string[];
  /** Solo en la demostración: municipios analizados de la provincia (el mejor primero). */
  municipios?: string[];
}

export interface ResumenModelos {
  prob_cpd?: { modelo: string; roc_auc: number | null; provincias_con_cpd: number | null };
  demanda?: { modelo: string; mape_test_pct: number | null };
  precio_luz?: {
    modelo: string;
    media_prevista_eur_mwh: number | null;
    inferior_eur_mwh: number | null;
    superior_eur_mwh: number | null;
    ultimo_mes: string | null;
    ultimo_mes_eur_mwh: number | null;
    mae_test_eur_mwh: number | null;
    futuro_gas_anio_eur_mwh?: number | null;
  };
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
  /** Resumen de los modelos de predicción (python -m cpd.modelos) usados en los datos. */
  modelos?: ResumenModelos;
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
      codigo_ccaa: texto(fila.codigo_ccaa),
      ambito_hidrografico: texto(fila.ambito_hidrografico),
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
      cobertura_renovable_pct: numero(fila.cobertura_renovable_pct),
      capacidad_demanda_otorgada_mw: numero(fila.capacidad_demanda_otorgada_mw),
      capacidad_demanda_pendiente_mw: numero(fila.capacidad_demanda_pendiente_mw),
      capacidad_acceso_disponible_mw: numero(fila.capacidad_acceso_disponible_mw),
      precio_suelo_urbano_eur_m2: numero(fila.precio_suelo_urbano_eur_m2),
      latencia_hubs_rtt_ms: numero(fila.latencia_hubs_rtt_ms),
      aceleracion_sismica_g: numero(fila.aceleracion_sismica_g),
      demanda_ccaa_ultimos_12m_mwh: numero(fila.demanda_ccaa_ultimos_12m_mwh),
      demanda_ccaa_prevision_12m_mwh: numero(fila.demanda_ccaa_prevision_12m_mwh),
      demanda_ccaa_prevision_inferior_mwh: numero(fila.demanda_ccaa_prevision_inferior_mwh),
      demanda_ccaa_prevision_superior_mwh: numero(fila.demanda_ccaa_prevision_superior_mwh),
      demanda_ccaa_hasta: texto(fila.demanda_ccaa_hasta),
      van_eur_precio_previsto: numero(fila.van_eur_precio_previsto),
      van_eur_precio_inferior: numero(fila.van_eur_precio_inferior),
      van_eur_precio_superior: numero(fila.van_eur_precio_superior),
      van_eur_precio_ultimo_mes: numero(fila.van_eur_precio_ultimo_mes),
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
    modelos: leerModelos(cabecera?.modelos),
    provincias,
    clasesMunicipio: new Map(),
  };
}

/** Valida el bloque `modelos` de la cabecera (lo que falte queda sin definir o en null). */
function leerModelos(v: unknown): ResumenModelos | undefined {
  if (!v || typeof v !== "object") return undefined;
  const m = v as Record<string, Record<string, unknown> | undefined>;
  const salida: ResumenModelos = {};
  const p = m.prob_cpd;
  if (p && texto(p.modelo)) salida.prob_cpd = { modelo: texto(p.modelo)!, roc_auc: numero(p.roc_auc), provincias_con_cpd: numero(p.provincias_con_cpd) };
  const d = m.demanda;
  if (d && texto(d.modelo)) salida.demanda = { modelo: texto(d.modelo)!, mape_test_pct: numero(d.mape_test_pct) };
  const l = m.precio_luz;
  if (l && texto(l.modelo))
    salida.precio_luz = {
      modelo: texto(l.modelo)!,
      media_prevista_eur_mwh: numero(l.media_prevista_eur_mwh),
      inferior_eur_mwh: numero(l.inferior_eur_mwh),
      superior_eur_mwh: numero(l.superior_eur_mwh),
      ultimo_mes: texto(l.ultimo_mes),
      ultimo_mes_eur_mwh: numero(l.ultimo_mes_eur_mwh),
      mae_test_eur_mwh: numero(l.mae_test_eur_mwh),
      futuro_gas_anio_eur_mwh: numero(l.futuro_gas_anio_eur_mwh),
    };
  return salida.prob_cpd || salida.demanda || salida.precio_luz ? salida : undefined;
}

/**
 * Rango del VAN (€) de las provincias con clase alta, media o baja. Sirve para avisar de que la clase es relativa:
 * si el rango es estrecho, una diferencia pequeña de VAN cambia el color. Devuelve null si no hay ninguna.
 */
export function rangoVanClasificadas(p: Prediccion): { min: number; max: number } | null {
  const van = [...p.provincias.values()]
    .filter((x) => x.clase && x.clase !== "no_rentable" && x.van_eur != null)
    .map((x) => x.van_eur!);
  return van.length ? { min: Math.min(...van), max: Math.max(...van) } : null;
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
