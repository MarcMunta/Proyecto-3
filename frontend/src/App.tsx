import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import metaJson from "./data/provincias.json";
import type { ProvinciaMeta } from "./data/types";
import { useDatos, usePrevisiones } from "./data/useDatos";
import { useDatosApis } from "./data/datosApis";
import { demanda as pedirDemanda, mix as pedirMix, precios as pedirPrecios } from "./live/redata";
import { tiempoCapitales } from "./live/openmeteo";
import { usePolling } from "./live/usePolling";
import { Ficha } from "./components/Ficha";
import { Franja } from "./components/Franja";
import { Ranking } from "./components/Ranking";
import { useMovimientoReducido } from "./components/useMovimientoReducido";

const MapaEspana = lazy(() => import("./components/MapaEspana").then((m) => ({ default: m.MapaEspana })));

const CatalogoModelos = lazy(() => import("./components/CatalogoModelos").then((m) => ({ default: m.CatalogoModelos })));
const CatalogoDatos = lazy(() => import("./components/CatalogoDatos").then((m) => ({ default: m.CatalogoDatos })));

const META = metaJson as ProvinciaMeta[];
const META_POR_CODIGO = new Map(META.map((m) => [m.codigo, m]));
const CINCO_MIN = 5 * 60_000;

interface Ruta {
  provincia: string | null;
  sitio: string | null;
  modelos?: boolean;
  datos?: boolean;
}

/** Enlace al mapa, a una zona o a los paneles laterales de modelos y de datos. */
function leerRuta(): Ruta {
  if (window.location.hash === "#/modelos") return { provincia: null, sitio: null, modelos: true };
  if (window.location.hash === "#/datos") return { provincia: null, sitio: null, datos: true };
  const m = window.location.hash.match(/^#\/provincia\/(\d{2})(?:\/(\d{5}))?(\/modelos|\/datos)?$/);
  if (!m || !META_POR_CODIGO.has(m[1]!)) return { provincia: null, sitio: null };
  return { provincia: m[1]!, sitio: m[2] ?? null, modelos: m[3] === "/modelos", datos: m[3] === "/datos" };
}

function hashRuta({ provincia, sitio, modelos, datos }: Ruta): string {
  const panel = datos ? "datos" : modelos ? "modelos" : "";
  if (!provincia) return panel ? `#/${panel}` : "#/";
  return `#/provincia/${provincia}${sitio ? `/${sitio}` : ""}${panel ? `/${panel}` : ""}`;
}

function useRuta(): [Ruta, (r: Ruta) => void] {
  const [ruta, setRuta] = useState<Ruta>(leerRuta);
  useEffect(() => {
    const alCambiar = () => setRuta(leerRuta());
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  const ir = useCallback((r: Ruta) => {
    const hash = hashRuta(r);
    if (window.location.hash !== hash) window.location.hash = hash;
    setRuta(r);
  }, []);
  return [ruta, ir];
}

export function App() {
  const { datos, error } = useDatos();
  const reducir = useMovimientoReducido();
  const [ruta, ir] = useRuta();
  const fichaAbierta = Boolean(ruta.provincia) && !ruta.modelos && !ruta.datos;
  const previsiones = usePrevisiones(datos?.publicacion, fichaAbierta || ruta.modelos === true);
  const panelDatos = useDatosApis(datos?.publicacion, ruta.datos === true);
  const [resaltado, setResaltado] = useState<string | null>(null);
  const panel = useRef<HTMLElement>(null);

  const precios = usePolling(pedirPrecios, CINCO_MIN);
  const demanda = usePolling(pedirDemanda, CINCO_MIN, fichaAbierta);
  const mix = usePolling(pedirMix, 30 * 60_000, fichaAbierta);
  const tiempo = usePolling(useCallback((s: AbortSignal) => tiempoCapitales(META, s), []), 10 * 60_000, fichaAbierta);

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
      if (e.key !== "Escape" || e.defaultPrevented || (e.target instanceof HTMLInputElement && e.target.type === "search")) return;
      if (ruta.modelos || ruta.datos) ir({ provincia: ruta.provincia, sitio: ruta.sitio });
      else if (ruta.provincia) elegirProvincia(null);
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [ruta.provincia, ruta.sitio, ruta.modelos, ruta.datos, elegirProvincia, ir]);

  useEffect(() => {
    panel.current?.scrollTo({ top: 0, behavior: "instant" });
    if (datos && (ruta.provincia || ruta.modelos || ruta.datos) && window.matchMedia("(max-width: 900px)").matches) {
      panel.current?.scrollIntoView({ block: "start", behavior: reducir ? "auto" : "smooth" });
    }
    setResaltado(null);
  }, [ruta.provincia, ruta.modelos, ruta.datos, datos, reducir]);

  const meta = ruta.provincia ? META_POR_CODIGO.get(ruta.provincia) : undefined;

  const enlaceDetalle = hashRuta({ ...ruta, modelos: false, datos: false });
  const enlaceModelos = hashRuta({ ...ruta, modelos: true, datos: false });
  const enlaceDatos = hashRuta({ ...ruta, modelos: false, datos: true });
  const enPanel = ruta.modelos || ruta.datos;
  const enlaces = [
    ...(enPanel ? [{ href: enlaceDetalle, etiqueta: meta ? "Ficha de zona" : "Provincias" }] : []),
    ...(ruta.modelos ? [] : [{ href: enlaceModelos, etiqueta: "Modelos" }]),
    ...(ruta.datos ? [] : [{ href: enlaceDatos, etiqueta: "Datos" }]),
  ];

  return (
    <div className="app">
      <Franja precios={precios} demo={demo} publicacion={datos?.publicacion ?? null} enlaces={enlaces} />
      <main className="escena">
        {datos ? (
          <Suspense fallback={<div className="mapa-marco mapa-espera"><p>Cargando mapa…</p></div>}>
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
          </Suspense>
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
          {ruta.datos ? (
            <Suspense fallback={<p role="status">Cargando datos…</p>}>
              <CatalogoDatos datos={panelDatos.datos} cargando={!error && panelDatos.estado === "cargando"}
                zona={meta?.nombre} volver={enlaceDetalle} />
            </Suspense>
          ) : ruta.modelos ? (
            <Suspense fallback={<p role="status">Cargando modelos…</p>}>
              <CatalogoModelos previsiones={previsiones.datos} prediccion={datos?.prediccion}
                cargando={!error && previsiones.estado === "cargando"} zona={meta?.nombre} volver={enlaceDetalle} />
            </Suspense>
          ) : datos && meta ? (
            <Ficha
              key={meta.codigo}
              meta={meta}
              geoProps={datos.geo.features.find((f) => f.properties.codigo === meta.codigo)?.properties}
              prediccion={datos.prediccion}
              previsiones={previsiones.datos}
              estadoPrevisiones={previsiones.estado}
              enlaceModelos={enlaceModelos}
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
