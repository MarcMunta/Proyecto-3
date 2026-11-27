import { useEffect, useRef, useState } from "react";
import type { Prediccion } from "../data/prediccion";
import type { EvaluacionModelo, Previsiones } from "../data/previsiones";
import { normalizar, num } from "../format";
import { Flecha } from "./Piezas";

import { EvaluacionesModelos } from "./EvaluacionesModelos";

function EscenariosCalculados({ previsiones }: { previsiones: Previsiones }) {
  const escenario = previsiones.escenarioDemanda;
  const socio = previsiones.socioeconomico;
  if (!escenario && !socio) return null;
  return (
    <section className="modelos-escenarios" aria-labelledby="otros-calculos">
      <h3 id="otros-calculos">Cálculos por escenario</h3>
      {escenario && (
        <details className="modelo-fila">
          <summary>Demanda adicional por acceso a la red</summary>
          <div className="modelo-detalle">
            <p className="modelo-formula">Energía anual (TWh) = potencia otorgada (MW) × 8.760 h × factor de utilización ÷ 1.000.000</p>
            {escenario.mwOtorgados !== null && escenario.factor !== null && escenario.twhOtorgados !== null && (
              <p className="modelo-formula">{num(escenario.mwOtorgados)} × 8.760 × {num(escenario.factor, 2)} ÷ 1.000.000 ≈ {num(escenario.twhOtorgados, 1)} TWh/año</p>
            )}
            <p>Supuesto de utilización sobre capacidad otorgada. La cifra se añade a la demanda tendencial en los escenarios.</p>
          </div>
        </details>
      )}
      {socio && (
        <details className="modelo-fila">
          <summary>Empleo e impacto económico</summary>
          <div className="modelo-detalle">
            <p className="modelo-formula">Empleo de operación = plantilla directa + empleo indirecto en proveedores</p>
            {socio.empleoDirecto !== null && socio.empleoIndirecto !== null && (
              <p className="modelo-formula">{num(socio.empleoDirecto, 1)} + {num(socio.empleoIndirecto, 1)} ≈ {num(socio.empleoDirecto + socio.empleoIndirecto, 1)} empleos equivalentes a tiempo completo</p>
            )}
            <p>El impacto indirecto se estima con las tablas input-output del INE y el gasto del escenario.</p>
          </div>
        </details>
      )}
    </section>
  );
}

export function CatalogoModelos({ previsiones, prediccion, cargando, zona, volver }: {
  previsiones: Previsiones | null; prediccion?: Prediccion; cargando: boolean; zona?: string; volver: string;
}) {
  const titulo = useRef<HTMLHeadingElement>(null);
  const [busqueda, setBusqueda] = useState("");
  useEffect(() => { titulo.current?.focus({ preventScroll: true }); }, []);
  const control = previsiones?.control ?? [];
  const consulta = normalizar(busqueda.trim());
  const coincide = (fila: EvaluacionModelo) => normalizar(fila.modelo).includes(consulta);
  const filas = [...control.filter((f) => coincide(f) && f.modelo.startsWith("Precio de la luz")),
    ...control.filter((f) => coincide(f) && !f.modelo.startsWith("Precio de la luz"))];
  return (
    <section className="modelos" aria-labelledby="titulo-modelos">
      <a className="volver" href={volver}><Flecha /> {zona ? `Ficha de ${zona}` : "Todas las provincias"}</a>
      <header className="ficha-cab">
        <h2 id="titulo-modelos" tabIndex={-1} ref={titulo}>Modelos y cálculos</h2>
        <p className="sub">Evaluación general de los modelos publicados. Abre una fila para ver su método y cálculo.</p>
      </header>
      {cargando && <p role="status">Cargando modelos…</p>}
      {!cargando && !control.length && <p role="status">No hay evaluaciones disponibles para esta versión.</p>}
      {previsiones && control.length > 0 && (
        <section aria-labelledby="modelos-evaluacion">
          <div className="modelos-controles">
            <h3 id="modelos-evaluacion">Evaluaciones <span>({control.length})</span></h3>
            <label className="buscador modelos-buscador">
              <span className="sr-only">Buscar modelo</span>
              <input type="search" placeholder="Buscar modelo" value={busqueda}
                onChange={(evento) => setBusqueda(evento.target.value)} />
            </label>
          </div>
          {filas.length === 0 ? <p role="status">Ningún modelo coincide con «{busqueda}».</p> : (
            <EvaluacionesModelos filas={filas} previsiones={previsiones} prediccion={prediccion} />
          )}
        </section>
      )}
      {previsiones && <EscenariosCalculados previsiones={previsiones} />}
    </section>
  );
}

