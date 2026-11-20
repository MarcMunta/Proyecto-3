import type { ClaseRentabilidad } from "../data/prediccion";
import { BARRAS_CLASE, colorClase } from "../model/colores";

/** Gris de las barras apagadas (alta, media y baja) y trazo de las barras vacías («No viable» / «No rentable»). */
const APAGADA = "#3b3d43";
const VACIA = "#6b6d74";
/** Color de la superficie de las fichas: separa el distintivo de las barras que pisa. */
const SUPERFICIE = "#17181b";

/**
 * Icono de rentabilidad: tres barras como la cobertura de un móvil (3 = alta, 2 = media, 1 = baja).
 * «No viable» / «No rentable» = sin cobertura: barras vacías y un distintivo rojo con una ×. La forma dice la
 * clase aunque no se distinga el color.
 */
export function IconoClase({ clase, tam = 16 }: { clase: ClaseRentabilidad | null; tam?: number }) {
  const encendidas = clase ? BARRAS_CLASE[clase] : 0;
  const color = colorClase(clase);
  const sinCobertura = clase === "no_rentable";
  return (
    <svg className="icono-clase" width={tam} height={tam} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {[0, 1, 2].map((i) =>
        sinCobertura ? (
          <rect key={i} x={1.6 + i * 5} y={11.6 - i * 4} width="2.8" height={2.8 + i * 4} fill="none" stroke={VACIA} strokeWidth="1.2" rx="0.4" />
        ) : (
          <rect key={i} x={1 + i * 5} y={11 - i * 4} width="4" height={4 + i * 4} fill={i < encendidas ? color : APAGADA} />
        ),
      )}
      {sinCobertura && (
        <g>
          <circle cx="5" cy="5" r="4.4" fill={color} stroke={SUPERFICIE} strokeWidth="1.2" />
          <path d="M3.4 3.4 6.6 6.6M6.6 3.4 3.4 6.6" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
        </g>
      )}
    </svg>
  );
}
