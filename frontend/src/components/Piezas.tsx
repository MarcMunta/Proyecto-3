import type { Punto } from "../live/redata";
import { cuartoDelDia, hora, num } from "../format";

/** Flecha de «volver», a trazo de 1,5 px. */
export function Flecha() {
  return (
    <svg className="flecha" width="16" height="12" viewBox="0 0 16 12" aria-hidden="true" focusable="false">
      <path d="M6 1 1 6l5 5M1.5 6H15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" />
    </svg>
  );
}

/** Marca discreta de dato en directo: punto que late + hora. */
export function Vivo({ momento, fuente }: { momento?: number | null; fuente?: string }) {
  return (
    <span className="vivo-marca">
      <i aria-hidden="true" />
      en directo{momento ? ` ${hora(momento)}` : ""}
      {fuente ? ` · ${fuente}` : ""}
    </span>
  );
}

/** Una magnitud como barra horizontal fina (0..máx), con su valor escrito y un umbral opcional. */
export function Barra({ etiqueta, valor, max, texto, umbral, etiquetaUmbral, nota }: {
  etiqueta: string;
  valor: number | null;
  max: number;
  texto: string;
  umbral?: number;
  etiquetaUmbral?: string;
  nota?: string;
}) {
  const f = valor == null ? 0 : Math.max(0, Math.min(1, valor / max));
  return (
    <div className="barra">
      <div className="barra-cab">
        <span>{etiqueta}</span>
        <strong>{texto}</strong>
      </div>
      <div className="barra-pista" role="meter" aria-label={etiqueta} aria-valuemin={0} aria-valuemax={max} aria-valuenow={valor ?? undefined} aria-valuetext={texto}>
        <span className="barra-relleno" style={{ width: `${f * 100}%` }} />
        {umbral != null && <i className="barra-umbral" style={{ left: `${(umbral / max) * 100}%` }} title={etiquetaUmbral} />}
      </div>
      {nota && <span className="barra-nota">{nota}</span>}
    </div>
  );
}

export interface ItemComparativa {
  etiqueta: string;
  valor: number | null;
  /** Dato en directo: se dibuja en blanco y lleva su hora. */
  vivo?: boolean;
  momento?: number | null;
}

/** Varias cifras de la misma unidad, comparadas como barras (p. ej. precios de la luz). */
export function Comparativa({ items, unidad, decimales = 0 }: { items: ItemComparativa[]; unidad: string; decimales?: number }) {
  const visibles = items.filter((i) => i.valor != null);
  if (!visibles.length) return null;
  const max = Math.max(...visibles.map((i) => i.valor!)) * 1.08;
  return (
    <ul className="comparativa">
      {visibles.map((i) => (
        <li key={i.etiqueta} className={i.vivo ? "es-vivo" : ""}>
          <span className="comparativa-et">
            {i.etiqueta}
            {i.vivo && <Vivo momento={i.momento} />}
          </span>
          <span className="comparativa-pista" aria-hidden="true">
            <span style={{ width: `${(i.valor! / max) * 100}%` }} />
          </span>
          <span className="comparativa-v">
            {num(i.valor, decimales)} <small>{unidad}</small>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Precio spot de hoy cada 15 min, con una línea de referencia. */
export function GraficoPrecio({ serie, referencia, etiquetaReferencia, ahora }: { serie: Punto[]; referencia: number | null; etiquetaReferencia: string; ahora: number }) {
  if (!serie.length) return null;
  const W = 480;
  const H = 96;
  const max = Math.max(referencia ?? 0, ...serie.map((p) => p.v)) * 1.08;
  const min = Math.min(0, ...serie.map((p) => p.v));
  const y = (v: number) => H - 16 - ((v - min) / (max - min)) * (H - 22);
  const ancho = W / 96;
  const actual = serie.reduce<Punto | null>((a, p) => (p.t <= ahora ? p : a), null);
  return (
    <figure className="grafico-precio">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={`Precio spot de hoy cada 15 minutos${referencia != null ? `; ${etiquetaReferencia} ${num(referencia)} €/MWh` : ""}`}>
        {serie.map((p) => {
          const i = cuartoDelDia(p.t);
          const yy = y(p.v);
          return (
            <rect
              key={p.t}
              x={i * ancho + 0.5}
              y={Math.min(yy, y(0))}
              width={Math.max(ancho - 1, 0.6)}
              height={Math.abs(y(0) - yy)}
              className={actual && p.t === actual.t ? "barra-ahora" : p.t > ahora ? "barra-futura" : "barra-pasada"}
            />
          );
        })}
        {referencia != null && <line x1="0" x2={W} y1={y(referencia)} y2={y(referencia)} className="linea-ref" />}
        {[0, 6, 12, 18].map((h) => (
          <text key={h} x={h * 4 * ancho + 2} y={H - 3} className="eje">
            {String(h).padStart(2, "0")}h
          </text>
        ))}
      </svg>
      <figcaption>
        Spot de hoy, cada 15 min{referencia != null && <> · línea: {etiquetaReferencia} ({num(referencia)} €/MWh)</>}
      </figcaption>
    </figure>
  );
}
