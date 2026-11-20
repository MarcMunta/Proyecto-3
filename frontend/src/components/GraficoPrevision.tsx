import { useId } from "react";
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
}

const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const corto = (aaaamm: string) => {
  const [a, m] = aaaamm.split("-").map(Number) as [number, number];
  return `${MESES_CORTOS[m - 1] ?? m} ${String(a).slice(2)}`;
};

/**
 * Serie mensual real (línea clara) y previsión a 1 año (línea naranja) con su intervalo (banda). El eje vertical se
 * ajusta a la historia y a la previsión; si el extremo alto del intervalo se sale mucho, la banda se recorta y se dice.
 */
export function GraficoPrevision({ titulo, historia, prevision, unidad, escala = 1, decimales = 0, nota }: Props) {
  const idTitulo = useId();
  if (!prevision.length) return null;
  const W = 480;
  const H = 150;
  const izq = 6;
  const der = 6;
  const arriba = 14;
  const abajo = 20;
  const meses = [...historia.map((p) => p.mes), ...prevision.map((p) => p.mes)];
  const n = meses.length;
  const x = (i: number) => izq + (i / Math.max(n - 1, 1)) * (W - izq - der);
  const valores = [...historia.map((p) => p.valor), ...prevision.map((p) => p.valor)].map((v) => v / escala);
  const bajos = prevision.map((p) => (p.inferior ?? p.valor) / escala);
  const altos = prevision.map((p) => (p.superior ?? p.valor) / escala);
  const maxDatos = Math.max(...valores);
  const tope = maxDatos * 1.45;
  const recortado = Math.max(...altos) > tope;
  const max = Math.min(Math.max(...altos, maxDatos), tope);
  const min = Math.max(0, Math.min(...bajos, ...valores) * 0.92);
  const y = (v: number) => arriba + (1 - (Math.min(v, max) - min) / (max - min || 1)) * (H - arriba - abajo);
  const desde = historia.length;
  const linea = (pts: { i: number; v: number }[]) => pts.map((p, k) => `${k ? "L" : "M"}${x(p.i).toFixed(1)} ${y(p.v).toFixed(1)}`).join("");
  const hist = historia.map((p, i) => ({ i, v: p.valor / escala }));
  const prev = prevision.map((p, k) => ({ i: desde + k, v: p.valor / escala }));
  const unionPrev = hist.length ? [hist[hist.length - 1]!, ...prev] : prev;
  const banda =
    prevision.map((_, k) => `${k ? "L" : "M"}${x(desde + k).toFixed(1)} ${y(altos[k]!).toFixed(1)}`).join("") +
    prevision
      .map((_, k) => k)
      .reverse()
      .map((k) => `L${x(desde + k).toFixed(1)} ${y(bajos[k]!).toFixed(1)}`)
      .join("") +
    "Z";
  const mediaPrev = prev.reduce((s, p) => s + p.v, 0) / prev.length;
  const mediaHist = hist.slice(-12).reduce((s, p) => s + p.v, 0) / Math.max(hist.slice(-12).length, 1);
  const marcas = [0, desde, n - 1].filter((i, k, a) => i < n && a.indexOf(i) === k);
  return (
    <figure className="grafico-prevision" aria-labelledby={idTitulo}>
      <figcaption id={idTitulo} className="gp-titulo">
        {titulo}
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${titulo}. Media del último año ${num(mediaHist, decimales)} ${unidad}; media prevista para los próximos 12 meses ${num(mediaPrev, decimales)} ${unidad}, de ${mesLegible(prevision[0]!.mes)} a ${mesLegible(prevision[prevision.length - 1]!.mes)}.`}
      >
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={izq} x2={W - der} y1={arriba + f * (H - arriba - abajo)} y2={arriba + f * (H - arriba - abajo)} className="gp-rejilla" />
        ))}
        <path d={banda} className="gp-banda" />
        {desde > 0 && <line x1={x(desde - 1)} x2={x(desde - 1)} y1={arriba - 6} y2={H - abajo} className="gp-hoy" />}
        <path d={linea(hist)} className="gp-real" />
        <path d={linea(unionPrev)} className="gp-prevision" />
        <text x={izq} y={10} className="gp-eje">
          {num(max, decimales)}
        </text>
        <text x={izq} y={H - abajo - 3} className="gp-eje">
          {num(min, decimales)}
        </text>
        {marcas.map((i) => (
          <text key={i} x={x(i)} y={H - 5} className="gp-eje" textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}>
            {corto(meses[i]!)}
          </text>
        ))}
      </svg>
      <p className="gp-leyenda">
        <span className="gp-l-real" aria-hidden="true" /> real · <span className="gp-l-prev" aria-hidden="true" /> previsto ·{" "}
        <span className="gp-l-banda" aria-hidden="true" /> intervalo 10-90 %
        {recortado ? " (recortado arriba)" : ""} · {unidad}
        {nota ? ` · ${nota}` : ""}
      </p>
    </figure>
  );
}
