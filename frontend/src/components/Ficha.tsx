import { useEffect, useMemo, useRef } from "react";
import type { Municipio, PropsProvincia, ProvinciaMeta, Viabilidad } from "../data/types";
import { rangoVanClasificadas, type ClaseRentabilidad, type Prediccion, type ProvinciaPrediccion } from "../data/prediccion";
import type { EnVivo } from "../live/usePolling";
import type { Demanda, Mix, Precios } from "../live/redata";
import type { TiempoActual } from "../live/openmeteo";
import { diaHora, mesLegible, millones, num, pct } from "../format";
import { COLOR_CLASE, nombreClaseDe } from "../model/colores";
import { UMBRAL_FREE_COOLING_C, recalcularConPrecio } from "../model/finanzas";
import { Flap } from "./Flap";
import { IconoClase } from "./IconoClase";
import { Barra, Comparativa, Flecha, GraficoPrecio, Vivo, type ItemComparativa } from "./Piezas";
import { GraficoPrevision } from "./GraficoPrevision";
import { ACIERTO_MINIMO, type ImpactoLocal, type MedioPlazo, type OperacionPrevista, type Previsiones, type RenovablePrevista, type SeriePrevista, type TemperaturaPrevista } from "../data/previsiones";

interface Props {
  meta: ProvinciaMeta;
  geoProps: PropsProvincia | undefined;
  prediccion: Prediccion;
  previsiones: Previsiones | null;
  viabilidad: Viabilidad;
  sitio: string | null;
  onSitio: (ine: string) => void;
  onVolver: () => void;
  precios: EnVivo<Precios>;
  demanda: EnVivo<Demanda>;
  mix: EnVivo<Mix>;
  tiempo: EnVivo<Record<string, TiempoActual>>;
}

/** En la demostración, las cifras de otro municipio analizado de la misma provincia. */
function deMunicipio(m: Municipio, base: ProvinciaPrediccion, clase: ClaseRentabilidad | null): ProvinciaPrediccion {
  return {
    ...base,
    clase,
    score: m.score_global,
    estado: m.estado,
    van_eur: m.salidas.van_eur,
    roi: m.salidas.roi,
    payback_anos: m.salidas.payback_anos,
    capex_eur: m.salidas.capex_total_eur,
    opex_eur_anual: m.salidas.opex_eur,
    temp_media_anual_c: m.entradas.temp_media_c ?? null,
    estres_hidrico: m.entradas.estres_hidrico_idx ?? null,
    motivos: m.motivos,
  };
}


