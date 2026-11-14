import * as maplibregl from "maplibre-gl";
import type {
  ExpressionSpecification,
  GeoJSONSource,
  LngLatBoundsLike,
  Map as MapaML,
  MapLayerMouseEvent,
  PaddingOptions,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import fuenteTrabajador from "maplibre-gl/dist/maplibre-gl-worker.mjs?raw";
import type { FeatureCollection } from "geojson";
import { useEffect, useRef, useState } from "react";
import type { GeoContexto, GeoProvincias, Municipio } from "../data/types";
import type { ClaseRentabilidad, Prediccion } from "../data/prediccion";
import { millones, nombreMunicipio, num } from "../format";
import { C, COLOR_CLASE, NOMBRE_CLASE, colorClase } from "../model/colores";
import { CanariasRecuadro } from "./CanariasRecuadro";
import { IconoClase } from "./IconoClase";
import { Leyenda } from "./Leyenda";
import { Flecha } from "./Piezas";

// Vite reempaqueta MapLibre y rompe la ruta de su web worker (y en desarrollo le inyecta su cliente).
// Se carga el worker original, sin transformar, desde un Blob.
maplibregl.setWorkerUrl(URL.createObjectURL(new Blob([fuenteTrabajador], { type: "text/javascript" })));

// Algo de océano al oeste y al sur para que el recuadro de Canarias no tape Huelva ni Cádiz.
const ESPANA: LngLatBoundsLike = [-10.6, 34.45, 4.45, 43.85];

/**
 * Límites de la cámara: no se puede alejar más que el encuadre de España (o de Canarias cuando se está allí)
 * ni arrastrar el mapa fuera de la zona. Se recalculan al cambiar el tamaño del mapa.
 */
const LIMITES = {
  peninsula: { encuadre: ESPANA, max: [-14.5, 32.0, 8.5, 46.5] as LngLatBoundsLike },
  canarias: { encuadre: [-18.4, 27.5, -13.3, 29.5] as LngLatBoundsLike, max: [-21.0, 25.5, -10.5, 31.0] as LngLatBoundsLike },
};
type Zona = keyof typeof LIMITES;

function acotar(mapa: MapaML, zona: Zona) {
  const { encuadre, max } = LIMITES[zona];
  const camara = mapa.cameraForBounds(encuadre, { padding: 24 });
  if (camara?.zoom != null) mapa.setMinZoom(Math.max(1, camara.zoom - 0.25));
  mapa.setMaxBounds(max);
}

function soltar(mapa: MapaML) {
  mapa.setMaxBounds(null);
  mapa.setMinZoom(1);
}
const VACIO: FeatureCollection = { type: "FeatureCollection", features: [] };
const BASE = import.meta.env.BASE_URL;

interface Props {
  geo: GeoProvincias;
  contexto: GeoContexto | null;
  prediccion: Prediccion;
  /** Municipios analizados de la demostración (lista vacía con datos reales). */
  sitios: Municipio[];
  seleccion: string | null;
  sitio: string | null;
  resaltado: string | null;
  reducirMovimiento: boolean;
  onProvincia: (codigo: string | null) => void;
  onSitio: (ine: string) => void;
}

interface Pista {
  x: number;
  y: number;
  titulo: string;
  linea: string;
  clase: ClaseRentabilidad | null;
  icono: boolean;
}

/** Rayado diagonal para «sin datos todavía» (a 2x). */
function rayado() {
  const n = 16;
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const i = (y * n + x) * 4;
      data[i] = 0x4f;
      data[i + 1] = 0x52;
      data[i + 2] = 0x5a;
      data[i + 3] = (x + y) % 10 < 2 ? 255 : 0;
    }
  }
  return { width: n, height: n, data };
}

