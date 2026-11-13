import type { EstadoMapa } from "../data/types";

// Mismos valores que las variables CSS de styles.css (el mapa WebGL no lee CSS).
export const C = {
  suelo: "#111214",
  contexto: "#1d1e21",
  junta: "#08090a",
  modulo: "#1b1d20",
  regla: "#2e3136",
  caracter: "#f1ecdf",
  caracterTenue: "#b6b0a3",
  amarillo: "#ffcc33",
  viable: "#3fd27f",
  condiciones: "#ff9c40",
  noViable: "#ff5b4b",
  sinDatos: "#6c6f75",
} as const;

export const COLOR_ESTADO: Record<EstadoMapa, string> = {
  Viable: C.viable,
  "Viable con condiciones": C.condiciones,
  "No viable": C.noViable,
  "Sin datos": C.sinDatos,
};

export const ETIQUETA_ESTADO: Record<EstadoMapa, string> = {
  Viable: "VIABLE",
  "Viable con condiciones": "CON CONDICIONES",
  "No viable": "NO VIABLE",
  "Sin datos": "SIN DATOS",
};

// Rampa de luminancia cálida: un panel apagado (score bajo) se va "encendiendo" hacia el blanco cálido.
const RAMPA: [number, [number, number, number]][] = [
  [0, [0x2a, 0x2a, 0x2c]],
  [25, [0x4b, 0x46, 0x3e]],
  [50, [0x7d, 0x71, 0x5c]],
  [75, [0xbd, 0xaa, 0x80]],
  [100, [0xf3, 0xe3, 0xb8]],
];
export const PARADAS_RAMPA = RAMPA.map(([v, [r, g, b]]) => [v, `rgb(${r},${g},${b})`] as const);

export function colorScore(score: number | null | undefined): string {
  if (score == null || !Number.isFinite(score)) return C.sinDatos;
  const s = Math.min(100, Math.max(0, score));
  for (let i = 1; i < RAMPA.length; i++) {
    const [v1, c1] = RAMPA[i]!;
    const [v0, c0] = RAMPA[i - 1]!;
    if (s <= v1) {
      const t = (s - v0) / (v1 - v0);
      const mezcla = c0.map((c, k) => Math.round(c + (c1[k]! - c) * t));
      return `rgb(${mezcla.join(",")})`;
    }
  }
  return PARADAS_RAMPA[PARADAS_RAMPA.length - 1]![1];
}

/** Texto legible encima de un color de la rampa. */
export const textoSobreScore = (score: number | null | undefined) =>
  score != null && score >= 58 ? "#141414" : C.caracter;
