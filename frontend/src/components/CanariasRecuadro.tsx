import type { Position } from "geojson";
import { useMemo } from "react";
import type { Agregado, GeoProvincias, Municipio, Viabilidad } from "../data/types";
import { scoreProvincia } from "../data/agregar";
import { C, colorScore } from "../model/colores";

interface Props {
  geo: GeoProvincias;
  datos: Viabilidad;
  agregado: Agregado;
  porIne: Map<string, Municipio>;
  onProvincia: (codigo: string) => void;
}

const ANCHO = 260;
const CODIGOS = ["35", "38"];

/** Recuadro de Canarias (como en los mapas oficiales). Pulsar una provincia vuela a su posición real. */
export function CanariasRecuadro({ geo, datos, agregado, porIne, onProvincia }: Props) {
  const dibujo = useMemo(() => {
    const feats = geo.features.filter((f) => CODIGOS.includes(f.properties.codigo));
    if (!feats.length) return null;
    const [x0, y0, x1, y1] = feats.reduce(
      (b, f) => [Math.min(b[0], f.properties.bbox[0]), Math.min(b[1], f.properties.bbox[1]), Math.max(b[2], f.properties.bbox[2]), Math.max(b[3], f.properties.bbox[3])],
      [Infinity, Infinity, -Infinity, -Infinity],
    );
    const cos = Math.cos((((y0 + y1) / 2) * Math.PI) / 180);
    const k = (ANCHO - 16) / ((x1 - x0) * cos);
    const alto = Math.round((y1 - y0) * k + 16);
    const p = ([lon, lat]: Position) => `${((lon! - x0) * cos * k + 8).toFixed(1)} ${((y1 - lat!) * k + 8).toFixed(1)}`;
    const anillo = (r: Position[]) => `M${r.map(p).join("L")}Z`;
    const rutas = feats.map((f) => {
      const g = f.geometry;
      const polis = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
      return { codigo: f.properties.codigo, nombre: f.properties.nombre, d: polis.flatMap((poli) => poli.map(anillo)).join("") };
    });
    return { alto, rutas };
  }, [geo]);

  if (!dibujo) return null;
  return (
    <figure className="canarias">
      <svg viewBox={`0 0 ${ANCHO} ${dibujo.alto}`} width={ANCHO} height={dibujo.alto} role="group" aria-label="Canarias">
        {dibujo.rutas.map((r) => {
          const resumen = datos.provincias[r.codigo];
          const s = scoreProvincia(resumen, agregado, porIne);
          return (
            <g
              key={r.codigo}
              className="canarias-prov"
              role="button"
              tabIndex={0}
              aria-label={`${r.codigo} ${r.nombre}${resumen ? "" : ": sin datos todavía"}`}
              onClick={() => onProvincia(r.codigo)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onProvincia(r.codigo);
                }
              }}
            >
              <title>{`${r.codigo} · ${r.nombre}`}</title>
              <path d={r.d} fill={resumen ? colorScore(s) : C.modulo} stroke={C.junta} strokeWidth="1" />
              {!resumen && <path d={r.d} fill="url(#rayado-canarias)" />}
            </g>
          );
        })}
        <defs>
          <pattern id="rayado-canarias" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
            <rect width="1.4" height="6" fill="#56595f" />
          </pattern>
        </defs>
      </svg>
      <figcaption>Canarias</figcaption>
    </figure>
  );
}