export function MapaEspana(props: Props) {
  const { geo, contexto, prediccion, sitios, seleccion, sitio, resaltado, reducirMovimiento } = props;
  const contenedor = useRef<HTMLDivElement>(null);
  const mapaRef = useRef<MapaML | null>(null);
  const [listo, setListo] = useState(false);
  const [pista, setPista] = useState<Pista | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const marcadores = useRef(new Map<string, { m: maplibregl.Marker; el: HTMLButtonElement }>());
  const cacheMunicipios = useRef(new Map<string, FeatureCollection>());
  const hoverRef = useRef<{ fuente: string; id: string | number } | null>(null);
  const zonaRef = useRef<Zona>("peninsula");

  // ---------- Creación del mapa (una vez) ----------
  useEffect(() => {
    if (!contenedor.current) return;
    const mapa = new maplibregl.Map({
      container: contenedor.current,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: "fondo", type: "background", paint: { "background-color": C.suelo } }],
      },
      bounds: ESPANA,
      fitBoundsOptions: { padding: 24 },
      minZoom: 1,
      maxZoom: 11.5,
      dragRotate: false,
      pitchWithRotate: false,
      renderWorldCopies: false,
      attributionControl: { compact: true, customAttribution: "Límites © EuroGeographics · Eurostat GISCO LAU 2024" },
      locale: {
        "NavigationControl.ZoomIn": "Acercar",
        "NavigationControl.ZoomOut": "Alejar",
        "AttributionControl.ToggleAttribution": "Créditos del mapa",
      },
    });
    mapa.touchZoomRotate.disableRotation();
    mapa.keyboard.disableRotation();
    mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapaRef.current = mapa;
    if (import.meta.env.DEV) (window as unknown as { __mapa: MapaML }).__mapa = mapa;
    mapa.on("error", (e) => console.error("MapLibre:", e.error?.message ?? e));

    mapa.on("load", () => {
      mapa.addImage("rayado", rayado(), { pixelRatio: 2 });
      mapa.addSource("contexto", { type: "geojson", data: (propsRef.current.contexto ?? VACIO) as FeatureCollection });
      mapa.addSource("provincias", { type: "geojson", data: propsRef.current.geo, promoteId: "codigo" });
      mapa.addSource("municipios", { type: "geojson", data: VACIO, promoteId: "ine" });

      mapa.addLayer({ id: "contexto", type: "fill", source: "contexto", paint: { "fill-color": C.contexto } });
      mapa.addLayer({ id: "prov-fill", type: "fill", source: "provincias", paint: { "fill-color": C.sinDatos } });
      mapa.addLayer({ id: "prov-rayado", type: "fill", source: "provincias", paint: { "fill-pattern": "rayado" }, filter: ["==", "x", "y"] });
      mapa.addLayer({
        id: "mun-fill",
        type: "fill",
        source: "municipios",
        paint: {
          "fill-color": "#ffffff",
          "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.14, 0],
        },
      });
      mapa.addLayer({
        id: "mun-linea",
        type: "line",
        source: "municipios",
        paint: {
          "line-color": "rgba(17, 18, 20, 0.55)",
          "line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.5, 10, 1.2],
        },
      });
      mapa.addLayer({
        id: "prov-linea",
        type: "line",
        source: "provincias",
        paint: { "line-color": C.suelo, "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.8, 8, 2] },
      });
      mapa.addLayer({
        id: "prov-hover",
        type: "line",
        source: "provincias",
        paint: {
          "line-color": C.texto,
          "line-width": 1.5,
          "line-opacity": [
            "case",
            ["any", ["boolean", ["feature-state", "hover"], false], ["boolean", ["feature-state", "resaltado"], false]],
            0.9,
            0,
          ],
        },
      });
      mapa.addLayer({
        id: "prov-sel",
        type: "line",
        source: "provincias",
        paint: { "line-color": C.texto, "line-width": 2.4 },
        filter: ["==", ["get", "codigo"], ""],
      });
      setListo(true);
    });

    const ponerHover = (fuente: string, id: string | number | undefined) => {
      const previo = hoverRef.current;
      if (previo && (previo.fuente !== fuente || previo.id !== id)) {
        mapa.setFeatureState({ source: previo.fuente, id: previo.id }, { hover: false });
        hoverRef.current = null;
      }
      if (id != null) {
        mapa.setFeatureState({ source: fuente, id }, { hover: true });
        hoverRef.current = { fuente, id };
      }
    };

    const alMover = (e: MapLayerMouseEvent) => {
      const p = propsRef.current;
      const mun = mapa.queryRenderedFeatures(e.point, { layers: ["mun-fill"] })[0];
      const prov = mapa.queryRenderedFeatures(e.point, { layers: ["prov-fill"] })[0];
      mapa.getCanvas().style.cursor = prov ? "pointer" : "";
      if (mun && p.seleccion && mun.properties.prov === p.seleccion) {
        ponerHover("municipios", mun.id);
        setPista({
          x: e.point.x,
          y: e.point.y,
          titulo: nombreMunicipio(String(mun.properties.nombre)),
          linea: `${num(Number(mun.properties.area_km2), 1)} km²`,
          clase: null,
          icono: false,
        });
        return;
      }
      if (prov) {
        ponerHover("provincias", prov.id);
        const codigo = String(prov.properties.codigo);
        const d = p.prediccion.provincias.get(codigo);
        setPista({
          x: e.point.x,
          y: e.point.y,
          titulo: String(prov.properties.nombre),
          linea: d?.clase
            ? `Rentabilidad ${NOMBRE_CLASE[d.clase].toLowerCase()}${d.van_eur != null ? ` · VAN ${millones(d.van_eur)}` : ""}`
            : "Sin datos todavía",
          clase: d?.clase ?? null,
          icono: true,
        });
        return;
      }
      ponerHover("provincias", undefined);
      setPista(null);
    };
    const alSalir = () => {
      ponerHover("provincias", undefined);
      setPista(null);
      mapa.getCanvas().style.cursor = "";
    };
    const alPulsar = (e: MapLayerMouseEvent) => {
      const p = propsRef.current;
      const prov = mapa.queryRenderedFeatures(e.point, { layers: ["prov-fill"] })[0];
      if (prov) {
        const codigo = String(prov.properties.codigo);
        if (codigo !== p.seleccion) p.onProvincia(codigo);
      } else if (p.seleccion) {
        p.onProvincia(null);
      }
    };
    mapa.on("mousemove", alMover);
    mapa.on("mouseout", alSalir);
    mapa.on("click", alPulsar);

    const ro = new ResizeObserver(() => {
      mapa.resize();
      if (mapa.loaded() && !mapa.isMoving()) acotar(mapa, zonaRef.current);
    });
    ro.observe(contenedor.current);
    return () => {
      ro.disconnect();
      mapa.remove();
      mapaRef.current = null;
      marcadores.current.clear();
    };
  }, []);

  // ---------- Color por clase de rentabilidad ----------
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!listo || !mapa) return;
    const pares: string[] = [];
    const conClase: string[] = [];
    for (const [codigo, d] of prediccion.provincias) {
      if (!d.clase) continue;
      conClase.push(codigo);
      pares.push(codigo, COLOR_CLASE[d.clase]);
    }
    const color = (pares.length ? ["match", ["get", "codigo"], ...pares, C.sinDatos] : C.sinDatos) as unknown as ExpressionSpecification;
    mapa.setPaintProperty("prov-fill", "fill-color", color);
    mapa.setFilter("prov-rayado", ["!", ["in", ["get", "codigo"], ["literal", conClase]]]);
    const opacidad = (seleccion ? ["case", ["==", ["get", "codigo"], seleccion], 1, 0.16] : 1) as ExpressionSpecification;
    mapa.setPaintProperty("prov-fill", "fill-opacity", opacidad);
    mapa.setPaintProperty("prov-rayado", "fill-opacity", opacidad);
  }, [listo, prediccion, seleccion]);

  // ---------- Puntos de los municipios analizados (solo en la demostración) ----------
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!listo || !mapa) return;
    for (const { m } of marcadores.current.values()) m.remove();
    marcadores.current.clear();
    for (const m of sitios) {
      if (m.lat == null || m.lon == null) continue;
      const clase = prediccion.clasesMunicipio.get(m.codigo_ine) ?? null;
      const el = document.createElement("button");
      el.type = "button";
      el.className = "sitio";
      el.dataset.provincia = m.provincia_codigo;
      el.setAttribute("aria-label", `${m.municipio}: rentabilidad ${clase ? NOMBRE_CLASE[clase].toLowerCase() : "sin datos"}`);
      const punto = document.createElement("span");
      punto.className = "sitio-punto";
      punto.style.background = colorClase(clase);
      const nombre = document.createElement("span");
      nombre.className = "sitio-nombre";
      nombre.textContent = m.municipio;
      el.append(punto, nombre);
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        propsRef.current.onSitio(m.codigo_ine);
      });
      const marcador = new maplibregl.Marker({ element: el, anchor: "left", offset: [-6, 0] }).setLngLat([m.lon, m.lat]).addTo(mapa);
      marcadores.current.set(m.codigo_ine, { m: marcador, el });
    }
  }, [listo, sitios, prediccion]);

  // ---------- Resaltado desde la lista ----------
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!listo || !mapa || !resaltado) return;
    mapa.setFeatureState({ source: "provincias", id: resaltado }, { resaltado: true });
    return () => {
      if (mapaRef.current?.getSource("provincias")) {
        mapaRef.current.setFeatureState({ source: "provincias", id: resaltado }, { resaltado: false });
      }
    };
  }, [listo, resaltado]);

  // ---------- Selección: vuelo de cámara y municipios de la provincia ----------
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!listo || !mapa) return;
    mapa.setFilter("prov-sel", ["==", ["get", "codigo"], seleccion ?? ""]);
    contenedor.current?.classList.toggle("en-provincia", Boolean(seleccion));
    for (const { el } of marcadores.current.values()) {
      const visible = !seleccion || el.dataset.provincia === seleccion;
      el.classList.toggle("oculto", !visible);
      el.tabIndex = seleccion && visible ? 0 : -1;
    }
    const ancho = contenedor.current?.clientWidth ?? 800;
    const margen = Math.max(24, Math.min(90, ancho * 0.07));
    const padding: PaddingOptions = { top: margen, bottom: margen, left: margen, right: margen };
    const duracion = reducirMovimiento ? 0 : 1600;
    const fuente = mapa.getSource("municipios") as GeoJSONSource | undefined;

    // Se sueltan los límites durante el vuelo (Canarias queda fuera de los de la península) y se vuelven a
    // poner al llegar, ya con la zona nueva.
    const zona: Zona = seleccion === "35" || seleccion === "38" ? "canarias" : "peninsula";
    zonaRef.current = zona;
    soltar(mapa);
    const alLlegar = () => acotar(mapa, zona);
    mapa.once("moveend", alLlegar);

    if (!seleccion) {
      fuente?.setData(VACIO);
      mapa.fitBounds(ESPANA, { padding: Math.min(32, margen), duration: duracion, essential: true });
      return () => {
        mapa.off("moveend", alLlegar);
      };
    }
    const f = geo.features.find((x) => x.properties.codigo === seleccion);
    if (f) mapa.fitBounds(f.properties.bbox, { padding, duration: duracion, essential: true, maxZoom: 9.5 });

    let cancelado = false;
    const enCache = cacheMunicipios.current.get(seleccion);
    if (enCache) fuente?.setData(enCache);
    else {
      fuente?.setData(VACIO);
      fetch(`${BASE}data/municipios/${seleccion}.geojson`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
        .then((gj: FeatureCollection) => {
          cacheMunicipios.current.set(seleccion, gj);
          if (!cancelado) fuente?.setData(gj);
        })
        .catch(() => {
          /* sin municipios: la provincia se ve igualmente */
        });
    }
    return () => {
      cancelado = true;
      mapa.off("moveend", alLlegar);
    };
  }, [listo, seleccion, geo, reducirMovimiento]);

  // ---------- Sitio activo ----------
  useEffect(() => {
    for (const [ine, { el }] of marcadores.current) el.classList.toggle("activo", ine === sitio);
  }, [sitio, listo, sitios]);

  // ---------- Contexto (Portugal/Francia) ----------
  useEffect(() => {
    const fuente = mapaRef.current?.getSource("contexto") as GeoJSONSource | undefined;
    if (listo && fuente && contexto) fuente.setData(contexto as FeatureCollection);
  }, [listo, contexto]);

  const enCanarias = seleccion === "35" || seleccion === "38";

  return (
    <div className="mapa-marco">
      <div
        ref={contenedor}
        className="mapa"
        role="region"
        aria-label="Mapa de España por provincias coloreado por rentabilidad. Para elegir con el teclado usa la lista."
      />
      {pista && (
        <div className="pista" style={{ transform: `translate(${pista.x + 14}px, ${pista.y + 14}px)` }} aria-hidden="true">
          <span className="pista-titulo">{pista.titulo}</span>
          <span className="pista-linea">
            {pista.icono && <IconoClase clase={pista.clase} tam={13} />}
            {pista.linea}
          </span>
        </div>
      )}
      {!seleccion && <CanariasRecuadro geo={geo} prediccion={prediccion} onProvincia={props.onProvincia} />}
      {seleccion && (
        <button type="button" className="mapa-volver" onClick={() => props.onProvincia(null)}>
          <Flecha /> {enCanarias ? "Volver a la península" : "Toda España"}
        </button>
      )}
      {!seleccion && <Leyenda prediccion={prediccion} />}
    </div>
  );
}
