// Tiempo actual en las 52 capitales de provincia con una sola llamada a Open-Meteo
// (https://open-meteo.com, gratuito para uso no comercial, sin clave, CORS abierto).
import type { ProvinciaMeta } from "../data/types";

export interface TiempoActual {
  hora: number;
  temperatura_c: number;
  humedad_pct: number;
  viento_kmh: number;
}

interface RespuestaMeteo {
  current?: { time: string; temperature_2m: number; relative_humidity_2m: number; wind_speed_10m: number };
}

export async function tiempoCapitales(provincias: ProvinciaMeta[], signal?: AbortSignal): Promise<Record<string, TiempoActual>> {
  const lat = provincias.map((p) => p.lat.toFixed(2)).join(",");
  const lon = provincias.map((p) => p.lon.toFixed(2)).join(",");
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
    `&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Europe%2FMadrid&timeformat=unixtime`;
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`Open-Meteo respondió ${r.status}`);
  const json = (await r.json()) as RespuestaMeteo | RespuestaMeteo[];
  const lista = Array.isArray(json) ? json : [json];
  const salida: Record<string, TiempoActual> = {};
  lista.forEach((item, i) => {
    const p = provincias[i];
    const c = item.current;
    if (!p || !c) return;
    salida[p.codigo] = {
      hora: Number(c.time) * 1000,
      temperatura_c: c.temperature_2m,
      humedad_pct: c.relative_humidity_2m,
      viento_kmh: c.wind_speed_10m,
    };
  });
  if (!Object.keys(salida).length) throw new Error("Open-Meteo no devolvió datos");
  return salida;
}
