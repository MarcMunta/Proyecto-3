import { useEffect, useMemo, useRef, useState } from "react";
import type { ApiFuente, DatosApis, ObjetoBbdd } from "../data/datosApis";
import { normalizar, num } from "../format";
import { Comparativa, Flecha } from "./Piezas";

const ETIQUETA_CAPA: Record<string, string> = { bronze: "Bronze", silver: "Silver", gold: "Gold" };
const DESCRIPCION_ESQUEMA: Record<string, string> = {
  fuentes: "Una tabla por fuente (capa Silver)",
  modelo: "Tablas para entrenar y predecir",
  dw: "Modelo en estrella: dimensiones y hechos",
  gold: "Tablas agregadas de este panel",
  meta: "Trazabilidad de la carga y de la publicación",
};
const DIAS_AL_DIA = 31;

/** «2026-11-18T17:43:48» → «18/11/2026 17:43». */
export function fecha(iso: string | null | undefined, conHora = true): string {
  if (!iso) return "—";
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return iso;
  return `${m[3]}/${m[2]}/${m[1]}${conHora && m[4] ? ` ${m[4]}:${m[5]}` : ""}`;
}

function Indicador({ etiqueta, valor, unidad }: { etiqueta: string; valor: string; unidad?: string }) {
  return (
    <div className="datos-kpi">
      <span>{etiqueta}</span>
      <strong>{valor}{unidad && <small> {unidad}</small>}</strong>
    </div>
  );
}

/** Descargas por día: columnas finas con el valor en el título (tooltip) y en el texto alternativo. */
function ColumnasDias({ dias }: { dias: { dia: string; descargas: number }[] }) {
  if (!dias.length) return null;
  const max = Math.max(...dias.map((d) => d.descargas), 1);
  const ancho = 100 / dias.length;
  return (
    <figure className="datos-columnas">
      <svg viewBox="0 0 100 40" preserveAspectRatio="none" role="img"
        aria-label={dias.map((d) => `${fecha(d.dia, false)}: ${d.descargas} descargas`).join("; ")}>
        {dias.map((d, i) => {
          const alto = Math.max(0.6, (d.descargas / max) * 38);
          return (
            <rect key={d.dia} x={i * ancho + ancho * 0.15} y={40 - alto} width={ancho * 0.7} height={alto} rx={0.6}>
              <title>{`${fecha(d.dia, false)}: ${num(d.descargas)} descargas`}</title>
            </rect>
          );
        })}
      </svg>
      <figcaption>
        <span>{fecha(dias[0]!.dia, false)}</span>
        <span>máx. {num(max)} descargas en un día</span>
        <span>{fecha(dias[dias.length - 1]!.dia, false)}</span>
      </figcaption>
    </figure>
  );
}

function FichaApi({ api }: { api: ApiFuente }) {
  return (
    <details className="modelo-fila">
      <summary className="modelo-columnas">
        <span className="modelo-nombre">
          {api.fuente}
          <small>{api.dominio ?? "sin dominio"} · {api.naturaleza || "sin clasificar"}</small>
        </span>
        <span className="modelo-cifra">{num(api.descargas)}</span>
        <span className="modelo-cifra">{num(api.megabytes, 1)}</span>
      </summary>
      <div className="modelo-detalle">
        <dl className="modelo-operaciones">
          <div><dt>Origen</dt><dd>{api.dominio ?? "—"}</dd></div>
          {api.url_ejemplo && (
            <div>
              <dt>Endpoint</dt>
              <dd><a href={api.url_ejemplo} target="_blank" rel="noopener noreferrer">{api.url_ejemplo}</a></dd>
            </div>
          )}
          <div><dt>Acceso</dt><dd>{api.acceso || "—"}</dd></div>
          <div><dt>Código</dt><dd>{api.modulo}</dd></div>
          <div><dt>Ficheros</dt><dd>{num(api.ficheros)} en data/raw</dd></div>
          <div><dt>Descargas</dt><dd>{fecha(api.primera_descarga)} → {fecha(api.ultima_descarga)}</dd></div>
        </dl>
        <p><strong>Caché y optimización.</strong> {api.estrategia_cache || "Sin ficha en el catálogo (cpd.capas.CATALOGO_APIS)."}</p>
      </div>
    </details>
  );
}

