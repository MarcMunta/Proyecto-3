import metaJson from "../data/provincias.json";
import type { Prediccion } from "../data/prediccion";
import { nombreClaseDe, ORDEN_CLASE } from "../model/colores";

const TOTAL_PROVINCIAS = metaJson.length;
import { IconoClase } from "./IconoClase";

/** Leyenda compacta del mapa: las cuatro clases (icono + nombre + cuántas provincias) y «sin datos». */
export function Leyenda({ prediccion }: { prediccion: Prediccion }) {
  const legado = prediccion.origen === "legado" || prediccion.tipo === "demo";
  const cuenta = (c: string | null) => [...prediccion.provincias.values()].filter((p) => p.clase === c).length;
  const sinDatos = TOTAL_PROVINCIAS - [...prediccion.provincias.values()].filter((p) => p.clase).length;
  return (
    <div className="leyenda" role="group" aria-label="Leyenda: rentabilidad">
      <span className="leyenda-t">{prediccion.tipo === "real" ? "Rentabilidad" : "Rentabilidad relativa"}</span>
      <ul>
        {ORDEN_CLASE.map((c) => (
          <li key={c}>
            <IconoClase clase={c} tam={14} />
            <span>{nombreClaseDe(c, null, legado)}</span>
            <span className="leyenda-n">{cuenta(c)}</span>
          </li>
        ))}
        {sinDatos > 0 && (
          <li className="leyenda-sin">
            <span className="muestra-rayado" aria-hidden="true" />
            <span>Sin datos</span>
            <span className="leyenda-n">{sinDatos}</span>
          </li>
        )}
      </ul>
    </div>
  );
}
