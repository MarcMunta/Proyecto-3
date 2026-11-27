import type { Precios } from "../live/redata";
import type { EnVivo } from "../live/usePolling";
import { punteroObsoleto } from "../data/publicacion";
import type { EstadoPublicacion } from "../data/useDatos";
import { num } from "../format";
import { Flap } from "./Flap";
import { Vivo } from "./Piezas";

/** Cabecera mínima: título, precio de la luz en directo y, solo con datos de demostración, su sello. */
export function Franja({ precios, demo, publicacion, enlace, etiquetaEnlace }: {
  precios: EnVivo<Precios>; demo: boolean; publicacion: EstadoPublicacion | null; enlace: string; etiquetaEnlace: string;
}) {
  const ahora = precios.datos?.spotAhora;
  return (
    <header className="cabecera">
      <div className="marca">
        <span className="marca-sigla" aria-hidden="true">
          CPD
        </span>
        <h1>¿Dónde construir un centro de datos en España?</h1>
      </div>
      <nav aria-label="Secciones" className="cabecera-nav">
        <a href={enlace}>{etiquetaEnlace}</a>
      </nav>
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
      {publicacion?.tipo === "versionada" && (
        <div className="sello sello-publicacion">
          <span>Datos del panel {publicacion.puntero.fecha_panel ?? "sin fecha"}</span>
          {punteroObsoleto(publicacion.puntero) && <p role="status">Publicación de más de siete días.</p>}
          {publicacion.puntero.avisos?.map((aviso) => <p role="status" key={aviso}>{aviso.replace("demanda_ccaa_mwh", "la demanda eléctrica por comunidad")}</p>)}
        </div>
      )}
      {publicacion?.tipo === "respaldo" && (
        <p className="sello sello-aviso" role="status" title={publicacion.motivo}>
          Datos de respaldo
        </p>
      )}
    </header>
  );
}
