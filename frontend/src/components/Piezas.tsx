import type { ReactNode } from "react";
import type { Punto } from "../live/redata";
import { cuartoDelDia, hora, num } from "../format";

/** Flecha de "volver", dibujada a trazo de 1,5 px como las reglas del tablero. */
export function Flecha() {
  return (
    <svg className="flecha" width="16" height="12" viewBox="0 0 16 12" aria-hidden="true" focusable="false">
      <path d="M6 1 1 6l5 5M1.5 6H15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" />
    </svg>
  );
}

/** De dónde sale una cifra: dato en vivo, dato oficial real o modelo con datos de demostración. */
export function Origen({ tipo, momento, fuente }: { tipo: "vivo" | "real" | "demo" | "error"; momento?: number | null; fuente?: string }) {
  if (tipo === "vivo")
    return (
      <span className="origen origen-vivo">
        <i aria-hidden="true" />
        En directo{momento ? ` ${hora(momento)}` : ""}
        {fuente ? ` · ${fuente}` : ""}
      </span>
    );
  if (tipo === "real") return <span className="origen origen-real">{fuente ?? "Dato real"}</span>;
  if (tipo === "error") return <span className="origen origen-error">Sin conexión</span>;
  return <span className="origen origen-demo">Demo</span>;
}

export function Cifra({ etiqueta, valor, unidad, origen, grande, nota }: {
  etiqueta: string;
  valor: ReactNode;
  unidad?: string;
  origen?: ReactNode;
  grande?: boolean;
  nota?: ReactNode;
}) {
  return (
    <div className={`cifra ${grande ? "cifra-grande" : ""}`}>
      <dt>{etiqueta}</dt>
      <dd>
        <span className="cifra-valor">
          {valor}
          {unidad && <span className="cifra-unidad">{unidad}</span>}
        </span>
        {origen}
        {nota && <span className="cifra-nota">{nota}</span>}
      </dd>
    </div>
  );
}

/** Medidor de 10 segmentos (como una barra de LEDs del panel). */
export function Medidor({ valor, etiqueta, peso }: { valor: number | null; etiqueta: string; peso?: number }) {
  const n = valor == null ? 0 : Math.round(valor / 10);
  return (
    <div className="medidor">
      <span className="medidor-et">
        {etiqueta}
        {peso != null && <span className="medidor-peso">peso {num(peso * 100)} %</span>}
      </span>
      <span className="medidor-seg" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={valor ?? undefined} aria-label={etiqueta}>
        {Array.from({ length: 10 }, (_, i) => (
          <i key={i} className={i < n ? "on" : ""} />
        ))}
      </span>
      <span className="medidor-v">{num(valor, 0)}</span>
    </div>
  );
}

/** Barra de un índice 0-1 con su umbral (p. ej. estrés hídrico 0,7). */
export function Indice({ valor, umbral, etiquetaUmbral }: { valor: number | null; umbral: number; etiquetaUmbral: string }) {
  const v = valor == null ? null : Math.max(0, Math.min(1, valor));
  return (
    <span className="indice" aria-hidden="true">
      <span className="indice-pista">
        {v != null && <span className={`indice-relleno ${v >= umbral ? "alto" : ""}`} style={{ width: `${v * 100}%` }} />}
        <span className="indice-umbral" style={{ left: `${umbral * 100}%` }} />
      </span>
      <span className="indice-et" style={{ left: `${umbral * 100}%` }}>
        {etiquetaUmbral}
      </span>
    </span>
  );
}

/** Precio spot de hoy cada 15 min, con el precio del modelo como referencia. */
export function GraficoPrecio({ serie, referencia, ahora }: { serie: Punto[]; referencia: number; ahora: number }) {
  if (!serie.length) return null;
  const W = 480;
  const H = 120;
  const max = Math.max(referencia, ...serie.map((p) => p.v)) * 1.08;
  const min = Math.min(0, ...serie.map((p) => p.v));
  const y = (v: number) => H - 18 - ((v - min) / (max - min)) * (H - 26);
  const ancho = W / 96;
  const idx = cuartoDelDia;
  const actual = serie.reduce<Punto | null>((a, p) => (p.t <= ahora ? p : a), null);
  return (
    <figure className="grafico-precio">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={`Precio spot de hoy cada 15 minutos; precio del modelo ${num(referencia)} €/MWh`}>
        {serie.map((p) => {
          const i = idx(p.t);
          const yy = y(p.v);
          return (
            <rect
              key={p.t}
              x={i * ancho + 0.4}
              y={Math.min(yy, y(0))}
              width={Math.max(ancho - 0.8, 0.6)}
              height={Math.abs(y(0) - yy)}
              className={actual && p.t === actual.t ? "barra-ahora" : p.t > ahora ? "barra-futura" : "barra"}
            />
          );
        })}
        <line x1="0" x2={W} y1={y(referencia)} y2={y(referencia)} className="linea-ref" />
        {[0, 6, 12, 18].map((h) => (
          <text key={h} x={h * 4 * ancho + 2} y={H - 4} className="eje">
            {String(h).padStart(2, "0")}h
          </text>
        ))}
      </svg>
      <figcaption>
        <span className="ley-barra" /> spot de hoy (cada 15 min) <span className="ley-ref" /> precio del modelo {num(referencia)} €/MWh
      </figcaption>
    </figure>
  );
}
