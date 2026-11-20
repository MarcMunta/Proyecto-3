import type { ClaseRentabilidad } from "../data/prediccion";
import type { Estado } from "../data/types";

// Mismos valores que las variables CSS de styles.css (el mapa WebGL no lee CSS).
export const C = {
  suelo: "#111214",
  superficie: "#17181b",
  contexto: "#1b1c1f",
  linea: "#26282c",
  texto: "#f1ecdf",
  texto2: "#b6b0a3",
  sinDatos: "#2b2d32",
  rayado: "#4f525a",
} as const;

/**
 * Rentabilidad: verde (alta) → amarillo (media) → naranja (baja) → rojo (no viable o VAN ≤ 0).
 * Tonos validados con scripts/validate_palette.js de la skill dataviz sobre #111214, todos los pares:
 * daltonismo ΔE ≥ 11 (deutan/protan), visión normal ΔE ≥ 15,2, contraste ≥ 3:1 con el fondo.
 * Nunca va solo: cada clase lleva además su icono de barras y su nombre.
 */
export const COLOR_CLASE: Record<ClaseRentabilidad, string> = {
  alta: "#40b97a",
  media: "#dcbc55",
  baja: "#e47b2f",
  no_rentable: "#b8383f",
};

export const NOMBRE_CLASE: Record<ClaseRentabilidad, string> = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
  // La 4.ª clase junta «no pasa un filtro eliminatorio» y «VAN ≤ 0». Con los datos actuales todas las provincias
  // de esta clase son «No viable» (con VAN positivo), así que el nombre general es ese; la ficha usa nombreClaseDe().
  no_rentable: "No viable",
};

/**
 * Nombre de la clase para una provincia concreta: en la 4.ª clase distingue «No viable» (no pasa un filtro
 * eliminatorio, aunque su VAN sea positivo) de «No rentable» (pasa los filtros pero su VAN es ≤ 0).
 */
export function nombreClaseDe(clase: ClaseRentabilidad, estado: Estado | null | undefined): string {
  if (clase === "no_rentable" && estado !== "No viable") return "No rentable";
  return NOMBRE_CLASE[clase];
}

/** Número de barras encendidas del icono (como la cobertura de un móvil). */
export const BARRAS_CLASE: Record<ClaseRentabilidad, number> = {
  alta: 3,
  media: 2,
  baja: 1,
  no_rentable: 0,
};

export const ORDEN_CLASE: ClaseRentabilidad[] = ["alta", "media", "baja", "no_rentable"];

export const colorClase = (c: ClaseRentabilidad | null | undefined) => (c ? COLOR_CLASE[c] : C.sinDatos);