function Esquema({ nombre, objetos }: { nombre: string; objetos: ObjetoBbdd[] }) {
  const filas = objetos.reduce((s, o) => s + o.filas, 0);
  return (
    <details className="modelo-fila">
      <summary className="modelo-columnas">
        <span className="modelo-nombre">
          {nombre}
          <small>{DESCRIPCION_ESQUEMA[nombre] ?? "Esquema del almacén"}</small>
        </span>
        <span className="modelo-cifra">{num(objetos.length)}</span>
        <span className="modelo-cifra">{num(filas)}</span>
      </summary>
      <div className="modelo-detalle">
        <table className="datos-tabla">
          <caption className="sr-only">Tablas del esquema {nombre}</caption>
          <thead><tr><th scope="col">Tabla</th><th scope="col">Tipo</th><th scope="col">Filas</th><th scope="col">Columnas</th></tr></thead>
          <tbody>
            {objetos.map((o) => (
              <tr key={o.tabla}><th scope="row">{o.tabla}</th><td>{o.tipo}</td><td>{num(o.filas)}</td><td>{num(o.columnas)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function CatalogoDatos({ datos, cargando, zona, volver }: {
  datos: DatosApis | null; cargando: boolean; zona?: string; volver: string;
}) {
  const titulo = useRef<HTMLHeadingElement>(null);
  const [busqueda, setBusqueda] = useState("");
  useEffect(() => { titulo.current?.focus({ preventScroll: true }); }, []);

  const consulta = normalizar(busqueda.trim());
  const apis = useMemo(() => (datos?.apis ?? []).filter((a) =>
    normalizar(`${a.fuente} ${a.dominio ?? ""} ${a.modulo}`).includes(consulta)), [datos, consulta]);
  const dias = useMemo(() => {
    const porDia = new Map<string, number>();
    for (const d of datos?.descargas_dia ?? []) porDia.set(d.dia, (porDia.get(d.dia) ?? 0) + d.descargas);
    return [...porDia].sort(([a], [b]) => a.localeCompare(b)).map(([dia, descargas]) => ({ dia, descargas }));
  }, [datos]);
  const esquemas = useMemo(() => {
    const grupos = new Map<string, ObjetoBbdd[]>();
    for (const o of datos?.bbdd.objetos ?? []) grupos.set(o.esquema, [...(grupos.get(o.esquema) ?? []), o]);
    return [...grupos];
  }, [datos]);

  const volverA = <a className="volver" href={volver}><Flecha /> {zona ? `Ficha de ${zona}` : "Todas las provincias"}</a>;
  if (!datos) {
    return (
      <section className="modelos" aria-labelledby="titulo-datos">
        {volverA}
        <header className="ficha-cab">
          <h2 id="titulo-datos" tabIndex={-1} ref={titulo}>Datos, APIs y base de datos</h2>
        </header>
        {cargando ? <p role="status">Cargando datos…</p> : (
          <p role="status">
            No hay panel de datos en esta versión. Genéralo con <code>python -m cpd.almacen</code> o publica una versión nueva con <code>python -m cpd.publicar</code>.
          </p>
        )}
      </section>
    );
  }

  const k = datos.kpis;
  const totalCapas = datos.capas.reduce((s, c) => s + c.megabytes, 0) || 1;
  const pq = datos.formatos.find((f) => f.formato === "Parquet" && f.motor === "DuckDB");
  const csv = datos.formatos.find((f) => f.formato === "CSV" && f.motor === "DuckDB");
  const tam = Object.fromEntries(datos.formatos.map((f) => [f.formato, f.megabytes])) as Record<string, number>;
  const alDia = datos.watermarks.filter((w) => w.dias_desde != null && w.dias_desde <= DIAS_AL_DIA).length;

  return (
    <section className="modelos datos" aria-labelledby="titulo-datos">
      {volverA}
      <header className="ficha-cab">
        <h2 id="titulo-datos" tabIndex={-1} ref={titulo}>Datos, APIs y base de datos</h2>
        <p className="sub">
          De dónde sale cada cifra del mapa: fuentes y APIs, capas Bronze, Silver y Gold, el almacén DuckDB y la frescura de cada tabla.
          Almacén construido el {fecha(k.construido_en)}.
        </p>
      </header>

      <div className="datos-kpis">
        <Indicador etiqueta="Fuentes" valor={num(k.fuentes)} />
        <Indicador etiqueta="Descargas" valor={num(k.descargas)} />
        <Indicador etiqueta="Tablas" valor={num(k.tablas)} />
        <Indicador etiqueta="Filas" valor={num(k.filas)} />
        <Indicador etiqueta="Datos originales" valor={num(k.megabytes_bronze)} unidad="MB" />
        <Indicador etiqueta="Base de datos" valor={num(datos.bbdd.megabytes, 1)} unidad="MB" />
      </div>

      <section className="bloque" aria-labelledby="datos-capas">
        <h3 id="datos-capas">Cómo viajan los datos <span className="h-nota">API → Bronze → Silver → Gold → DuckDB → este mapa</span></h3>
        <div className="reparto datos-reparto" role="img"
          aria-label={datos.capas.map((c) => `${ETIQUETA_CAPA[c.capa] ?? c.capa}: ${num(c.megabytes, 1)} MB`).join(", ")}>
          {datos.capas.map((c) => (
            <span key={c.capa} className={`capa-${c.capa}`} style={{ flexGrow: Math.max(c.megabytes / totalCapas, 0.02) }} />
          ))}
        </div>
        <ol className="datos-capas">
          {datos.capas.map((c) => (
            <li key={c.capa}>
              <span className={`muestra capa-${c.capa}`} aria-hidden="true" />
              <div>
                <strong>{ETIQUETA_CAPA[c.capa] ?? c.capa}</strong> <code>{c.rutas}</code>
                <p className="dato-linea"><strong>{num(c.ficheros)}</strong> ficheros · <strong>{num(c.megabytes, 1)}</strong> MB · {c.formatos}</p>
                <p className="sub">{c.que_es}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="dato-linea">
          Ingesta con reintentos (backoff exponencial y jitter), caché con caducidad, límite de ritmo y peticiones en paralelo.
          Este panel solo lee: no descarga ni calcula nada.
        </p>
      </section>

      <section className="bloque" aria-labelledby="datos-apis">
        <h3 id="datos-apis">De dónde salen los datos <span className="h-nota">{num(datos.apis.length)} fuentes y APIs</span></h3>
        <h4 className="datos-h4">Descargas por fuente</h4>
        <Comparativa items={datos.apis.map((a) => ({ etiqueta: a.fuente, valor: a.descargas }))} unidad="desc." />
        <h4 className="datos-h4">Volumen descargado</h4>
        <Comparativa items={[...datos.apis].filter((a) => a.megabytes > 0).sort((a, b) => b.megabytes - a.megabytes)
          .map((a) => ({ etiqueta: a.fuente, valor: a.megabytes }))} unidad="MB" decimales={1} />
        <h4 className="datos-h4">Descargas por día</h4>
        <ColumnasDias dias={dias} />
        <div className="modelos-controles">
          <h4 className="datos-h4">Ficha de cada fuente</h4>
          <label className="buscador modelos-buscador">
            <span className="sr-only">Buscar fuente</span>
            <input type="search" placeholder="Buscar fuente o dominio" value={busqueda}
              onChange={(evento) => setBusqueda(evento.target.value)} />
          </label>
        </div>
        <div>
          <div className="modelo-columnas modelo-cabecera" aria-hidden="true">
            <span>Fuente</span><span>Descargas</span><span>MB</span>
          </div>
          {apis.length ? apis.map((a) => <FichaApi key={a.fuente} api={a} />)
            : <p role="status">Ninguna fuente coincide con «{busqueda}».</p>}
        </div>
      </section>

      <section className="bloque" aria-labelledby="datos-bbdd">
        <h3 id="datos-bbdd">Base de datos <span className="h-nota">{datos.bbdd.motor} · {datos.bbdd.fichero}</span></h3>
        <Comparativa items={esquemas.map(([nombre, objetos]) => ({ etiqueta: nombre, valor: objetos.reduce((s, o) => s + o.filas, 0) }))}
          unidad="filas" />
        <div>
          <div className="modelo-columnas modelo-cabecera" aria-hidden="true">
            <span>Esquema</span><span>Tablas</span><span>Filas</span>
          </div>
          {esquemas.map(([nombre, objetos]) => <Esquema key={nombre} nombre={nombre} objetos={objetos} />)}
        </div>
      </section>

      <section className="bloque" aria-labelledby="datos-frescura">
        <h3 id="datos-frescura">Frescura de los datos <span className="h-nota">{num(alDia)} de {num(datos.watermarks.length)} tablas con dato del último mes</span></h3>
        <Comparativa items={[...datos.watermarks].sort((a, b) => (a.dias_desde ?? 0) - (b.dias_desde ?? 0))
          .map((w) => ({ etiqueta: `${w.tabla} · ${fecha(w.watermark, false)}`, valor: w.dias_desde }))} unidad="días" />
        <p className="dato-linea">
          Días desde el último dato de cada tabla (su <em>watermark</em>). Población, renta y PIB son anuales: muchos días no indican un fallo.
        </p>
      </section>

      <section className="bloque" aria-labelledby="datos-bronze">
        <h3 id="datos-bronze">Datos originales por carpeta <span className="h-nota">capa Bronze, data/raw</span></h3>
        <Comparativa items={datos.bronze.filter((b) => b.megabytes > 0).map((b) => ({ etiqueta: b.carpeta, valor: b.megabytes }))}
          unidad="MB" decimales={1} />
      </section>

      {pq && csv && (
        <section className="bloque" aria-labelledby="datos-formatos">
          <h3 id="datos-formatos">CSV frente a Parquet <span className="h-nota">{pq.tabla}, media de {pq.columna}</span></h3>
          <h4 className="datos-h4">Tamaño del fichero</h4>
          <Comparativa items={[{ etiqueta: "CSV", valor: tam.CSV ?? null }, { etiqueta: "Parquet", valor: tam.Parquet ?? null }]}
            unidad="MB" decimales={2} />
          <h4 className="datos-h4">Tiempo de la consulta (menos es mejor)</h4>
          <Comparativa items={datos.formatos.map((f) => ({ etiqueta: `${f.formato} · ${f.motor}`, valor: f.segundos * 1000 }))}
            unidad="ms" decimales={1} />
          <p className="dato-linea">
            Parquet ocupa <strong>{num((tam.CSV ?? 0) / (tam.Parquet || 1), 1)}</strong> veces menos y DuckDB lo consulta{" "}
            <strong>{num(csv.segundos / (pq.segundos || 1), 0)}</strong> veces más rápido que el CSV, porque solo lee la columna que necesita.
          </p>
        </section>
      )}
    </section>
  );
}
