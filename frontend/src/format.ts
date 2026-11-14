// Formato de números y fechas en español (España).

const formatos = new Map<number, Intl.NumberFormat>();
function nf(decimales: number): Intl.NumberFormat {
  let f = formatos.get(decimales);
  if (!f) {
    f = new Intl.NumberFormat("es-ES", {
      minimumFractionDigits: decimales,
      maximumFractionDigits: decimales,
      useGrouping: "always",
    } as unknown as Intl.NumberFormatOptions);
    formatos.set(decimales, f);
  }
  return f;
}

const vacio = (v: number | null | undefined): v is null | undefined => v == null || !Number.isFinite(v);

export const SIN_VALOR = "—";

export function num(v: number | null | undefined, decimales = 0): string {
  return vacio(v) ? SIN_VALOR : nf(decimales).format(v);
}

/** Euros en millones: 412,5 M€ (o 1.234 M€). */
export function millones(v: number | null | undefined): string {
  if (vacio(v)) return SIN_VALOR;
  const m = v / 1e6;
  return `${num(m, Math.abs(m) >= 100 ? 0 : 1)} M€`;
}

/** Fracción 0-1 como porcentaje. */
export function pct(v: number | null | undefined, decimales = 0): string {
  return vacio(v) ? SIN_VALOR : `${num(v * 100, decimales)} %`;
}

const zona = "Europe/Madrid";
const fHora = new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit", timeZone: zona });
const fHoraSeg = new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: zona });
const fDiaHora = new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: zona });
const fISO = new Intl.DateTimeFormat("sv-SE", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: zona });

export const hora = (d: Date | number) => fHora.format(d);
export const horaSeg = (d: Date | number) => fHoraSeg.format(d);
export const diaHora = (d: Date | number) => fDiaHora.format(d).replace(",", "");
/** Fecha YYYY-MM-DD en hora peninsular española. */
export const fechaMadrid = (d: Date | number) => fISO.format(d);

const fHM = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: zona });
/** Índice 0-95 del cuarto de hora del día (hora peninsular). */
export function cuartoDelDia(t: number): number {
  const [h, m] = fHM.format(t).split(":").map(Number) as [number, number];
  return h * 4 + Math.floor(m / 15);
}

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
/** "2026-10" -> "octubre de 2026". */
export function mesLegible(aaaamm: string): string {
  const [a, m] = aaaamm.split("-").map(Number) as [number, number];
  return MESES[m - 1] ? `${MESES[m - 1]} de ${a}` : aaaamm;
}

/** "Acebeda, La" (formato GISCO) -> "La Acebeda". */
export function nombreMunicipio(nombre: string): string {
  const m = nombre.match(/^(.*), (La|El|Los|Las|Lo|A|O|Os|As|Es|Sa|Ses|Els|Les|L')$/);
  if (!m) return nombre;
  const [, resto, articulo] = m as unknown as [string, string, string];
  return articulo.endsWith("'") ? `${articulo}${resto}` : `${articulo} ${resto}`;
}

/** Quita tildes y pasa a minúsculas para buscar. */
export function normalizar(s: string): string {
  return s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}
