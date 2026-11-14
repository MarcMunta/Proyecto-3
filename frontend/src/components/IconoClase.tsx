import type { ClaseRentabilidad } from "../data/prediccion";
import { BARRAS_CLASE, colorClase } from "../model/colores";

/**
 * Icono de rentabilidad: tres barras como la cobertura de un móvil (3 = alta, 2 = media, 1 = baja),
 * y una barra cruzada para «no rentable». La forma dice la clase aunque no se distinga el color.
 */
export function IconoClase({ clase, tam = 16 }: { clase: ClaseRentabilidad | null; tam?: number }) {
  const encendidas = clase ? BARRAS_CLASE[clase] : 0;
  const color = colorClase(clase);
  return (
    <svg className="icono-clase" width={tam} height={tam} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {[0, 1, 2].map((i) => (
        <rect key={i} x={1 + i * 5} y={11 - i * 4} width="4" height={4 + i * 4} fill={i < encendidas ? color : "#3b3d43"} />
      ))}
      {clase === "no_rentable" && <path d="M1.5 14.5 14.5 1.5" stroke={color} strokeWidth="2.4" strokeLinecap="square" />}
    </svg>
  );
}
