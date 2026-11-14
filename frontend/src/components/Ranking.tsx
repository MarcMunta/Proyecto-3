import { useMemo, useState } from "react";
import type { ProvinciaMeta } from "../data/types";
import type { ClaseRentabilidad, Prediccion, ProvinciaPrediccion } from "../data/prediccion";
import { diaHora, millones, normalizar } from "../format";
import { COLOR_CLASE, NOMBRE_CLASE, ORDEN_CLASE } from "../model/colores";
import { IconoClase } from "./IconoClase";

interface Props {
  meta: ProvinciaMeta[];
  prediccion: Prediccion;
  onProvincia: (codigo: string) => void;
  onResaltar: (codigo: string | null) => void;
}

interface Fila {
  meta: ProvinciaMeta;
  d: ProvinciaPrediccion | undefined;
}

const porValor = (a: Fila, b: Fila) =>
  (b.d?.van_eur ?? -Infinity) - (a.d?.van_eur ?? -Infinity) ||
  (b.d?.score ?? -1) - (a.d?.score ?? -1) ||
  a.meta.nombre.localeCompare(b.meta.nombre, "es");

/** Vista nacional: reparto por clase (una barra) y las provincias agrupadas por rentabilidad. */
export function Ranking({ meta, prediccion, onProvincia, onResaltar }: Props) {
  const [busca, setBusca] = useState("");
  const filas = useMemo(() => meta.map((m) => ({ meta: m, d: prediccion.provincias.get(m.codigo) })), [meta, prediccion]);
  const q = normalizar(busca.trim());
  const coincide = (f: Fila) => !q || normalizar(f.meta.nombre).includes(q) || normalizar(f.meta.capital).includes(q);

  const grupos = ORDEN_CLASE.map((c) => ({ clase: c, filas: filas.filter((f) => f.d?.clase === c).sort(porValor) }));
  const sinDatos = filas.filter((f) => !f.d?.clase).sort((a, b) => a.meta.nombre.localeCompare(b.meta.nombre, "es"));
  const total = filas.length;

  const fila = (f: Fila) => (
    <li key={f.meta.codigo}>
      <button
        type="button"
        className="fila"
        onClick={() => onProvincia(f.meta.codigo)}
        onMouseEnter={() => onResaltar(f.meta.codigo)}
        onMouseLeave={() => onResaltar(null)}
        onFocus={() => onResaltar(f.meta.codigo)}
        onBlur={() => onResaltar(null)}
        aria-label={`${f.meta.nombre}: rentabilidad ${f.d?.clase ? NOMBRE_CLASE[f.d.clase].toLowerCase() : "sin datos"}${f.d?.van_eur != null ? `, VAN ${millones(f.d.van_eur)}` : ""}`}
      >
        <span className="fila-nombre">{f.meta.nombre}</span>
        {f.d?.van_eur != null && <span className="fila-valor">{millones(f.d.van_eur)}</span>}
      </button>
    </li>
  );

  return (
    <section className="ranking" aria-labelledby="r-titulo">
      <header className="ranking-cab">
        <h2 id="r-titulo">Rentabilidad de un CPD por provincia</h2>
        <p className="sub">
          {prediccion.tipo === "real"
            ? `Predicción del modelo${prediccion.generado ? ` · ${diaHora(Date.parse(prediccion.generado))}` : ""}`
            : prediccion.tipo === "simulacion"
              ? `Simulación con datos reales${prediccion.actualizado ? ` · actualizados el ${diaHora(Date.parse(prediccion.actualizado))}` : ""}`
              : `Demostración con datos sintéticos · ${prediccion.provincias.size} de ${total} provincias`}
        </p>
        <div className="reparto" role="img" aria-label={`${grupos.map((g) => `${g.filas.length} ${NOMBRE_CLASE[g.clase].toLowerCase()}`).join(", ")}, ${sinDatos.length} sin datos`}>
          {grupos.map((g) =>
            g.filas.length ? <span key={g.clase} style={{ flexGrow: g.filas.length, background: COLOR_CLASE[g.clase] }} /> : null,
          )}
          {sinDatos.length > 0 && <span className="reparto-sin" style={{ flexGrow: sinDatos.length }} />}
        </div>
        <ul className="reparto-ley">
          {grupos.map((g) => (
            <li key={g.clase}>
              <IconoClase clase={g.clase} tam={13} />
              <strong>{g.filas.length}</strong> {NOMBRE_CLASE[g.clase].toLowerCase()}
            </li>
          ))}
          {sinDatos.length > 0 && (
            <li>
              <span className="muestra-rayado" aria-hidden="true" />
              <strong>{sinDatos.length}</strong> sin datos
            </li>
          )}
        </ul>
        {prediccion.tipo !== "real" && (
          <p className="nota-clase">Clase relativa entre provincias: tercios del VAN simulado; «no viable» cuenta como no rentable.</p>
        )}
        <label className="buscador">
          <span className="sr-only">Buscar provincia</span>
          <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar provincia" autoComplete="off" spellCheck={false} />
        </label>
      </header>

      {grupos.map((g) => {
        const visibles = g.filas.filter(coincide);
        if (!visibles.length) return null;
        return (
          <section key={g.clase} className="grupo" aria-labelledby={`g-${g.clase}`}>
            <h3 id={`g-${g.clase}`}>
              <IconoClase clase={g.clase as ClaseRentabilidad} tam={15} />
              {NOMBRE_CLASE[g.clase]}
              <span className="grupo-n">{g.filas.length}</span>
            </h3>
            <ol>{visibles.map(fila)}</ol>
          </section>
        );
      })}

      {sinDatos.some(coincide) && (
        <details className="grupo grupo-sin" open={Boolean(q)}>
          <summary>
            <span className="muestra-rayado" aria-hidden="true" />
            Sin datos todavía
            <span className="grupo-n">{sinDatos.length}</span>
          </summary>
          <ol>{sinDatos.filter(coincide).map(fila)}</ol>
        </details>
      )}
      {!filas.some(coincide) && <p className="vacio">Ninguna provincia coincide con «{busca}».</p>}
    </section>
  );
}
