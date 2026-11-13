import { useMemo, useState } from "react";
import type { Agregado, EstadoMapa, Municipio, ProvinciaMeta, Viabilidad } from "../data/types";
import { filasTablero } from "../data/agregar";
import { hora, normalizar, num } from "../format";
import { Flap } from "./Flap";
import { Lampara } from "./Lampara";

interface Props {
  meta: ProvinciaMeta[];
  datos: Viabilidad;
  agregado: Agregado;
  porIne: Map<string, Municipio>;
  onProvincia: (codigo: string) => void;
  onResaltar: (codigo: string | null) => void;
}

const CORTO: Record<EstadoMapa, string> = {
  Viable: "VIABLE",
  "Viable con condiciones": "CONDIC.",
  "No viable": "NO VIABLE",
  "Sin datos": "SIN DATOS",
};

/** Nombre corto para las 13 casillas del panel (el nombre oficial completo va en la etiqueta accesible). */
const NOMBRE_PANEL: Record<string, string> = {
  "01": "Álava",
  "03": "Alicante",
  "12": "Castellón",
  "35": "Las Palmas",
  "38": "S.C. Tenerife",
  "46": "Valencia",
};
const CASILLAS_NOMBRE = 13;

export function Tablero({ meta, datos, agregado, porIne, onProvincia, onResaltar }: Props) {
  const [busca, setBusca] = useState("");
  const filas = useMemo(() => filasTablero(meta, datos, agregado, porIne), [meta, datos, agregado, porIne]);
  const visibles = useMemo(() => {
    const q = normalizar(busca.trim());
    if (!q) return filas;
    return filas.filter((f) => normalizar(f.meta.nombre).includes(q) || f.meta.codigo.startsWith(q) || normalizar(f.meta.capital).includes(q));
  }, [filas, busca]);

  const cuenta = (e: EstadoMapa) => filas.filter((f) => f.estado === e).length;
  const conDatos = filas.filter((f) => f.resumen).length;
  const horaDato = hora(Date.parse(datos.generado));
  const marcaDato = datos.fuente.sintetico ? "DEMO" : "MODELO";

  return (
    <section className="tablero-lista" aria-labelledby="t-provincias">
      <header className="tablero-cab">
        <h2 id="t-provincias">Provincias</h2>
        <p className="tablero-recuento">
          <strong>{conDatos}</strong> con datos · <strong>{filas.length - conDatos}</strong> sin datos todavía
        </p>
        <ul className="recuento-estados" aria-label="Recuento por estado">
          {(["Viable", "Viable con condiciones", "No viable"] as const).map((e) => (
            <li key={e}>
              <Lampara estado={e} tam={13} />
              <span className="recuento-n">{cuenta(e)}</span>
              <span>{e === "Viable" ? "viables" : e === "No viable" ? "no viables" : "con condiciones"}</span>
            </li>
          ))}
        </ul>
        <p className="tablero-regla">
          El score ordena, el estado decide: un solo filtro eliminatorio deja una provincia en «No viable» aunque su
          score sea alto.
        </p>
        <label className="buscador">
          <span className="sr-only">Buscar provincia</span>
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar provincia o capital"
            autoComplete="off"
            spellCheck={false}
          />
        </label>
      </header>

      <div className="panel-salidas">
        <div className="fila fila-cabecera" aria-hidden="true">
          <span>Cód</span>
          <span>Destino</span>
          <span>Estado</span>
          <span className="der">Score</span>
          <span className="der fila-dato">Dato</span>
        </div>
        <ol className="filas">
          {visibles.map((f, i) => {
            const retardo = Math.min(i, 26) * 30;
            return (
              <li key={f.meta.codigo}>
                <button
                  type="button"
                  className={`fila ${f.resumen ? "" : "fila-sin-datos"}`}
                  title={f.meta.nombre}
                  onClick={() => onProvincia(f.meta.codigo)}
                  onMouseEnter={() => onResaltar(f.meta.codigo)}
                  onMouseLeave={() => onResaltar(null)}
                  onFocus={() => onResaltar(f.meta.codigo)}
                  onBlur={() => onResaltar(null)}
                  aria-label={`${f.meta.codigo} ${f.meta.nombre}: ${f.resumen ? `${f.estado}, score ${num(f.score, 1)}` : "sin datos todavía"}`}
                >
                  <Flap texto={f.meta.codigo} largo={2} className="flap-codigo" retardo={retardo} />
                  <Flap texto={NOMBRE_PANEL[f.meta.codigo] ?? f.meta.nombre} largo={CASILLAS_NOMBRE} className="flap-nombre" retardo={retardo + 40} />
                  <span className="fila-estado">
                    <Lampara estado={f.estado} tam={13} />
                    <span>{CORTO[f.estado]}</span>
                  </span>
                  <span className="der">
                    {f.resumen ? <Flap texto={num(f.score, 0)} largo={3} alinear="der" retardo={retardo + 90} /> : <span className="guion">—</span>}
                  </span>
                  <span className="der fila-dato">
                    {f.resumen ? (
                      <>
                        <span className="fila-hora">{horaDato}</span>
                        <span className="fila-marca">{marcaDato}</span>
                      </>
                    ) : (
                      <span className="guion">—</span>
                    )}
                  </span>
                </button>
              </li>
            );
          })}
          {!visibles.length && <li className="vacio">Ninguna provincia coincide con «{busca}».</li>}
        </ol>
      </div>
    </section>
  );
}
