import { useEffect, useMemo, useRef } from "react";
import type { Municipio, PropsProvincia, ProvinciaMeta, Viabilidad } from "../data/types";
import type { ClaseRentabilidad, Prediccion, ProvinciaPrediccion } from "../data/prediccion";
import type { EnVivo } from "../live/usePolling";
import type { Demanda, Mix, Precios } from "../live/redata";
import type { TiempoActual } from "../live/openmeteo";
import { diaHora, mesLegible, millones, num, pct } from "../format";
import { COLOR_CLASE, NOMBRE_CLASE } from "../model/colores";
import { UMBRAL_FREE_COOLING_C, recalcularConPrecio } from "../model/finanzas";
import { Flap } from "./Flap";
import { IconoClase } from "./IconoClase";
import { Barra, Comparativa, Flecha, GraficoPrecio, Vivo, type ItemComparativa } from "./Piezas";

interface Props {
  meta: ProvinciaMeta;
  geoProps: PropsProvincia | undefined;
  prediccion: Prediccion;
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
              {NOMBRE_CLASE[d.clase]}
            </strong>
            {demo && <span className="clase-nota">relativa · demostración</span>}
            {prediccion.tipo === "simulacion" && <span className="clase-nota">relativa entre provincias · simulación con datos reales</span>}
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

          <BloqueClima d={d} tiempo={tiempo} vivo={p.tiempo} capital={meta.capital} />

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
                {d.pue != null && (
                  <div>
                    <dt>PUE estimado</dt>
                    <dd>{num(d.pue, 2)}</dd>
                  </div>
                )}
                {d.latencia_rtt_ms != null && (
                  <div>
                    <dt>Latencia al IXP</dt>
                    <dd>{num(d.latencia_rtt_ms, 1)} ms</dd>
                  </div>
                )}
              </dl>
              {d.prob_cpd != null && <Barra etiqueta="Probabilidad de que se instale un CPD" valor={d.prob_cpd} max={1} texto={pct(d.prob_cpd)} />}
            </section>
          )}

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
            <strong>Demostración:</strong> indicadores sintéticos; clase relativa (tercios del VAN, «no viable» = no rentable).
          </>
        ) : prediccion.tipo === "simulacion" ? (
          <>
            <strong>Simulación</strong> con el modelo del proyecto y datos reales de la provincia
            {prediccion.actualizado ? `, actualizados el ${diaHora(Date.parse(prediccion.actualizado))}` : ""}
            {prediccion.mesReferencia ? ` (clima, agua y precio medio hasta ${mesLegible(prediccion.mesReferencia)})` : ""}. Clase relativa
            (tercios del VAN; «no viable» = no rentable).
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

function BloqueClima({ d, tiempo, vivo, capital }: { d: ProvinciaPrediccion; tiempo: TiempoActual | undefined; vivo: EnVivo<Record<string, TiempoActual>>; capital: string }) {
  const hayModelo = d.horas_free_cooling_anual != null || d.reserva_hidrica_pct != null || d.estres_hidrico != null || d.temp_media_anual_c != null;
  return (
    <section className="bloque" aria-labelledby="b-clima">
      <h3 id="b-clima">Clima y agua</h3>
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
              Temperatura media anual <strong>{num(d.temp_media_anual_c, 1)} °C</strong>
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
