// Datos en vivo de Red Eléctrica (REData, https://www.ree.es/es/apidatos). Sin clave, con CORS abierto.
// Todo es NACIONAL (sistema peninsular), no por provincia.
import { fechaMadrid } from "../format";

const BASE = "https://apidatos.ree.es/es/datos";
const TIEMPO_MAX_MS = 15000;

export interface Punto {
  t: number;
  v: number;
}

interface RespuestaRee {
  included?: { type?: string; attributes?: { title?: string; values?: { value: number; datetime: string; percentage?: number }[] } }[];
}

async function pedir(ruta: string, signal?: AbortSignal): Promise<RespuestaRee> {
  const control = new AbortController();
  const corte = setTimeout(() => control.abort(new Error("tiempo de espera agotado")), TIEMPO_MAX_MS);
  signal?.addEventListener("abort", () => control.abort(signal.reason), { once: true });
  try {
    const r = await fetch(`${BASE}${ruta}`, { signal: control.signal, headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(`REData respondió ${r.status}`);
    return (await r.json()) as RespuestaRee;
  } finally {
    clearTimeout(corte);
  }
}

function serie(json: RespuestaRee, titulo: string, campo: "value" | "percentage" = "value"): Punto[] {
  const bloque = json.included?.find((i) => i.attributes?.title === titulo || i.type === titulo);
  return (bloque?.attributes?.values ?? [])
    .map((x) => ({ t: Date.parse(x.datetime), v: Number(campo === "value" ? x.value : x.percentage) }))
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
    .sort((a, b) => a.t - b.t);
}

const rango = (desde: string, hasta: string, trunc: "hour" | "day") =>
  `start_date=${desde}T00:00&end_date=${hasta}T23:59&time_trunc=${trunc}`;

const dia = (offsetDias: number) => fechaMadrid(Date.now() + offsetDias * 86400000);

const ultimoHasta = (s: Punto[], t: number) => {
  let r: Punto | undefined;
  for (const p of s) if (p.t <= t) r = p;
  return r;
};
const media = (s: Punto[]) => (s.length ? s.reduce((a, p) => a + p.v, 0) / s.length : null);

export interface Precios {
  /** Mercado diario (OMIE) en España, cada 15 min, €/MWh. */
  spot: Punto[];
  /** Precio voluntario al pequeño consumidor, horario, €/MWh. */
  pvpc: Punto[];
  spotAhora: Punto | null;
  spotMediaHoy: number | null;
  spotMediaManana: number | null;
  pvpcAhora: Punto | null;
}

export async function precios(signal?: AbortSignal): Promise<Precios> {
  const json = await pedir(`/mercados/precios-mercados-tiempo-real?${rango(dia(0), dia(1), "hour")}`, signal);
  const spot = serie(json, "Precio mercado spot");
  const pvpc = serie(json, "PVPC");
  if (!spot.length) throw new Error("REData no devolvió precios spot");
  const hoy = dia(0);
  const manana = dia(1);
  const spotHoy = spot.filter((p) => fechaMadrid(p.t) === hoy);
  const spotManana = spot.filter((p) => fechaMadrid(p.t) === manana);
  const ahora = Date.now();
  return {
    spot: spotHoy,
    pvpc: pvpc.filter((p) => fechaMadrid(p.t) === hoy),
    spotAhora: ultimoHasta(spotHoy, ahora) ?? null,
    spotMediaHoy: media(spotHoy),
    // El mercado diario publica el día siguiente hacia las 13:00; antes no hay datos de mañana.
    spotMediaManana: spotManana.length >= 90 ? media(spotManana) : null,
    pvpcAhora: ultimoHasta(pvpc, ahora) ?? null,
  };
}

export interface Demanda {
  real: Punto[];
  prevista: Punto[];
  ahora: Punto | null;
}

export async function demanda(signal?: AbortSignal): Promise<Demanda> {
  const json = await pedir(`/demanda/demanda-tiempo-real?${rango(dia(0), dia(0), "hour")}`, signal);
  const real = serie(json, "Real");
  const prevista = serie(json, "Prevista");
  if (!real.length) throw new Error("REData no devolvió demanda real");
  return { real, prevista, ahora: real[real.length - 1] ?? null };
}

export interface Mix {
  /** % renovable del último día completo (ayer). */
  renovableAyer: Punto | null;
  /** % renovable de hoy hasta ahora. */
  renovableHoy: Punto | null;
  /** t CO2 eq. por MWh generado, último día completo. */
  factorCo2Ayer: Punto | null;
}

export async function mix(signal?: AbortSignal): Promise<Mix> {
  const q = rango(dia(-7), dia(0), "day");
  const [renov, co2] = await Promise.all([
    pedir(`/generacion/evolucion-renovable-no-renovable?${q}`, signal),
    pedir(`/generacion/no-renovables-detalle-emisiones-CO2?${q}`, signal),
  ]);
  const pctRenov = serie(renov, "Renovable", "percentage");
  const factor = serie(co2, "tCO2 eq./MWh");
  const hoy = dia(0);
  const completo = (s: Punto[]) => [...s].reverse().find((p) => fechaMadrid(p.t) < hoy) ?? null;
  return {
    renovableAyer: completo(pctRenov),
    renovableHoy: pctRenov.find((p) => fechaMadrid(p.t) === hoy) ?? null,
    factorCo2Ayer: completo(factor),
  };
}
