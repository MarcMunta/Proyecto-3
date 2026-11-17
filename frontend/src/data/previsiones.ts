/**
 * Previsión a 1 año (python -m cpd.modelos → data/curated/modelos/previsiones_1_anio.json, que npm run data copia
 * a public/data/previsiones.json): precio de la luz nacional, demanda eléctrica de cada comunidad, reservas de agua de
 * cada ámbito y temperatura media de cada provincia, mes a mes.
 */

export interface PuntoMes {
  /** AAAA-MM */
  mes: string;
  valor: number;
}

export interface PuntoPrevision extends PuntoMes {
  inferior: number | null;
  superior: number | null;
}

export interface SeriePrevista {
  modelo: string;
  miembros: string[];
  /** Error medio a 1 año del modelo en validación y test (MAPE en %, o MAE en la unidad de la serie). */
  errorValidacion: number | null;
  errorTest: number | null;
  /** Acierto (100 − WAPE, %) en validación y test, y si cumple el requisito (85 % ≤ acierto < 99,9 %). */
  aciertoValidacion: number | null;
  aciertoTest: number | null;
  historia: PuntoMes[];
  prevision: PuntoPrevision[];
}

export interface TemperaturaPrevista extends SeriePrevista {
  nombre: string;
  /** Media (°C) de los últimos 12 meses reales y de los 12 meses previstos, con su intervalo 10-90 %. */
  media12m: number | null;
  mediaPrevista: number | null;
  mediaInferior: number | null;
  mediaSuperior: number | null;
}

export interface RenovablePrevista extends TemperaturaPrevista {
  /** Acierto (100 − WAPE, %) de la media de los 12 meses previstos, en validación y test. */
  aciertoAnualValidacion: number | null;
  aciertoAnualTest: number | null;
}

export interface Previsiones {
  generado: string | null;
  precio: (SeriePrevista & { mediaPrevista: number | null; futuroGasAnio: number | null }) | null;
  /** Por código INE de comunidad (dos dígitos). */
  demanda: Map<string, SeriePrevista & { nombre: string }>;
  demandaModelo: { modelo: string; miembros: string[]; errorValidacion: number | null; errorTest: number | null } | null;
  /** Reserva de los embalses por ámbito hidrográfico (%). */
  reservas: Map<string, SeriePrevista>;
  /** Temperatura media mensual (°C) por código INE de provincia, y la media del último año y de los 12 meses previstos. */
  temperatura: Map<string, TemperaturaPrevista>;
  /** % de generación renovable mensual por código INE de comunidad, con el acierto de la media de 12 meses. */
  renovables: Map<string, RenovablePrevista>;
  /** Demanda nacional anual (TWh): historia y previsión a 10 años (`mes` = «AAAA-01»). */
  demanda10: (SeriePrevista & { acierto: number | null }) | null;
  /** Requisito de acierto por modelo. */
  control: { modelo: string; estado: string }[];
}

/** Mínimo de acierto exigido a los modelos (cpd.modelos.metricas.ACIERTO_MINIMO). */
export const ACIERTO_MINIMO = 85;

const numero = (v: unknown): number | null => {
  const n = typeof v === "number" ? v : typeof v === "string" && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
};
const texto = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.trim() : null);
const esMes = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}$/.test(v);

function puntos(v: unknown): PuntoMes[] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((p) => {
    const valor = numero((p as Record<string, unknown>)?.valor);
    const mes = (p as Record<string, unknown>)?.mes;
    return esMes(mes) && valor != null ? [{ mes, valor }] : [];
  });
}

function puntosPrevision(v: unknown): PuntoPrevision[] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((p) => {
    const fila = p as Record<string, unknown>;
    const valor = numero(fila?.valor);
    return esMes(fila?.mes) && valor != null ? [{ mes: fila.mes, valor, inferior: numero(fila.inferior), superior: numero(fila.superior) }] : [];
  });
}

const miembros = (v: unknown): string[] => (Array.isArray(v) ? v.filter((m): m is string => typeof m === "string") : []);