export function Ficha(p: Props) {
  const { meta, geoProps, prediccion, viabilidad } = p;
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titulo.current?.focus({ preventScroll: true });
  }, [meta.codigo]);

  const demo = prediccion.tipo === "demo";
  const base = prediccion.provincias.get(meta.codigo);
  const porIne = useMemo(() => new Map(viabilidad.municipios.map((m) => [m.codigo_ine, m])), [viabilidad]);
  const sitios = demo && base?.municipios ? base.municipios.map((ine) => porIne.get(ine)).filter((m): m is Municipio => Boolean(m)) : [];
  const elegido = demo ? (sitios.find((m) => m.codigo_ine === p.sitio) ?? sitios[0]) : undefined;
  const d = base && elegido && elegido !== sitios[0] ? deMunicipio(elegido, base, prediccion.clasesMunicipio.get(elegido.codigo_ine) ?? null) : base;
  const tiempo = p.tiempo.datos?.[meta.codigo];
  const rango = useMemo(() => rangoVanClasificadas(prediccion), [prediccion]);
  const descartada = d?.clase === "no_rentable" && d.estado === "No viable";

  return (
    <article className="ficha" aria-labelledby="ficha-titulo">
      <button type="button" className="volver" onClick={p.onVolver}>
        <Flecha /> Toda España <kbd>Esc</kbd>
      </button>
      <header className="ficha-cab">
        <h2 id="ficha-titulo" ref={titulo} tabIndex={-1}>
          {meta.nombre}
        </h2>
        <p className="sub">
          {[d?.ccaa, geoProps?.n_municipios != null ? `${num(geoProps.n_municipios)} municipios` : null, geoProps?.area_km2 != null ? `${num(geoProps.area_km2)} km²` : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </header>

      {d?.clase ? (
        <div className="clase" style={{ ["--c" as string]: COLOR_CLASE[d.clase] }}>
          <IconoClase clase={d.clase} tam={34} />
          <div>
            <strong>
              <span className="sr-only">Rentabilidad </span>
              {nombreClaseDe(d.clase, d.estado)}
            </strong>
            {descartada ? (
              <span className="clase-nota">no pasa un filtro eliminatorio (ver «Por qué»): el VAN supone que se pudiera construir</span>
            ) : (
              <>
                {demo && <span className="clase-nota">relativa · demostración</span>}
                {prediccion.tipo === "simulacion" && (
                  <span className="clase-nota">
                    relativa entre provincias · simulación con datos reales
                    {rango ? ` · el VAN de las viables solo va de ${millones(rango.min)} a ${millones(rango.max)}` : ""}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="clase clase-sin">
          <span className="muestra-rayado grande" aria-hidden="true" />
          <div>
            <strong>Sin datos todavía</strong>
          </div>
          <p>
            {demo
              ? `La demostración no tiene ningún municipio de ${meta.nombre}. Con la predicción real (data/curated/predicciones_provincia.json) aparecerá aquí.`
              : `Los datos no incluyen ${meta.nombre}.`}
          </p>
        </div>
      )}

      {d?.faltan && d.faltan.length > 0 && <p className="faltan">Sin dato de {d.faltan.join(", ")}: esa parte no se ha evaluado.</p>}

      {sitios.length > 1 && (
        <nav className="sitios" aria-label="Municipios analizados">
          {sitios.map((m) => {
            const c = prediccion.clasesMunicipio.get(m.codigo_ine) ?? null;
            return (
              <button key={m.codigo_ine} type="button" aria-pressed={m === elegido} onClick={() => p.onSitio(m.codigo_ine)}>
                <IconoClase clase={c} tam={13} /> {m.municipio}
              </button>
            );
          })}
        </nav>
      )}

      {d && (
        <>
          <dl className="heroes">
            <div>
              <dt>VAN</dt>
              <dd>
                <Flap texto={d.van_eur == null ? "—" : num(d.van_eur / 1e6, Math.abs(d.van_eur) >= 1e8 ? 0 : 1)} etiqueta={millones(d.van_eur)} />
                {d.van_eur != null && <span className="hero-u">M€</span>}
              </dd>
            </div>
            <div>
              <dt>ROI</dt>
              <dd>
                <Flap texto={d.roi == null ? "—" : num(d.roi * 100, 0)} retardo={80} etiqueta={pct(d.roi)} />
                {d.roi != null && <span className="hero-u">%</span>}
              </dd>
            </div>
            <div>
              <dt>Recuperación</dt>
              <dd>
                {d.payback_anos == null ? (
                  <span className="hero-texto">no se recupera</span>
                ) : (
                  <>
                    <Flap texto={num(d.payback_anos, 1)} retardo={160} />
                    <span className="hero-u">años</span>
                  </>
                )}
              </dd>
            </div>
          </dl>

          {d.score != null && (
            <Barra etiqueta="Viabilidad" valor={d.score} max={100} texto={`${num(d.score, 0)}/100${d.estado ? ` · ${d.estado}` : ""}`} />
          )}

          <BloqueLuz {...p} d={d} municipio={demo ? elegido : undefined} />

          <BloqueClima
            d={d}
            tiempo={tiempo}
            vivo={p.tiempo}
            capital={meta.capital}
            reservas={d.ambito_hidrografico ? p.previsiones?.reservas.get(d.ambito_hidrografico) : undefined}
            ambito={d.ambito_hidrografico ?? null}
            temperatura={p.previsiones?.temperatura.get(meta.codigo)}
            operacion={p.previsiones?.operacion.get(meta.codigo)}
            medio={p.previsiones?.medioPlazo.get(meta.codigo)}
            impacto={p.previsiones?.impacto.get(meta.codigo)}
          />

          {(d.capex_eur != null || d.opex_eur_anual != null || d.prob_cpd != null || d.cpd_existentes != null) && (
            <section className="bloque" aria-labelledby="b-inv">
              <h3 id="b-inv">Inversión, red y mercado</h3>
              <dl className="pares">
                {d.capex_eur != null && (
                  <div>
                    <dt>Inversión (CAPEX)</dt>
                    <dd>{millones(d.capex_eur)}</dd>
                  </div>
                )}
                {d.opex_eur_anual != null && (
                  <div>
                    <dt>Coste anual (OPEX)</dt>
                    <dd>{millones(d.opex_eur_anual)}</dd>
                  </div>
                )}
                {d.cpd_existentes != null && (
                  <div>
                    <dt>CPD ya existentes</dt>
                    <dd>{num(d.cpd_existentes)}</dd>
                  </div>
                )}
                {d.capacidad_demanda_otorgada_mw != null && (
                  <div>
                    <dt>Red otorgada a nuevos grandes consumos (comunidad)</dt>
                    <dd>{num(d.capacidad_demanda_otorgada_mw)} MW</dd>
                  </div>
                )}
                {d.capacidad_demanda_pendiente_mw != null && (
                  <div>
                    <dt>Pedida y en trámite (comunidad)</dt>
                    <dd>{num(d.capacidad_demanda_pendiente_mw)} MW</dd>
                  </div>
                )}
                {d.capacidad_acceso_disponible_mw != null && (
                  <div>
                    <dt>Aún disponible para demanda (comunidad)</dt>
                    <dd>{num(d.capacidad_acceso_disponible_mw)} MW</dd>
                  </div>
                )}
                {d.precio_suelo_urbano_eur_m2 != null && (
                  <div>
                    <dt>Suelo urbano (mediana de 4 trimestres)</dt>
                    <dd>{num(d.precio_suelo_urbano_eur_m2)} €/m²</dd>
                  </div>
                )}
                {d.latencia_hubs_rtt_ms != null && (
                  <div>
                    <dt>Latencia a Madrid y Barcelona (la peor de las dos)</dt>
                    <dd>{num(d.latencia_hubs_rtt_ms, 1)} ms</dd>
                  </div>
                )}
                {d.aceleracion_sismica_g != null && (
                  <div>
                    <dt>Aceleración sísmica básica de la capital (NCSE-02)</dt>
                    <dd>{d.aceleracion_sismica_g <= 0.04 ? "≤ 0,04" : num(d.aceleracion_sismica_g, 2)} g</dd>
                  </div>
                )}
                {d.cobertura_renovable_pct != null && (
                  <div>
                    <dt>Renovable generada / demanda (comunidad, 12 meses previstos)</dt>
                    <dd>{num(d.cobertura_renovable_pct, 0)} %</dd>
                  </div>
                )}
                {d.pue != null && (
                  <div>
                    <dt>PUE estimado</dt>
                    <dd>{num(d.pue, 2)}</dd>
                  </div>
                )}
                {d.latencia_rtt_ms != null && (
                  <div>
                    <dt>Latencia al IXP</dt>
                    <dd>{d.latencia_rtt_ms < 1 ? "menos de 1 ms" : `${num(d.latencia_rtt_ms, 1)} ms`}</dd>
                  </div>
                )}
              </dl>
              {d.prob_cpd != null && (
                <Barra
                  etiqueta="Probabilidad de tener un CPD (modelo)"
                  valor={d.prob_cpd}
                  max={1}
                  texto={pct(d.prob_cpd)}
                  nota={notaProbCpd(prediccion)}
                />
              )}
            </section>
          )}

          <BloqueDemanda d={d} prediccion={prediccion} previsiones={p.previsiones} />

          {d.motivos.length > 0 && (
            <section className="bloque" aria-labelledby="b-motivos">
              <h3 id="b-motivos">Por qué</h3>
              <ul className="motivos">
                {d.motivos.map((t) => (
                  <li key={t}>
                    <i aria-hidden="true" />
                    {t}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <p className="fuente">
        {demo ? (
          <>
            <strong>Demostración:</strong> indicadores sintéticos; clase relativa (tercios del VAN; en rojo, no pasa un filtro
            eliminatorio o VAN ≤ 0).
          </>
        ) : prediccion.tipo === "simulacion" ? (
          <>
            <strong>Simulación</strong> con el modelo del proyecto y datos reales de la provincia
            {prediccion.actualizado ? `, actualizados el ${diaHora(Date.parse(prediccion.actualizado))}` : ""}
            {prediccion.mesReferencia ? ` (clima, agua y precio medio hasta ${mesLegible(prediccion.mesReferencia)})` : ""}. Clase relativa
            (tercios del VAN; en rojo, no pasa un filtro eliminatorio o VAN ≤ 0).
            {prediccion.noEvaluado?.length ? ` A escala provincial no se evalúan: ${prediccion.noEvaluado.join(", ")}.` : ""}
          </>
        ) : (
          <>Predicción del modelo (data/curated/predicciones_provincia.json){d?.generado_en ? `, generada el ${diaHora(Date.parse(d.generado_en))}` : ""}.</>
        )}
      </p>
    </article>
  );
}

function BloqueLuz(p: Props & { d: ProvinciaPrediccion; municipio: Municipio | undefined }) {
  const { precios, demanda, mix, d, viabilidad, municipio, prediccion } = p;
  const pr = precios.datos;
  const demo = prediccion.tipo === "demo";
  const simulacion = prediccion.tipo === "simulacion";
  const vivos: ItemComparativa[] = [
    { etiqueta: "Spot ahora", valor: pr?.spotAhora?.v ?? null, vivo: true, momento: pr?.spotAhora?.t },
    { etiqueta: "Media de hoy", valor: pr?.spotMediaHoy ?? null, vivo: true, momento: precios.actualizado },
  ];
  const items: ItemComparativa[] = simulacion
    ? [
        { etiqueta: "Media de 12 meses (usada en el cálculo)", valor: d.precio_luz_usado_eur_mwh ?? null },
        { etiqueta: "Media de mañana (OMIE)", valor: d.precio_luz_previsto_eur_mwh },
        ...vivos,
      ]
    : [
        { etiqueta: demo ? "Precio del modelo" : "Precio actual (modelo)", valor: d.precio_luz_actual_eur_mwh },
        { etiqueta: "Precio previsto", valor: d.precio_luz_previsto_eur_mwh },
        ...vivos,
      ];
  const referencia = simulacion ? (d.precio_luz_usado_eur_mwh ?? null) : d.precio_luz_actual_eur_mwh;
  const etiquetaReferencia = simulacion ? "media de 12 meses usada en el cálculo" : demo ? "precio del modelo" : "precio actual del modelo";
  const mediaHoy = pr?.spotMediaHoy ?? null;
  const recalculo = municipio && mediaHoy != null ? recalcularConPrecio(municipio, mediaHoy, viabilidad) : null;
  return (
    <section className="bloque" aria-labelledby="b-luz">
      <h3 id="b-luz">
        Luz <span className="h-nota">€/MWh · precio de mercado nacional (peninsular)</span>
      </h3>
      <Comparativa items={items} unidad="€/MWh" decimales={1} />
      {pr && <GraficoPrecio serie={pr.spot} referencia={referencia} etiquetaReferencia={etiquetaReferencia} ahora={Date.now()} />}
      {precios.error && !pr && (
        <p className="aviso-vivo">
          Sin respuesta de Red Eléctrica. <button type="button" onClick={precios.reintentar}>Reintentar</button>
        </p>
      )}
      {recalculo && municipio && (
        <dl className="pares">
          <div>
            <dt>VAN con la luz de hoy ({num(mediaHoy, 0)} €/MWh)</dt>
            <dd>{millones(recalculo.van_eur)}</dd>
          </div>
          <div>
            <dt>VAN con {num(viabilidad.precios.precio_electricidad_eur_mwh)} €/MWh</dt>
            <dd>{millones(municipio.salidas.van_eur)}</dd>
          </div>
        </dl>
      )}
      {simulacion && p.previsiones?.precio && (
        <GraficoPrevision
          titulo="Precio de la luz: últimos 3 años y previsión a 1 año"
          historia={p.previsiones.precio.historia}
          prevision={p.previsiones.precio.prevision}
          unidad="€/MWh"
          nota={`${NOMBRE_MODELO[p.previsiones.precio.modelo] ?? p.previsiones.precio.modelo}${p.previsiones.precio.errorTest != null ? `; error medio a 1 año ${num(p.previsiones.precio.errorTest, 0)} €/MWh` : ""}`}
          aviso={avisoAcierto(p.previsiones.precio)}
        />
      )}
      {simulacion && <SensibilidadPrecio d={d} prediccion={prediccion} />}
      {d.codigo_ccaa && p.previsiones?.renovables.get(d.codigo_ccaa) && <Renovables serie={p.previsiones.renovables.get(d.codigo_ccaa)!} />}
      {(demanda.datos?.ahora || mix.datos?.renovableAyer) && (
        <p className="linea-vivo">
          {demanda.datos?.ahora && <>Demanda {num(demanda.datos.ahora.v)} MW</>}
          {demanda.datos?.ahora && mix.datos?.renovableAyer && " · "}
          {mix.datos?.renovableAyer && <>renovable ayer {pct(mix.datos.renovableAyer.v)}</>}
          <Vivo momento={demanda.datos?.ahora?.t} fuente="Red Eléctrica" />
        </p>
      )}
    </section>
  );
}

/**
 * % de generación renovable de la comunidad: gráfico mes a mes (orientativo si no llega al mínimo de acierto) y el %
 * medio de los próximos 12 meses, que es la cifra útil para un CPD y tiene su propio acierto.
 */
function Renovables({ serie }: { serie: RenovablePrevista }) {
  const anual = [serie.aciertoAnualValidacion, serie.aciertoAnualTest].filter((v): v is number => v != null);
  return (
    <>
      <GraficoPrevision
        titulo={`Generación renovable de ${serie.nombre}: últimos 3 años y previsión a 1 año`}
        historia={serie.historia}
        prevision={serie.prevision}
        unidad="% renovable"
        nota={textoAcierto(serie) ? `${textoAcierto(serie)} mes a mes` : undefined}
        aviso={avisoAcierto(serie)}
      />
      {serie.mediaPrevista != null && (
        <p className="dato-linea">
          Renovable previsto para los próximos 12 meses: <strong>{num(serie.mediaPrevista, 0)} %</strong>
          {serie.mediaInferior != null && serie.mediaSuperior != null ? ` (${num(serie.mediaInferior, 0)}-${num(serie.mediaSuperior, 0)} %)` : ""}
          {serie.media12m != null ? `; último año ${num(serie.media12m, 0)} %` : ""}
          {anual.length ? `. Acierto de este % anual: ${num(Math.min(...anual), 1)} %.` : "."}
        </p>
      )}
    </>
  );
}

/** «acierto 95,6 %» con el peor de validación y test (100 − WAPE). */
function textoAcierto(s: SeriePrevista): string | undefined {
  const valores = [s.aciertoValidacion, s.aciertoTest].filter((v): v is number => v != null);
  return valores.length ? `acierto ${num(Math.min(...valores), 1)} %` : undefined;
}

/** Aviso si el modelo no llega al mínimo de acierto exigido (85 %). */
function avisoAcierto(s: SeriePrevista): string | undefined {
  const valores = [s.aciertoValidacion, s.aciertoTest].filter((v): v is number => v != null);
  if (!valores.length || Math.min(...valores) >= ACIERTO_MINIMO) return undefined;
  // Con un decimal: 84,8 % redondeado a «85 %» parecería que llega al mínimo.
  return `Previsión orientativa: el modelo acierta un ${num(Math.min(...valores), 1)} %, por debajo del mínimo del ${ACIERTO_MINIMO} % exigido. No se usa en el cálculo del VAN.`;
}

const NOMBRE_MODELO: Record<string, string> = {
  solo_poblacion: "regresión logística con la población",
  logistica: "regresión logística",
  bosque: "random forest",
  estacional: "mismo mes del año anterior",
  media_12m: "media de los últimos 12 meses",
  combinacion: "combinación de los 3 mejores modelos",
  ets: "ETS (Holt-Winters)",
  naive: "último valor",
  tendencia_estacionalidad: "tendencia + estacionalidad",
  ridge: "regresión Ridge",
  gradient_boosting: "gradient boosting",
  ridge_gas: "regresión Ridge con el gas",
  climatologia: "climatología",
  anomalia_persistente: "anomalía persistente",
};

/** Nota de la barra de prob_cpd: qué modelo es y cuánto acierta (sale de docs/modelos/prob_cpd.md). */
function notaProbCpd(p: Prediccion): string {
  const m = p.modelos?.prob_cpd;
  if (!m) return "propensión según provincias parecidas, no la probabilidad de que se construya uno nuevo";
  return [
    `${NOMBRE_MODELO[m.modelo] ?? m.modelo}: provincias parecidas a las que ya tienen CPD`,
    m.provincias_con_cpd != null ? `${num(m.provincias_con_cpd)} de 52 tienen` : null,
    m.roc_auc != null ? `ROC-AUC ${num(m.roc_auc, 2)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Cuánto cambia el VAN con el precio de la luz (modelo precio_luz): con el precio del último mes y con los extremos
 * del rango probable del precio medio de los 12 meses siguientes. Los VAN los calcula simular_provincias.py.
 */
function SensibilidadPrecio({ d, prediccion }: { d: ProvinciaPrediccion; prediccion: Prediccion }) {
  const m = prediccion.modelos?.precio_luz;
  if (!m || (d.van_eur_precio_ultimo_mes == null && d.van_eur_precio_inferior == null)) return null;
  const eur = (v: number | null | undefined) => `${num(v, 0)} €/MWh`;
  return (
    <>
      <dl className="pares">
        {d.van_eur_precio_previsto != null && (
          <div>
            <dt>VAN con el precio previsto a 1 año ({eur(m.media_prevista_eur_mwh)})</dt>
            <dd>{millones(d.van_eur_precio_previsto)}</dd>
          </div>
        )}
        {d.van_eur_precio_ultimo_mes != null && (
          <div>
            <dt>
              VAN si la luz sigue como {m.ultimo_mes ? `en ${mesLegible(m.ultimo_mes)}` : "el último mes"} ({eur(m.ultimo_mes_eur_mwh)})
            </dt>
            <dd>{millones(d.van_eur_precio_ultimo_mes)}</dd>
          </div>
        )}
        {d.van_eur_precio_inferior != null && d.van_eur_precio_superior != null && (
          <div>
            <dt>
              VAN en el rango probable del precio ({num(m.inferior_eur_mwh, 0)}-{eur(m.superior_eur_mwh)})
            </dt>
            <dd>
              {millones(d.van_eur_precio_superior)} a {millones(d.van_eur_precio_inferior)}
            </dd>
          </div>
        )}
      </dl>
      <p className="dato-linea">
        Precio medio previsto para los próximos 12 meses: <strong>{eur(m.media_prevista_eur_mwh)}</strong> (modelo:{" "}
        {NOMBRE_MODELO[m.modelo] ?? m.modelo}
        {m.mae_test_eur_mwh != null ? `; error medio en test ${num(m.mae_test_eur_mwh, 0)} €/MWh` : ""}). El precio de la luz pesa más en
        el VAN que la ubicación.
      </p>
    </>
  );
}

/** Demanda eléctrica de la comunidad: último año con datos válidos y previsión de los 12 meses siguientes. */
function BloqueDemanda({ d, prediccion, previsiones }: { d: ProvinciaPrediccion; prediccion: Prediccion; previsiones: Previsiones | null }) {
  const ultimos = d.demanda_ccaa_ultimos_12m_mwh;
  const prevision = d.demanda_ccaa_prevision_12m_mwh;
  if (ultimos == null && prevision == null) return null;
  const gwh = (v: number | null | undefined) => (v == null ? "—" : `${num(v / 1e3)} GWh`);
  const modelo = prediccion.modelos?.demanda;
  const serieDemanda = d.codigo_ccaa ? previsiones?.demanda.get(d.codigo_ccaa) : undefined;
  return (
    <section className="bloque" aria-labelledby="b-demanda">
      <h3 id="b-demanda">
        Demanda eléctrica <span className="h-nota">{d.ccaa ?? "comunidad autónoma"} · 12 meses</span>
      </h3>
      {serieDemanda && (
        <GraficoPrevision
          titulo={`Demanda de ${serieDemanda.nombre}: últimos 3 años y previsión a 1 año`}
          historia={serieDemanda.historia}
          prevision={serieDemanda.prevision}
          unidad="GWh"
          escala={1000}
          nota={textoAcierto(serieDemanda)}
          aviso={avisoAcierto(serieDemanda)}
        />
      )}
      {previsiones?.demanda10 && (
        <GraficoPrevision
          titulo="Demanda eléctrica de España: desde 2007 y previsión a 10 años"
          historia={previsiones.demanda10.historia}
          prevision={previsiones.demanda10.prevision}
          unidad="TWh al año"
          anual
          nota={textoAcierto(previsiones.demanda10)}
          aviso={avisoAcierto(previsiones.demanda10)}
        />
      )}
      <dl className="pares">
        <div>
          <dt>Último año{d.demanda_ccaa_hasta ? ` (hasta ${mesLegible(d.demanda_ccaa_hasta)})` : ""}</dt>
          <dd>{gwh(ultimos)}</dd>
        </div>
        <div>
          <dt>Previsión de los 12 meses siguientes</dt>
          <dd>{gwh(prevision)}</dd>
        </div>
      </dl>
      {(d.demanda_ccaa_prevision_inferior_mwh != null || modelo) && (
        <p className="dato-linea">
          {d.demanda_ccaa_prevision_inferior_mwh != null && d.demanda_ccaa_prevision_superior_mwh != null && (
            <>
              Rango probable: {gwh(d.demanda_ccaa_prevision_inferior_mwh)} a {gwh(d.demanda_ccaa_prevision_superior_mwh)}.{" "}
            </>
          )}
          {modelo && (
            <>
              Modelo: {NOMBRE_MODELO[modelo.modelo] ?? modelo.modelo}
              {modelo.mape_test_pct != null ? ` (error medio en test ${num(modelo.mape_test_pct, 1)} %)` : ""}.
            </>
          )}
        </p>
      )}
    </section>
  );
}

function BloqueClima({
  d, tiempo, vivo, capital, reservas, ambito, temperatura, operacion, medio, impacto,
}: {
  d: ProvinciaPrediccion;
  tiempo: TiempoActual | undefined;
  vivo: EnVivo<Record<string, TiempoActual>>;
  capital: string;
  reservas?: SeriePrevista;
  ambito: string | null;
  temperatura?: TemperaturaPrevista;
  operacion?: OperacionPrevista;
  medio?: MedioPlazo;
  impacto?: ImpactoLocal;
}) {
  const hayModelo =
    d.horas_free_cooling_anual != null || d.reserva_hidrica_pct != null || d.estres_hidrico != null || d.temp_media_anual_c != null || operacion != null || medio != null || impacto != null;
  const notaTemperatura = temperatura
    ? [textoAcierto(temperatura), temperatura.errorTest != null ? `error medio ${num(temperatura.errorTest, 1)} °C al mes` : null].filter(Boolean).join(" · ")
    : undefined;
  return (
    <section className="bloque" aria-labelledby="b-clima">
      <h3 id="b-clima">Clima y agua</h3>
      {temperatura && (
        <GraficoPrevision
          titulo={`Temperatura media en ${temperatura.nombre}: últimos 3 años y previsión a 1 año`}
          historia={temperatura.historia}
          prevision={temperatura.prevision}
          unidad="°C"
          decimales={1}
          nota={notaTemperatura || undefined}
          aviso={avisoAcierto(temperatura)}
        />
      )}
      {reservas && (
        <GraficoPrevision
          titulo={`Reserva de los embalses (${ambito}): últimos 3 años y previsión a 1 año`}
          historia={reservas.historia}
          prevision={reservas.prevision}
          unidad="% de la capacidad"
          nota={textoAcierto(reservas)}
          aviso={avisoAcierto(reservas)}
        />
      )}
      {hayModelo && (
        <div className="barras">
          {d.horas_free_cooling_anual != null && (
            <Barra etiqueta="Horas de free cooling al año" valor={d.horas_free_cooling_anual} max={8760} texto={`${num(d.horas_free_cooling_anual)} h`} nota="enfriar con aire exterior, sin compresores" />
          )}
          {d.reserva_hidrica_pct != null && (
            <Barra etiqueta="Reserva hídrica" valor={d.reserva_hidrica_pct} max={100} texto={`${num(d.reserva_hidrica_pct)} %`} />
          )}
          {d.estres_hidrico != null && (
            <Barra etiqueta="Estrés hídrico" valor={d.estres_hidrico} max={1} umbral={0.7} etiquetaUmbral="umbral alto 0,7" texto={num(d.estres_hidrico, 2)} nota="0 = sin estrés · 1 = máximo · marca: umbral alto (0,7)" />
          )}
          {d.temp_media_anual_c != null && (
            <p className="dato-linea">
              Temperatura media anual <strong>{num(d.temp_media_anual_c, 1)} °C</strong> (la que usa el PUE)
              {temperatura?.mediaPrevista != null && (
                <>
                  {" "}
                  · próximos 12 meses <strong>{num(temperatura.mediaPrevista, 1)} °C</strong>
                  {temperatura.mediaInferior != null && temperatura.mediaSuperior != null
                    ? ` (${num(temperatura.mediaInferior, 1)}-${num(temperatura.mediaSuperior, 1)} °C)`
                    : ""}
                </>
              )}
            </p>
          )}
          {operacion && (
            <p className="dato-linea">
              Operación prevista del CPD (12 meses):{" "}
              {operacion.pue != null && <>PUE <strong>{num(operacion.pue, 2)}</strong></>}
              {operacion.consumoMwh != null && <> · {num(operacion.consumoMwh / 1e3)} GWh</>}
              {operacion.emisionesT != null && <> · <strong>{num(operacion.emisionesT)} t CO2</strong> con el mix de su comunidad</>}
              {operacion.reservaMinimaPct != null && (
                <>
                  {" "}
                  · reserva mínima de los embalses del ámbito {num(operacion.reservaMinimaPct)} %
                  {operacion.mesReservaMinima ? ` (${mesLegible(operacion.mesReservaMinima)})` : ""}
                </>
              )}
              {operacion.aciertoEmisiones != null && <>. Acierto de las emisiones: {num(operacion.aciertoEmisiones, 1)} %.</>}
            </p>
          )}
          {impacto && (impacto.pctDemanda != null || impacto.pctAgua != null) && (
            <p className="dato-linea">
              Impacto en su comunidad (12 meses):
              {impacto.pctDemanda != null && (
                <>
                  {" "}
                  <strong>{num(impacto.pctDemanda, 1)} %</strong> de la electricidad
                  {impacto.habitantesElectricidad != null && <> (como {num(impacto.habitantesElectricidad)} habitantes)</>}
                </>
              )}
              {impacto.sinCapacidadLibre ? (
                <> · <strong>0 MW libres</strong> en la red de acceso: hoy no cabe</>
              ) : (
                impacto.pctCapacidad != null && (
                  <>
                    {" "}
                    · <strong>{num(impacto.pctCapacidad)} %</strong> de la capacidad libre de la red
                    {impacto.capacidadLibreMw != null && <> ({num(impacto.capacidadLibreMw)} MW)</>}
                  </>
                )
              )}
              {impacto.pctAgua != null && (
                <>
                  {" "}
                  · <strong>{num(impacto.pctAgua, 2)} %</strong> del agua
                  {impacto.habitantesAgua != null && <> (como {num(impacto.habitantesAgua)} habitantes)</>}
                  {impacto.anioAgua != null && <>, INE {impacto.anioAgua}</>}
                </>
              )}
              {impacto.acierto != null && <>. Acierto del % eléctrico: {num(impacto.acierto, 1)} %.</>}
            </p>
          )}
          {medio && medio.tempFinal != null && (
            <p className="dato-linea">
              A 10 años ({medio.anioFinal}): temperatura media <strong>{num(medio.tempFinal, 1)} °C</strong>
              {medio.tempInferior != null && medio.tempSuperior != null ? ` (${num(medio.tempInferior, 1)}-${num(medio.tempSuperior, 1)} °C)` : ""}
              {medio.temp10a != null && <> frente a {num(medio.temp10a, 1)} °C de media en los últimos 10 años</>}
              {medio.pueFinal != null && <> · PUE <strong>{num(medio.pueFinal, 2)}</strong></>}
              {medio.reservaDecadaPct != null && (
                <> · reserva media de los embalses del ámbito en la década <strong>{num(medio.reservaDecadaPct)} %</strong></>
              )}
              {medio.aciertoTemperaturaTest != null && <>. Acierto en test: temperatura {num(medio.aciertoTemperaturaTest, 1)} %</>}
              {medio.aciertoReservaDecadaTest != null && <>, agua media de la década {num(medio.aciertoReservaDecadaTest, 1)} %</>}
              {medio.aciertoTemperaturaTest != null || medio.aciertoReservaDecadaTest != null ? "." : ""}
            </p>
          )}
        </div>
      )}
      {tiempo ? (
        <p className="linea-vivo">
          Ahora en {capital}: <strong>{num(tiempo.temperatura_c, 1)} °C</strong> · {num(tiempo.humedad_pct)} % humedad · free cooling{" "}
          {tiempo.temperatura_c < UMBRAL_FREE_COOLING_C ? "sí" : "no"}
          <Vivo momento={tiempo.hora} fuente="Open-Meteo" />
        </p>
      ) : (
        <p className="aviso-vivo">
          {vivo.cargando ? "Cargando el tiempo actual…" : "Sin respuesta de Open-Meteo."}
          {!vivo.cargando && (
            <>
              {" "}
              <button type="button" onClick={vivo.reintentar}>Reintentar</button>
            </>
          )}
        </p>
      )}
    </section>
  );
}
