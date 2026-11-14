import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import metaJson from "./data/provincias.json";
import type { ProvinciaMeta } from "./data/types";
import { useDatos } from "./data/useDatos";
import { demanda as pedirDemanda, mix as pedirMix, precios as pedirPrecios } from "./live/redata";
import { tiempoCapitales } from "./live/openmeteo";
import { usePolling } from "./live/usePolling";
import { Ficha } from "./components/Ficha";
import { Franja } from "./components/Franja";
import { MapaEspana } from "./components/MapaEspana";
import { Ranking } from "./components/Ranking";
import { useMovimientoReducido } from "./components/useMovimientoReducido";

const META = metaJson as ProvinciaMeta[];
const META_POR_CODIGO = new Map(META.map((m) => [m.codigo, m]));
const CINCO_MIN = 5 * 60_000;

interface Ruta {
  provincia: string | null;
  sitio: string | null;
}

/** #/provincia/28 o #/provincia/28/28079 (enlace directo a una provincia o municipio analizado). */
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
  const [resaltado, setResaltado] = useState<string | null>(null);
  const panel = useRef<HTMLElement>(null);

  const precios = usePolling(pedirPrecios, CINCO_MIN);
  const demanda = usePolling(pedirDemanda, CINCO_MIN);
  const mix = usePolling(pedirMix, 30 * 60_000);
  const tiempo = usePolling(useCallback((s: AbortSignal) => tiempoCapitales(META, s), []), 10 * 60_000);

  // El sello de demostración solo aparece cuando ya se sabe que no hay predicción real.
  const demo = datos ? datos.prediccion.tipo === "demo" : false;
  const sitios = useMemo(() => (datos && datos.prediccion.tipo === "demo" ? datos.viabilidad.municipios : []), [datos]);
  const porIne = useMemo(() => new Map(sitios.map((m) => [m.codigo_ine, m])), [sitios]);

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
    const comportamiento = reducir ? "auto" : "smooth";
    panel.current?.scrollTo({ top: 0, behavior: comportamiento });
    // En el móvil el mapa y el panel van apilados: al elegir una provincia, subir al mapa para ver el zoom.
    if (ruta.provincia && window.matchMedia("(max-width: 900px)").matches) {
      document.querySelector(".mapa-marco")?.scrollIntoView({ block: "start", behavior: comportamiento });
    }
    setResaltado(null);
  }, [ruta.provincia, reducir]);

  const meta = ruta.provincia ? META_POR_CODIGO.get(ruta.provincia) : undefined;

  return (
    <div className="app">
      <Franja precios={precios} demo={demo} />
      <main className="escena">
        {datos ? (
          <MapaEspana
            geo={datos.geo}
            contexto={datos.contexto}
            prediccion={datos.prediccion}
            sitios={sitios}
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
        <aside className="panel" ref={panel} aria-label="Detalle">
          {error && (
            <div className="error-carga" role="alert">
              <h2>No se han podido cargar los datos del mapa</h2>
              <p>{error}</p>
              <p>
                Genera los ficheros con <code>npm run data</code> y <code>npm run geo</code> dentro de <code>frontend/</code> y recarga.
              </p>
            </div>
          )}
          {datos && meta ? (
            <Ficha
              key={meta.codigo}
              meta={meta}
              geoProps={datos.geo.features.find((f) => f.properties.codigo === meta.codigo)?.properties}
              prediccion={datos.prediccion}
              viabilidad={datos.viabilidad}
              sitio={ruta.sitio}
              onSitio={elegirSitio}
              onVolver={() => elegirProvincia(null)}
              precios={precios}
              demanda={demanda}
              mix={mix}
              tiempo={tiempo}
            />
          ) : datos ? (
            <Ranking meta={META} prediccion={datos.prediccion} onProvincia={elegirProvincia} onResaltar={setResaltado} />
          ) : null}
          {datos && (
            <footer className="creditos">
              Límites © EuroGeographics, Eurostat GISCO LAU 2024 · Luz, demanda y mix: REData (Red Eléctrica) · Tiempo: Open-Meteo
            </footer>
          )}
        </aside>
      </main>
    </div>
  );
}
