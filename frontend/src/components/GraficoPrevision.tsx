import { useCallback, useId, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { PuntoMes, PuntoPrevision } from "../data/previsiones";
import { mesLegible, num } from "../format";

interface Props {
  titulo: string;
  historia: PuntoMes[];
  prevision: PuntoPrevision[];
  /** Unidad que se muestra (p. ej. «€/MWh» o «GWh»). */
  unidad: string;
  /** Divide los valores antes de mostrarlos (p. ej. 1000 para pasar de MWh a GWh). */
  escala?: number;
  decimales?: number;
  nota?: string;
  /** Serie anual: `mes` es «AAAA-01» y el eje muestra solo el año. */
  anual?: boolean;
  /** Aviso destacado (p. ej. si el modelo no cumple el mínimo de acierto). */
  aviso?: string;
}

interface Punto {
  mes: string;
  real: number | null;
  previsto: number | null;
  inferior: number | null;
  superior: number | null;
}

const ALTO = 176;
const MARGEN = { arriba: 18, derecha: 52, abajo: 22, izquierda: 44 };
const ANCHO_POR_DEFECTO = 480;

/** Ancho real del contenedor (px). El SVG se dibuja a ese ancho, así el texto nunca se deforma. */
function useAncho(): [(el: HTMLDivElement | null) => void, number] {
  const [ancho, setAncho] = useState(0);
  const observador = useRef<ResizeObserver | null>(null);
  const ref = useCallback((el: HTMLDivElement | null) => {
    observador.current?.disconnect();
    if (!el) return;
    if (typeof ResizeObserver === "undefined") {
      setAncho(ANCHO_POR_DEFECTO);
      return;
    }
    observador.current = new ResizeObserver(([e]) => e && setAncho(Math.round(e.contentRect.width)));
    observador.current.observe(el);
  }, []);
  return [ref, ancho];
}

/** Eje con marcas «redondas» (1, 2 o 5 × 10ⁿ) que cubren [min, max]. */
export function ejeRedondo(min: number, max: number, cuantas = 4) {
  const bruto = (max - min) / cuantas || 1;
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const paso = [1, 2, 5, 10].map((f) => f * potencia).find((p) => p >= bruto) ?? bruto;
  const inicio = Math.floor(min / paso) * paso;
  const fin = Math.ceil(max / paso) * paso;
  const marcas: number[] = [];
  for (let v = inicio; v <= fin + paso / 1e6; v += paso) marcas.push(Number(v.toFixed(6)));
  return { marcas, inicio, fin, decimales: Math.max(0, -Math.floor(Math.log10(paso))) };
}

/**
 * Serie real (azul) y previsión (magenta) con su intervalo 10-90 % (banda). Al pasar el ratón, tocar o usar las
 * flechas del teclado, una línea vertical marca el mes y un recuadro da sus valores. Los mismos datos están en la tabla
 * «Ver los datos». Colores comprobados con el validador de paletas (daltonismo y contraste sobre el fondo oscuro).
 */
export function GraficoPrevision({ titulo, historia, prevision, unidad, escala = 1, decimales = 0, nota, anual = false, aviso }: Props) {
  const id = useId();
  const [refMarco, anchoMedido] = useAncho();
  const [activo, setActivo] = useState<number | null>(null);

  const puntos: Punto[] = useMemo(
    () => [
      ...historia.map((p) => ({ mes: p.mes, real: p.valor / escala, previsto: null, inferior: null, superior: null })),
      ...prevision.map((p) => ({
        mes: p.mes,
        real: null,
        previsto: p.valor / escala,
        inferior: p.inferior != null ? p.inferior / escala : null,
        superior: p.superior != null ? p.superior / escala : null,
      })),
    ],
    [historia, prevision, escala],
  );

  if (!prevision.length) return null;
  const n = puntos.length;
  const desde = historia.length;
  const nombreMes = (m: string) => (anual ? m.slice(0, 4) : mesLegible(m));
  const fmt = (v: number | null) => (v == null ? "—" : num(v, decimales));

  // Escala vertical: datos + intervalo. Si el extremo alto del intervalo se dispara, se recorta (y se dice en la leyenda).
  const valores = puntos.flatMap((p) => [p.real, p.previsto]).filter((v): v is number => v != null);
  const altos = puntos.map((p) => p.superior).filter((v): v is number => v != null);
  const bajos = puntos.map((p) => p.inferior).filter((v): v is number => v != null);
  const tope = Math.max(...valores) * 1.45;
  const recortado = altos.some((v) => v > tope);
  // Con valores negativos (p. ej. temperaturas bajo cero) el eje baja de 0; si no, empieza un poco por debajo del mínimo.
  const minimo = Math.min(...valores, ...bajos);
  const eje = ejeRedondo(minimo >= 0 ? minimo * 0.97 : minimo * 1.03, Math.min(Math.max(...valores, ...altos), tope));

  const w = Math.max(anchoMedido || ANCHO_POR_DEFECTO, 260);
  const anchoPlot = w - MARGEN.izquierda - MARGEN.derecha;
  const x = (i: number) => MARGEN.izquierda + (i / Math.max(n - 1, 1)) * anchoPlot;
  const y = (v: number) => MARGEN.arriba + (1 - (Math.min(v, eje.fin) - eje.inicio) / (eje.fin - eje.inicio || 1)) * (ALTO - MARGEN.arriba - MARGEN.abajo);
  const ruta = (pares: [number, number][]) => pares.map(([i, v], k) => `${k ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");

  const real = puntos.flatMap((p, i): [number, number][] => (p.real != null ? [[i, p.real]] : []));
  const previsto = puntos.flatMap((p, i): [number, number][] => (p.previsto != null ? [[i, p.previsto]] : []));
  const ultimoReal = real[real.length - 1];
  const final = previsto[previsto.length - 1]!;
  const conBanda = puntos.flatMap((p, i) => (p.inferior != null && p.superior != null ? [{ i, inf: p.inferior, sup: p.superior }] : []));
  const banda = conBanda.length
    ? [
        ...conBanda.map((b, k) => `${k ? "L" : "M"}${x(b.i).toFixed(1)},${y(b.sup).toFixed(1)}`),
        ...[...conBanda].reverse().map((b) => `L${x(b.i).toFixed(1)},${y(b.inf).toFixed(1)}`),
        "Z",
      ].join("")
    : "";

  // Eje X: un rótulo por año (enero o cada punto anual), saltando años si no caben (≈ 40 px por rótulo).
  const anios = puntos.flatMap((p, i) => (anual || p.mes.endsWith("-01") ? [{ i, texto: p.mes.slice(0, 4) }] : []));
  const salto = Math.max(1, Math.ceil((anios.length * 40) / Math.max(anchoPlot, 1)));
  const marcasX = anios.filter((_, k) => k % salto === 0);

  const indicePuntero = (e: PointerEvent<SVGSVGElement>) => {
    const caja = e.currentTarget.getBoundingClientRect();
    const rel = (e.clientX - caja.left - MARGEN.izquierda) / Math.max(caja.width - MARGEN.izquierda - MARGEN.derecha, 1);
    return Math.min(n - 1, Math.max(0, Math.round(rel * (n - 1))));
  };
  const teclado = (e: KeyboardEvent<SVGSVGElement>) => {
    const mover: Record<string, (a: number | null) => number> = {
      ArrowRight: (a) => Math.min(n - 1, a == null ? desde : a + 1),
      ArrowLeft: (a) => Math.max(0, a == null ? desde - 1 : a - 1),
      Home: () => 0,
      End: () => n - 1,
    };
    if (mover[e.key]) {
      e.preventDefault();
      setActivo((a) => mover[e.key]!(a));
    } else if (e.key === "Escape") setActivo(null);
  };
  const pa = activo != null ? puntos[activo] : undefined;
  const ANCHO_TIP = 168;
  const tipX = activo != null ? (x(activo) + 12 + ANCHO_TIP > w ? x(activo) - 12 - ANCHO_TIP : x(activo) + 12) : 0;

  return (
    <figure className="grafico-prevision" aria-labelledby={`${id}-t`}>
      <figcaption id={`${id}-t`} className="gp-titulo">
        {titulo}
      </figcaption>
      {aviso && <p className="gp-aviso">{aviso}</p>}
      <div className="gp-marco" ref={refMarco}>
        <svg
          width={w}
          height={ALTO}
          viewBox={`0 0 ${w} ${ALTO}`}
          role="img"
          tabIndex={0}
          aria-label={`${titulo}. Último dato real: ${fmt(ultimoReal?.[1] ?? null)} ${unidad} (${nombreMes(puntos[desde - 1]?.mes ?? puntos[0]!.mes)}). Previsión: ${fmt(final[1])} ${unidad} en ${nombreMes(puntos[n - 1]!.mes)}. Flechas izquierda y derecha para recorrer los ${anual ? "años" : "meses"}.`}
          onPointerMove={(e) => setActivo(indicePuntero(e))}
          onPointerDown={(e) => setActivo(indicePuntero(e))}
          onPointerLeave={() => setActivo(null)}
          onKeyDown={teclado}
          onBlur={() => setActivo(null)}
        >
          {eje.marcas.map((m) => (
            <g key={m}>
              <line x1={MARGEN.izquierda} x2={w - MARGEN.derecha} y1={y(m)} y2={y(m)} className="gp-rejilla" />
              <text x={MARGEN.izquierda - 8} y={y(m)} className="gp-eje" textAnchor="end" dominantBaseline="middle">
                {num(m, eje.decimales)}
              </text>
            </g>
          ))}
          {marcasX.map((m) => (
            <text key={m.i} x={x(m.i)} y={ALTO - 4} className="gp-eje" textAnchor="middle">
              {m.texto}
            </text>
          ))}
          {banda && <path d={banda} className="gp-banda" />}
          {desde > 0 && (
            <g aria-hidden="true">
              <line x1={x(desde - 1)} x2={x(desde - 1)} y1={MARGEN.arriba - 6} y2={ALTO - MARGEN.abajo} className="gp-hoy" />
              <text x={x(desde - 1) + 5} y={MARGEN.arriba - 8} className="gp-eje">
                previsión
              </text>
            </g>
          )}
          <path d={ruta(real)} className="gp-real" />
          <path d={ruta(ultimoReal ? [ultimoReal, ...previsto] : previsto)} className="gp-prevision" />
          {ultimoReal && <circle cx={x(ultimoReal[0])} cy={y(ultimoReal[1])} r={4} className="gp-punto gp-punto-real" />}
          <circle cx={x(final[0])} cy={y(final[1])} r={4} className="gp-punto gp-punto-prev" />
          <text x={x(final[0]) + 8} y={y(final[1])} className="gp-valor" dominantBaseline="middle">
            {fmt(final[1])}
          </text>
          {pa && activo != null && (
            <g pointerEvents="none" aria-hidden="true">
              <line x1={x(activo)} x2={x(activo)} y1={MARGEN.arriba} y2={ALTO - MARGEN.abajo} className="gp-cruz" />
              {pa.real != null && <circle cx={x(activo)} cy={y(pa.real)} r={4} className="gp-punto gp-punto-real" />}
              {pa.previsto != null && <circle cx={x(activo)} cy={y(pa.previsto)} r={4} className="gp-punto gp-punto-prev" />}
            </g>
          )}
        </svg>
        {pa && (
          <div className="gp-tip" style={{ left: tipX, width: ANCHO_TIP }} role="status">
            <span className="gp-tip-mes">{nombreMes(pa.mes)}</span>
            {pa.real != null && (
              <span className="gp-tip-fila">
                <i className="gp-l-real" aria-hidden="true" />
                real <strong>{fmt(pa.real)}</strong>
              </span>
            )}
            {pa.previsto != null && (
              <span className="gp-tip-fila">
                <i className="gp-l-prev" aria-hidden="true" />
                previsto <strong>{fmt(pa.previsto)}</strong>
              </span>
            )}
            {pa.inferior != null && pa.superior != null && (
              <span className="gp-tip-int">
                entre {fmt(pa.inferior)} y {fmt(pa.superior)}
              </span>
            )}
            <span className="gp-tip-int">{unidad}</span>
          </div>
        )}
      </div>
      <p className="gp-leyenda">
        <span>
          <i className="gp-l-real" aria-hidden="true" /> real
        </span>
        <span>
          <i className="gp-l-prev" aria-hidden="true" /> previsto
        </span>
        <span>
          <i className="gp-l-banda" aria-hidden="true" /> intervalo 10-90 %{recortado ? " (recortado arriba)" : ""}
        </span>
        <span>{unidad}</span>
        {nota && <span>{nota}</span>}
      </p>
      <details className="gp-datos">
        <summary>Ver los datos</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">{anual ? "Año" : "Mes"}</th>
              <th scope="col">Real</th>
              <th scope="col">Previsto</th>
              <th scope="col">Intervalo 10-90 %</th>
            </tr>
          </thead>
          <tbody>
            {puntos.slice(Math.max(0, desde - 12)).map((p) => (
              <tr key={p.mes}>
                <th scope="row">{nombreMes(p.mes)}</th>
                <td>{fmt(p.real)}</td>
                <td>{fmt(p.previsto)}</td>
                <td>{p.inferior != null && p.superior != null ? `${fmt(p.inferior)}-${fmt(p.superior)}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
