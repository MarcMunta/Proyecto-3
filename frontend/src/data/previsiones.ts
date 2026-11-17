/**
 * Previsión a 1 año (python -m cpd.modelos → data/curated/modelos/previsiones_1_anio.json, que npm run data copia
 * a public/data/previsiones.json): precio de la luz nacional y demanda eléctrica de cada comunidad, mes a mes.
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
  historia: PuntoMes[];
  prevision: PuntoPrevision[];
}

export interface Previsiones {
  generado: string | null;
  precio: (SeriePrevista & { mediaPrevista: number | null; futuroGasAnio: number | null }) | null;
  /** Por código INE de comunidad (dos dígitos). */
  demanda: Map<string, SeriePrevista & { nombre: string }>;
  demandaModelo: { modelo: string; miembros: string[]; errorValidacion: number | null; errorTest: number | null } | null;
}

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
      demanda.set(codigo, { ...demandaModelo, nombre: texto(c.nombre) ?? codigo, historia: puntos(c.historia), prevision });
    }
  }
  if (!precio && !demanda.size) return null;
  return { generado: texto((json as Record<string, unknown>).generado), precio, demanda, demandaModelo };
}
