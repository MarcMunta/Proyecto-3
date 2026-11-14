import type { Precios } from "../live/redata";
import type { EnVivo } from "../live/usePolling";
import { num } from "../format";
import { Flap } from "./Flap";
import { Vivo } from "./Piezas";

/** Cabecera mínima: título, precio de la luz en directo y, solo con datos de demostración, su sello. */
export function Franja({ precios, demo }: { precios: EnVivo<Precios>; demo: boolean }) {
  const ahora = precios.datos?.spotAhora;
  return (
    <header className="cabecera">
      <div className="marca">
        <span className="marca-sigla" aria-hidden="true">
          CPD
        </span>
        <h1>¿Dónde construir un centro de datos en España?</h1>
      </div>
      <div className="cabecera-luz" aria-label="Precio de la luz en directo (mercado nacional)">
        <span className="cabecera-et">Luz nacional ahora</span>
        {ahora ? (
          <>
            <Flap texto={num(ahora.v, 1)} />
            <span className="unidad">€/MWh</span>
            <Vivo momento={ahora.t} />
          </>
        ) : precios.error ? (
          <span className="sin-conexion">sin conexión</span>
        ) : (
          <span className="unidad">cargando…</span>
        )}
      </div>
      {demo && (
        <p className="sello" title="Los indicadores municipales son sintéticos; los límites, la luz y el tiempo son reales.">
          Datos de demostración
        </p>
      )}
    </header>
  );
}