/** Valida el JSON de previsiones; lo que no tenga forma válida se descarta (nunca se rellena). */
export function normalizarPrevisiones(json: unknown): Previsiones | null {
  if (!json || typeof json !== "object") return null;
  const raiz = json as Record<string, Record<string, unknown> | undefined>;
  const p = raiz.precio;
  const precio =
    p && texto(p.modelo)
      ? {
          modelo: texto(p.modelo)!,
          miembros: miembros(p.miembros),
          errorValidacion: numero(p.error_validacion),
          errorTest: numero(p.error_test),
          aciertoValidacion: numero(p.acierto_validacion),
          aciertoTest: numero(p.acierto_test),
          historia: puntos(p.historia),
          prevision: puntosPrevision(p.prevision),
          mediaPrevista: numero(p.media_prevista),
          futuroGasAnio: numero(p.futuro_gas_anio),
        }
      : null;
  const d = raiz.demanda;
  const demanda = new Map<string, SeriePrevista & { nombre: string }>();
  let demandaModelo: Previsiones["demandaModelo"] = null;
  if (d && texto(d.modelo)) {
    demandaModelo = { modelo: texto(d.modelo)!, miembros: miembros(d.miembros), errorValidacion: numero(d.error_validacion), errorTest: numero(d.error_test) };
    const porCcaa = d.ccaa && typeof d.ccaa === "object" ? (d.ccaa as Record<string, Record<string, unknown>>) : {};
    for (const [codigo, c] of Object.entries(porCcaa)) {
      if (!/^\d{2}$/.test(codigo) || !c) continue;
      const prevision = puntosPrevision(c.prevision);
      if (!prevision.length) continue;
      demanda.set(codigo, { ...demandaModelo, aciertoValidacion: numero(d.acierto_validacion), aciertoTest: numero(d.acierto_test), nombre: texto(c.nombre) ?? codigo, historia: puntos(c.historia), prevision });
    }
  }
  const reservas = new Map<string, SeriePrevista>();
  const r = raiz.reservas;
  if (r && texto(r.modelo)) {
    const porAmbito = r.ambitos && typeof r.ambitos === "object" ? (r.ambitos as Record<string, Record<string, unknown>>) : {};
    for (const [ambito, a] of Object.entries(porAmbito)) {
      const prevision = puntosPrevision(a?.prevision);
      if (!prevision.length) continue;
      reservas.set(ambito, {
        modelo: texto(r.modelo)!, miembros: miembros(r.miembros), errorValidacion: numero(r.error_validacion), errorTest: numero(r.error_test),
        aciertoValidacion: numero(r.acierto_validacion), aciertoTest: numero(r.acierto_test), historia: puntos(a.historia), prevision,
      });
    }
  }
  const temperatura = new Map<string, TemperaturaPrevista>();
  const t = raiz.temperatura;
  if (t && texto(t.modelo)) {
    const porProvincia = t.provincias && typeof t.provincias === "object" ? (t.provincias as Record<string, Record<string, unknown>>) : {};
    for (const [codigo, a] of Object.entries(porProvincia)) {
      const prevision = puntosPrevision(a?.prevision);
      if (!/^\d{2}$/.test(codigo) || !prevision.length) continue;
      temperatura.set(codigo, {
        modelo: texto(t.modelo)!, miembros: miembros(t.miembros), errorValidacion: numero(t.error_validacion), errorTest: numero(t.error_test),
        aciertoValidacion: numero(t.acierto_validacion), aciertoTest: numero(t.acierto_test), historia: puntos(a.historia), prevision,
        nombre: texto(a.nombre) ?? codigo, media12m: numero(a.media_12m_actual), mediaPrevista: numero(a.media_prevista),
        mediaInferior: numero(a.media_inferior), mediaSuperior: numero(a.media_superior),
      });
    }
  }
  const renovables = new Map<string, RenovablePrevista>();
  const v = raiz.renovables;
  if (v && texto(v.modelo)) {
    const porCcaa = v.ccaa && typeof v.ccaa === "object" ? (v.ccaa as Record<string, Record<string, unknown>>) : {};
    for (const [codigo, a] of Object.entries(porCcaa)) {
      const prevision = puntosPrevision(a?.prevision);
      if (!/^\d{2}$/.test(codigo) || !prevision.length) continue;
      renovables.set(codigo, {
        modelo: texto(v.modelo)!, miembros: miembros(v.miembros), errorValidacion: numero(v.error_validacion), errorTest: numero(v.error_test),
        aciertoValidacion: numero(v.acierto_validacion), aciertoTest: numero(v.acierto_test), historia: puntos(a.historia), prevision,
        nombre: texto(a.nombre) ?? codigo, media12m: numero(a.media_12m_actual), mediaPrevista: numero(a.media_prevista),
        mediaInferior: numero(a.media_inferior), mediaSuperior: numero(a.media_superior),
        aciertoAnualValidacion: numero(v.acierto_anual_validacion), aciertoAnualTest: numero(v.acierto_anual_test),
      });
    }
  }
  const diez = raiz.demanda_10_anios;
  const anual = (v: unknown) =>
    Array.isArray(v) ? v.map((x) => ({ ...(x as Record<string, unknown>), mes: `${(x as Record<string, unknown>)?.anio}-01` })) : [];
  const demanda10 =
    diez && texto(diez.modelo)
      ? {
          modelo: texto(diez.modelo)!, miembros: miembros(diez.miembros), errorValidacion: numero(diez.mape_medio), errorTest: null,
          aciertoValidacion: numero(diez.acierto), aciertoTest: null, acierto: numero(diez.acierto),
          historia: puntos(anual(diez.historia)), prevision: puntosPrevision(anual(diez.prevision)),
        }
      : null;
  const control = Array.isArray((json as Record<string, unknown>).control_acierto)
    ? ((json as Record<string, unknown>).control_acierto as Record<string, unknown>[]).flatMap((c) =>
        texto(c?.modelo) && texto(c?.estado) ? [{ modelo: texto(c.modelo)!, estado: texto(c.estado)! }] : [],
      )
    : [];
  if (!precio && !demanda.size && !reservas.size && !temperatura.size && !renovables.size && !demanda10) return null;
  return {
    generado: texto((json as Record<string, unknown>).generado), precio, demanda, demandaModelo, reservas, temperatura, renovables,
    demanda10: demanda10?.prevision.length ? demanda10 : null, control,
  };
}
