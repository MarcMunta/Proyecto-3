import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";

export type Estado = "Viable" | "Viable con condiciones" | "No viable";
export type EstadoMapa = Estado | "Sin datos";

export const BLOQUES = [
  "energia",
  "agua_refrigeracion",
  "conectividad",
  "riesgos_naturales",
  "suelo_regulatorio",
  "costes",
  "mercado_talento",
  "impacto",
] as const;
export type Bloque = (typeof BLOQUES)[number];

type Num = number | null;

export interface Salidas {
  pue_estimado: Num;
  pue_aplicado: Num;
  potencia_total_mw: Num;
  consumo_mwh: Num;
  agua_m3_anual: Num;
  coste_energia_eur: Num;
  opex_energia_eur: Num;
  opex_agua_eur: Num;
  opex_personal_eur: Num;
  opex_mantenimiento_eur: Num;
  opex_impuestos_eur: Num;
  opex_eur: Num;
  co2_t: Num;
  impacto_local_pct: Num;
  latencia_rtt_ms: Num;
  coste_suelo_eur: Num;
  capex_total_eur: Num;
  ingresos_alquiler_eur: Num;
  ingresos_energia_eur: Num;
  ingresos_anuales_eur: Num;
  flujo_caja_anual_eur: Num;
  van_eur: Num;
  roi: Num;
  payback_anos: Num;
}

export interface Municipio {
  codigo_ine: string;
  municipio: string;
  provincia_codigo: string;
  provincia: string | null;
  ccaa: string | null;
  lat: Num;
  lon: Num;
  origen_datos: string;
  sintetico: boolean;
  ranking: number;
  estado: Estado;
  motivos: string[];
  score_global: Num;
  sub: Record<Bloque, Num>;
  entradas: Partial<Record<string, Num>>;
  salidas: Salidas;
}

export interface ResumenProvincia {
  codigo: string;
  municipios: string[];
  mejor: string;
  estado: Estado;
  conteo_estados: Partial<Record<Estado, number>>;
  score_max: Num;
  score_medio: Num;
  n_municipios: number;
}

export interface Viabilidad {
  generado: string;
  fuente: { fichero: string; sintetico: boolean; n_municipios: number; nota: string };
  parametros: {
    potencia_ti_mw: number;
    factor_carga: number;
    pue: number;
    wue_l_kwh: number;
    tipo_refrigeracion: string;
    pct_renovable: number;
    autoproduccion_mwh: number;
    inversion_eur: number;
    vida_util_anos: number;
    personal: number;
    latencia_max_ms: number;
    tier: string;
    usar_pue_estimado: boolean;
  };
  precios: {
    precio_electricidad_eur_mwh: number;
    precio_agua_eur_m3: number;
    salario_medio_eur: number;
    tasa_descuento: number;
    precio_venta_eur_kw_mes: number;
    ocupacion: number;
    repercusion_energia_pct: number;
    factor_emision_t_mwh: number;
    [k: string]: number;
  };
  pesos: Record<Bloque, number>;
  umbrales: Record<string, number | boolean>;
  latencia: Record<string, number>;
  municipios: Municipio[];
  provincias: Record<string, ResumenProvincia>;
}

export interface ProvinciaMeta {
  codigo: string;
  nombre: string;
  capital: string;
  lat: number;
  lon: number;
}

export interface PropsProvincia {
  codigo: string;
  nombre: string;
  n_municipios: number | null;
  area_km2: number | null;
  bbox: [number, number, number, number];
  etiqueta: [number, number] | null;
}

export type GeoProvincias = FeatureCollection<Polygon | MultiPolygon, PropsProvincia>;
export type GeoContexto = FeatureCollection<Polygon | MultiPolygon>;

/** Cómo resumir una provincia con varios municipios analizados. */
export type Agregado = "mejor" | "media";
