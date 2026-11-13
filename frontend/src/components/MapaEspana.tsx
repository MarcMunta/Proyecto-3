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
import { useEffect, useMemo, useRef, useState } from "react";
import type { Agregado, EstadoMapa, GeoContexto, GeoProvincias, Viabilidad } from "../data/types";
import { nombreMunicipio, num } from "../format";
import { C, COLOR_ESTADO, ETIQUETA_ESTADO, colorScore } from "../model/colores";
import { CanariasRecuadro } from "./CanariasRecuadro";
import { Leyenda } from "./Leyenda";
import { Flecha } from "./Piezas";
import { scoreProvincia } from "../data/agregar";

// Vite reempaqueta MapLibre y rompe la ruta de su web worker (y en desarrollo le inyecta su cliente).
// Se carga el worker original, sin transformar, desde un Blob.
maplibregl.setWorkerUrl(URL.createObjectURL(new Blob([fuenteTrabajador], { type: "text/javascript" })));

// Algo de océano al oeste y al sur para que el recuadro de Canarias no tape Huelva ni Cádiz.
const ESPANA: LngLatBoundsLike = [-10.6, 34.45, 4.45, 43.85];
const VACIO: FeatureCollection = { type: "FeatureCollection", features: [] };
const BASE = import.meta.env.BASE_URL;

interface Props {
  geo: GeoProvincias;
  contexto: GeoContexto | null;
  datos: Viabilidad;
  agregado: Agregado;
  onAgregado: (a: Agregado) => void;
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
  estado: EstadoMapa | null;
}

/**
 * Imagen de rayado diagonal para "sin datos todavía" (a 2x). Las provincias usan un rayado marcado;
 * los municipios, uno más fino y tenue para que sigan leyéndose sus límites.
 */
function rayado(periodo = 8, grosor = 2, alfa = 255) {
  const n = 16;
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const i = (y * n + x) * 4;
      const enLinea = (x + y) % periodo < grosor;
      data[i] = 0x56;
      data[i + 1] = 0x59;
      data[i + 2] = 0x5f;
      data[i + 3] = enLinea ? alfa : 0;
    }
  }
  return { width: n, height: n, data };
}

const svgLampara = (estado: EstadoMapa) => {
  const c = COLOR_ESTADO[estado];
  const forma =
    estado === "Viable"
      ? `<circle cx="8" cy="8" r="6.5" fill="${c}"/>`
      : estado === "Viable con condiciones"
        ? `<path d="M8 1.2 15.2 14.4H.8Z" fill="${c}"/>`
        : estado === "No viable"
          ? `<path d="M2.5 2.5 13.5 13.5M13.5 2.5 2.5 13.5" stroke="${c}" stroke-width="3.4" stroke-linecap="square"/>`
          : `<circle cx="8" cy="8" r="5.6" fill="none" stroke="${c}" stroke-width="1.8"/>`;
  return `<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">${forma}</svg>`;
};

