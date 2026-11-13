import type { Estado, Municipio, Viabilidad } from "../data/types";

export interface Recalculo {
  precio_eur_mwh: number;
  coste_energia_eur: number;
  opex_eur: number;
  ingresos_anuales_eur: number;
  flujo_caja_anual_eur: number;
  van_eur: number;
  roi: number | null;
  payback_anos: number | null;
}

/**
 * Repite las fórmulas de src/cpd/scoring.py (simular_municipio) cambiando SOLO el precio de la
 * electricidad. Así se puede responder "¿y si todo el año la luz costara como hoy?" con el precio
 * spot en vivo, sin tocar el resto de supuestos del modelo.
 *
 *   energía  = max(consumo − autoproducción, 0) × precio
 *   OPEX     = OPEX del modelo − energía del modelo + energía nueva
 *   ingresos = alquiler + energía nueva × repercusión al cliente
 *   flujo    = ingresos − OPEX            (constante cada año)
 *   VAN      = −CAPEX + Σ flujo / (1 + tasa)^t,  t = 1..vida útil
 *   ROI      = (flujo × años − CAPEX) / CAPEX
 *   payback  = CAPEX / flujo (si se recupera dentro de la vida útil)
 */
export function recalcularConPrecio(m: Municipio, precio: number, d: Viabilidad): Recalculo | null {
  const s = m.salidas;
  const capex = s.capex_total_eur;
  if (
    s.consumo_mwh == null || s.opex_eur == null || s.opex_energia_eur == null ||
    s.ingresos_alquiler_eur == null || capex == null || !Number.isFinite(precio)
  ) {
    return null;
  }
  const anos = Math.trunc(d.parametros.vida_util_anos);
  const tasa = d.precios.tasa_descuento;
  const energia = Math.max(s.consumo_mwh - d.parametros.autoproduccion_mwh, 0) * precio;
  const opex = s.opex_eur - s.opex_energia_eur + energia;
  const ingresos = s.ingresos_alquiler_eur + energia * (d.precios.repercusion_energia_pct ?? 0);
  const flujo = ingresos - opex;
  let van = -capex;
  for (let t = 1; t <= anos; t++) van += flujo / (1 + tasa) ** t;
  const roi = capex > 0 ? (flujo * anos - capex) / capex : null;
  let payback: number | null = null;
  if (capex <= 0) payback = 0;
  else if (flujo > 0 && capex / flujo <= anos) payback = capex / flujo;
  return {
    precio_eur_mwh: precio,
    coste_energia_eur: energia,
    opex_eur: opex,
    ingresos_anuales_eur: ingresos,
    flujo_caja_anual_eur: flujo,
    van_eur: van,
    roi,
    payback_anos: payback,
  };
}

export type TipoMotivo = "ko" | "condicion" | "aviso" | "ok";

// Textos de cpd.scoring.aplicar_filtros(): los KO llevan al estado "No viable".
const PATRONES_KO = [
  /^Zona inundable/,
  /^Espacio Red Natura/,
  /^Subestación a /,
  /^Capacidad de acceso/,
  /^Latencia RTT/,
  /^Estrés hídrico [\d.,]+ con refrigeración/,
];

export function tipoMotivo(texto: string, estado: Estado): TipoMotivo {
  if (texto.startsWith("Aviso")) return "aviso";
  if (texto.startsWith("Cumple")) return "ok";
  if (estado === "No viable" && PATRONES_KO.some((p) => p.test(texto))) return "ko";
  return "condicion";
}

/** Horas de "free cooling": por debajo de este umbral el aire exterior basta para enfriar (simulator.horas_free_cooling). */
export const UMBRAL_FREE_COOLING_C = 18;
