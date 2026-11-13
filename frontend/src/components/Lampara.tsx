import type { EstadoMapa } from "../data/types";
import { COLOR_ESTADO } from "../model/colores";

/**
 * Lámpara de estado. Cada estado tiene su propia forma además del color
 * (círculo, triángulo, aspa, aro apagado), para no depender solo del color.
 */
export function Lampara({ estado, tam = 14 }: { estado: EstadoMapa; tam?: number }) {
  const c = COLOR_ESTADO[estado];
  return (
    <svg className="lampara" width={tam} height={tam} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {estado === "Viable" && <circle cx="8" cy="8" r="6.5" fill={c} />}
      {estado === "Viable con condiciones" && <path d="M8 1.2 15.2 14.4H.8Z" fill={c} />}
      {estado === "No viable" && (
        <path d="M2.5 2.5 13.5 13.5M13.5 2.5 2.5 13.5" stroke={c} strokeWidth="3.4" strokeLinecap="square" />
      )}
      {estado === "Sin datos" && <circle cx="8" cy="8" r="5.6" fill="none" stroke={c} strokeWidth="1.8" />}
    </svg>
  );
}
