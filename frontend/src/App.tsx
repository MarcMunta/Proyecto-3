import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import metaJson from "./data/provincias.json";
import type { Agregado, ProvinciaMeta } from "./data/types";
import { useDatos } from "./data/useDatos";
import { demanda as pedirDemanda, mix as pedirMix, precios as pedirPrecios } from "./live/redata";
import { tiempoCapitales } from "./live/openmeteo";
import { usePolling } from "./live/usePolling";
import { diaHora } from "./format";
import { Ficha } from "./components/Ficha";
import { Franja } from "./components/Franja";
import { MapaEspana } from "./components/MapaEspana";
import { Tablero } from "./components/Tablero";
import { useMovimientoReducido } from "./components/useMovimientoReducido";

const META = metaJson as ProvinciaMeta[];
const META_POR_CODIGO = new Map(META.map((m) => [m.codigo, m]));
const CINCO_MIN = 5 * 60_000;

interface Ruta {
  provincia: string | null;
  sitio: string | null;
}

/** #/provincia/28 o #/provincia/28/28079 (enlace directo a una provincia o emplazamiento). */
function leerRuta(): Ruta {
  const m = window.location.hash.match(/^#\/provincia\/(\d{2})(?:\/(\d{5}))?$/);
  if (!m || !META_POR_CODIGO.has(m[1]!)) return { provincia: null, sitio: null };
  return { provincia: m[1]!, sitio: m[2] ?? null };
}

function useRuta(): [Ruta, (r: Ruta) => void] {
  const [ruta, setRuta] = useState<Ruta>(leerRuta);
  useEffect(() => {
    const alCambiar = () => setRuta(leerRuta());
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  const ir = useCallback((r: Ruta) => {
    const hash = r.provincia ? `#/provincia/${r.provincia}${r.sitio ? `/${r.sitio}` : ""}` : "#/";
    if (window.location.hash !== hash) window.location.hash = hash;
    setRuta(r);
  }, []);
  return [ruta, ir];
}

export function App() {
  const { datos, error } = useDatos();
  const reducir = useMovimientoReducido();
  const [ruta, ir] = useRuta();
  const [agregado, setAgregado] = useState<Agregado>("mejor");
  const [resaltado, setResaltado] = useState<string | null>(null);
  const tablero = useRef<HTMLElement>(null);

  const precios = usePolling(pedirPrecios, CINCO_MIN);
  const demanda = usePolling(pedirDemanda, CINCO_MIN);
  const mix = usePolling(pedirMix, 30 * 60_000);
  const tiempo = usePolling(useCallback((s: AbortSignal) => tiempoCapitales(META, s), []), 10 * 60_000);

  const porIne = useMemo(() => new Map((datos?.viabilidad.municipios ?? []).map((m) => [m.codigo_ine, m])), [datos]);

  const elegirProvincia = useCallback((codigo: string | null) => ir({ provincia: codigo, sitio: null }), [ir]);
  const elegirSitio = useCallback(
    (ine: string) => {
      const m = porIne.get(ine);
      if (m) ir({ provincia: m.provincia_codigo, sitio: ine });
    },
    [ir, porIne],
  );

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape" && ruta.provincia) elegirProvincia(null);
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [ruta.provincia, elegirProvincia]);

  useEffect(() => {
    tablero.current?.scrollTo({ top: 0, behavior: reducir ? "auto" : "smooth" });
    setResaltado(null);
  }, [ruta.provincia, reducir]);

  const meta = ruta.provincia ? META_POR_CODIGO.get(ruta.provincia) : undefined;

  return (
    <div className="app">
      <Franja precios={precios} demanda={demanda} mix={mix} sintetico={datos?.viabilidad.fuente.sintetico ?? true} />
      <main className="escena">
        {datos ? (
          <MapaEspana
            geo={datos.geo}
            contexto={datos.contexto}
            datos={datos.viabilidad}
            agregado={agregado}
            onAgregado={setAgregado}
            seleccion={ruta.provincia}
            sitio={ruta.sitio}
            resaltado={resaltado}
            reducirMovimiento={reducir}
            onProvincia={elegirProvincia}
            onSitio={elegirSitio}
          />
        ) : (
          <div className="mapa-marco mapa-espera">{error ? null : <p>Cargando mapa…</p>}</div>
        )}
        <aside className="tablero" ref={tablero} aria-label="Tablero de viabilidad">
          {error && (
            <div className="error-carga" role="alert">
              <h2>No se han podido cargar los datos del mapa</h2>
              <p>{error}</p>
              <p>
                Genera los ficheros con <code>npm run data</code> (modelo) y <code>npm run geo</code> (límites) dentro de{" "}
                <code>frontend/</code> y recarga la página.
              </p>
            </div>
          )}
          {datos && meta ? (
            <Ficha
              key={meta.codigo}
              meta={meta}
              geoProps={datos.geo.features.find((f) => f.properties.codigo === meta.codigo)?.properties}
              datos={datos.viabilidad}
              resumen={datos.viabilidad.provincias[meta.codigo]}
              porIne={porIne}
              sitio={ruta.sitio}
              onSitio={elegirSitio}
              onVolver={() => elegirProvincia(null)}
              precios={precios}
              demanda={demanda}
              mix={mix}
              tiempo={tiempo}
            />
          ) : datos ? (
            <Tablero
              meta={META}
              datos={datos.viabilidad}
              agregado={agregado}
              porIne={porIne}
              onProvincia={elegirProvincia}
              onResaltar={setResaltado}
            />
          ) : null}
          {datos && (
            <footer className="creditos">
              <p>
                <strong>Modelo:</strong> embudo de viabilidad del proyecto (<code>src/cpd</code>) sobre{" "}
                <code>{datos.viabilidad.fuente.fichero}</code>
                {datos.viabilidad.fuente.sintetico && <> — {datos.viabilidad.fuente.nota}</>} Generado el{" "}
                {diaHora(Date.parse(datos.viabilidad.generado))}.
              </p>
              <p>
                <strong>Límites:</strong> © EuroGeographics, Eurostat GISCO LAU 2024. <strong>En directo:</strong> REData de
                Red Eléctrica (precio, demanda, mix; datos nacionales) y Open-Meteo (tiempo en las capitales).
              </p>
            </footer>
          )}
        </aside>
      </main>
    </div>
  );
}