export function MapaEspana(props: Props) {
  const { geo, contexto, datos, agregado, seleccion, sitio, resaltado, reducirMovimiento } = props;
  const contenedor = useRef<HTMLDivElement>(null);
  const mapaRef = useRef<MapaML | null>(null);
  const [listo, setListo] = useState(false);
  const [pista, setPista] = useState<Pista | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;
  const marcadoresSitio = useRef(new Map<string, { m: maplibregl.Marker; el: HTMLButtonElement }>());
  const cacheMunicipios = useRef(new Map<string, FeatureCollection>());
  const hoverRef = useRef<{ fuente: string; id: string | number } | null>(null);

  const porIne = useMemo(() => new Map(datos.municipios.map((m) => [m.codigo_ine, m])), [datos]);
  const porIneRef = useRef(porIne);
  porIneRef.current = porIne;

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
      minZoom: 3.6,
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
      mapa.addImage("rayado-fino", rayado(16, 1, 150), { pixelRatio: 2 });
      mapa.addSource("contexto", { type: "geojson", data: (propsRef.current.contexto ?? VACIO) as FeatureCollection });
      mapa.addSource("provincias", { type: "geojson", data: propsRef.current.geo, promoteId: "codigo" });
      mapa.addSource("municipios", { type: "geojson", data: VACIO, promoteId: "ine" });

      mapa.addLayer({ id: "contexto", type: "fill", source: "contexto", paint: { "fill-color": C.contexto } });
      mapa.addLayer({ id: "prov-fill", type: "fill", source: "provincias", paint: { "fill-color": C.modulo } });
      mapa.addLayer({ id: "prov-rayado", type: "fill", source: "provincias", paint: { "fill-pattern": "rayado" }, filter: ["==", "x", "y"] });
      mapa.addLayer({ id: "mun-fill", type: "fill", source: "municipios", paint: { "fill-color": C.modulo } });
      // Municipios sin análisis: mismo rayado que las provincias sin datos ("rayado = sin datos").
      mapa.addLayer({
        id: "mun-rayado",
        type: "fill",
        source: "municipios",
        paint: { "fill-pattern": "rayado-fino" },
        filter: ["!", ["in", ["get", "ine"], ["literal", propsRef.current.datos.municipios.map((m) => m.codigo_ine)]]],
      });
      mapa.addLayer({
        id: "mun-linea",
        type: "line",
        source: "municipios",
        paint: { "line-color": "#6a6e76", "line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.6, 10, 1.4] },
      });
      mapa.addLayer({
        id: "mun-hover",
        type: "line",
        source: "municipios",
        paint: {
          "line-color": C.caracter,
          "line-width": 1.6,
          "line-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1, 0],
        },
      });
      mapa.addLayer({
        id: "prov-linea",
        type: "line",
        source: "provincias",
        paint: { "line-color": C.junta, "line-width": ["interpolate", ["linear"], ["zoom"], 4, 1, 8, 2.2] },
      });
      mapa.addLayer({
        id: "prov-hover",
        type: "line",
        source: "provincias",
        paint: {
          "line-color": C.caracter,
          "line-width": 1.8,
          "line-opacity": [
            "case",
            ["any", ["boolean", ["feature-state", "hover"], false], ["boolean", ["feature-state", "resaltado"], false]],
            1,
            0,
          ],
        },
      });
      mapa.addLayer({
        id: "prov-sel",
        type: "line",
        source: "provincias",
        paint: { "line-color": C.amarillo, "line-width": 2.6 },
        filter: ["==", ["get", "codigo"], ""],
      });

      // Etiquetas de código INE de provincia: el mismo código que en el tablero.
      for (const f of propsRef.current.geo.features) {
        if (!f.properties.etiqueta) continue;
        const el = document.createElement("div");
        el.className = "tag-prov";
        el.textContent = f.properties.codigo;
        el.setAttribute("aria-hidden", "true");
        const [lon, lat] = f.properties.etiqueta;
        // Si una lámpara cae justo encima, la etiqueta baja un poco para no taparse.
        const choca = propsRef.current.datos.municipios.some(
          (m) => m.lon != null && m.lat != null && Math.hypot(m.lon - lon, m.lat - lat) < 0.32,
        );
        new maplibregl.Marker({ element: el, offset: choca ? [0, 17] : [0, 0] }).setLngLat([lon, lat]).addTo(mapa);
      }

      // Lámparas de los municipios analizados por el modelo.
      for (const m of propsRef.current.datos.municipios) {
        if (m.lat == null || m.lon == null) continue;
        const el = document.createElement("button");
        el.type = "button";
        el.className = "sitio";
        el.dataset.provincia = m.provincia_codigo;
        el.setAttribute("aria-label", `${m.municipio}: ${m.estado}, score ${num(m.score_global, 1)}`);
        el.innerHTML = svgLampara(m.estado); // SVG fijo generado aquí, sin datos externos
        const nombre = document.createElement("span");
        nombre.className = "sitio-nombre";
        nombre.textContent = m.municipio;
        el.append(nombre);
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          propsRef.current.onSitio(m.codigo_ine);
        });
        const marcador = new maplibregl.Marker({ element: el, anchor: "left", offset: [-8, 0] }).setLngLat([m.lon, m.lat]).addTo(mapa);
        marcadoresSitio.current.set(m.codigo_ine, { m: marcador, el });
      }

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
        const ine = String(mun.properties.ine);
        const analizado = porIneRef.current.get(ine);
        setPista({
          x: e.point.x,
          y: e.point.y,
          titulo: nombreMunicipio(String(mun.properties.nombre)),
          linea: analizado
            ? `${ETIQUETA_ESTADO[analizado.estado]} · SCORE ${num(analizado.score_global, 1)}`
            : `${num(Number(mun.properties.area_km2), 1)} km² · sin analizar`,
          estado: analizado ? analizado.estado : null,
        });
        return;
      }
      if (prov) {
        ponerHover("provincias", prov.id);
        const codigo = String(prov.properties.codigo);
        const r = p.datos.provincias[codigo];
        const s = scoreProvincia(r, p.agregado, porIneRef.current);
        setPista({
          x: e.point.x,
          y: e.point.y,
          titulo: `${codigo} · ${String(prov.properties.nombre)}`,
          linea: r ? `${ETIQUETA_ESTADO[r.estado]} · SCORE ${num(s, 1)}` : "SIN DATOS TODAVÍA",
          estado: r ? r.estado : "Sin datos",
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
      const mun = mapa.queryRenderedFeatures(e.point, { layers: ["mun-fill"] })[0];
      if (mun && p.seleccion && mun.properties.prov === p.seleccion) {
        const ine = String(mun.properties.ine);
        if (porIneRef.current.has(ine)) {
          p.onSitio(ine);
          return;
        }
      }
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

    const ro = new ResizeObserver(() => mapa.resize());
    ro.observe(contenedor.current);
    return () => {
      ro.disconnect();
      mapa.remove();
      mapaRef.current = null;
      marcadoresSitio.current.clear();
    };
  }, []);

  // ---------- Color de provincias según score (mejor emplazamiento o media) ----------
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!listo || !mapa) return;
    const pares: string[] = [];
    const conDatos: string[] = [];
    for (const f of geo.features) {
      const r = datos.provincias[f.properties.codigo];
      if (!r) continue;
      conDatos.push(f.properties.codigo);
      pares.push(f.properties.codigo, colorScore(scoreProvincia(r, agregado, porIne)));
    }
    const color = (pares.length ? ["match", ["get", "codigo"], ...pares, C.modulo] : C.modulo) as unknown as ExpressionSpecification;
    mapa.setPaintProperty("prov-fill", "fill-color", color);
    mapa.setFilter("prov-rayado", ["!", ["in", ["get", "codigo"], ["literal", conDatos]]]);
    const opacidad = (seleccion
      ? ["case", ["==", ["get", "codigo"], seleccion], 1, 0.2]
      : 1) as ExpressionSpecification;
    mapa.setPaintProperty("prov-fill", "fill-opacity", opacidad);
    mapa.setPaintProperty("prov-rayado", "fill-opacity", opacidad);

    // Municipios analizados: misma rampa; el resto, módulo apagado.
    const paresMun: string[] = [];
    for (const m of datos.municipios) paresMun.push(m.codigo_ine, colorScore(m.score_global));
    mapa.setPaintProperty("mun-fill", "fill-color", [
      "case",
      ["boolean", ["feature-state", "hover"], false],
      "#2b2e33",
      (paresMun.length ? ["match", ["get", "ine"], ...paresMun, C.modulo] : C.modulo) as unknown as ExpressionSpecification,
    ] as ExpressionSpecification);
  }, [listo, geo, datos, agregado, porIne, seleccion]);

  // ---------- Resaltado desde el tablero ----------
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
    for (const { el } of marcadoresSitio.current.values()) {
      const visible = !seleccion || el.dataset.provincia === seleccion;
      el.classList.toggle("oculto", !visible);
      el.tabIndex = seleccion && visible ? 0 : -1;
    }
    const ancho = contenedor.current?.clientWidth ?? 800;
    const margen = Math.max(24, Math.min(90, ancho * 0.07));
    const padding: PaddingOptions = { top: margen, bottom: margen, left: margen, right: margen };
    const duracion = reducirMovimiento ? 0 : 1700;
    const fuente = mapa.getSource("municipios") as GeoJSONSource | undefined;

    if (!seleccion) {
      fuente?.setData(VACIO);
      mapa.fitBounds(ESPANA, { padding: Math.min(32, margen), duration: duracion, essential: true });
      return;
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
    };
  }, [listo, seleccion, geo, reducirMovimiento]);

  // ---------- Sitio activo ----------
  useEffect(() => {
    for (const [ine, { el }] of marcadoresSitio.current) el.classList.toggle("activo", ine === sitio);
  }, [sitio, listo]);

  // ---------- Contexto (Portugal/Francia) cuando llega ----------
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
        aria-label="Mapa de España por provincias. Para elegir con el teclado usa la lista del tablero."
      />
      {pista && (
        <div className="pista" style={{ transform: `translate(${pista.x + 14}px, ${pista.y + 14}px)` }} aria-hidden="true">
          <span className="pista-titulo">{pista.titulo}</span>
          <span className="pista-linea">
            {pista.estado && <i className="pista-punto" style={{ background: COLOR_ESTADO[pista.estado] }} />}
            {pista.linea}
          </span>
        </div>
      )}
      {!seleccion && (
        <CanariasRecuadro geo={geo} datos={datos} agregado={agregado} porIne={porIne} onProvincia={props.onProvincia} />
      )}
      {seleccion && !enCanarias && (
        <button type="button" className="mapa-volver" onClick={() => props.onProvincia(null)}>
          <Flecha /> Toda España
        </button>
      )}
      {enCanarias && (
        <button type="button" className="mapa-volver" onClick={() => props.onProvincia(null)}>
          <Flecha /> Volver a la península
        </button>
      )}
      <Leyenda agregado={agregado} onAgregado={props.onAgregado} />
    </div>
  );
}
