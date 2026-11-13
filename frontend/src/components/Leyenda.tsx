import type { Agregado } from "../data/types";
import { PARADAS_RAMPA } from "../model/colores";
import { Lampara } from "./Lampara";

const degradado = `linear-gradient(90deg, ${PARADAS_RAMPA.map(([v, c]) => `${c} ${v}%`).join(", ")})`;

export function Leyenda({ agregado, onAgregado }: { agregado: Agregado; onAgregado: (a: Agregado) => void }) {
  return (
    <div className="leyenda">
      <fieldset className="conmutador">
        <legend>Color de cada provincia</legend>
        <label>
          <input type="radio" name="agregado" checked={agregado === "mejor"} onChange={() => onAgregado("mejor")} />
          <span>Mejor emplazamiento</span>
        </label>
        <label>
          <input type="radio" name="agregado" checked={agregado === "media"} onChange={() => onAgregado("media")} />
          <span>Media provincial</span>
        </label>
      </fieldset>
      <div className="leyenda-rampa">
        <span className="leyenda-t">Score 0–100</span>
        <span className="rampa" style={{ background: degradado }} />
        <span className="rampa-marcas" aria-hidden="true">
          <span>0</span>
          <span>50</span>
          <span>100</span>
        </span>
      </div>
      <ul className="leyenda-estados">
        <li>
          <span className="muestra-rayado" aria-hidden="true" /> Sin datos todavía
        </li>
        <li>
          <Lampara estado="Viable" tam={12} /> Viable
        </li>
        <li>
          <Lampara estado="Viable con condiciones" tam={12} /> Con condiciones
        </li>
        <li>
          <Lampara estado="No viable" tam={12} /> No viable
        </li>
      </ul>
    </div>
  );
}
