import { useEffect, useRef } from "react";
import type { Bloque, Municipio, PropsProvincia, ProvinciaMeta, ResumenProvincia, Viabilidad } from "../data/types";
import { BLOQUES } from "../data/types";
import type { EnVivo } from "../live/usePolling";
import type { Demanda, Mix, Precios } from "../live/redata";
import type { TiempoActual } from "../live/openmeteo";
import { diaHora, millones, num, pct } from "../format";
import { ETIQUETA_ESTADO } from "../model/colores";
import { UMBRAL_FREE_COOLING_C, recalcularConPrecio, tipoMotivo } from "../model/finanzas";
import { Flap } from "./Flap";
import { Lampara } from "./Lampara";
import { Cifra, Flecha, GraficoPrecio, Indice, Medidor, Origen } from "./Piezas";

const NOMBRE_BLOQUE: Record<Bloque, string> = {
  energia: "Energía (red eléctrica)",
  agua_refrigeracion: "Agua y refrigeración",
  conectividad: "Conectividad",
  riesgos_naturales: "Riesgos naturales",
  suelo_regulatorio: "Suelo y regulación",
  costes: "Costes",
  mercado_talento: "Mercado y talento",
  impacto: "Impacto local",
};

const REFRIGERACION: Record<string, string> = {
  aire: "por aire",
  evaporativa: "evaporativa",
  adiabatica: "adiabática",
  inmersion: "por inmersión",
};

interface Props {
  meta: ProvinciaMeta;
  geoProps: PropsProvincia | undefined;
  datos: Viabilidad;
  resumen: ResumenProvincia | undefined;
  porIne: Map<string, Municipio>;
  sitio: string | null;
  onSitio: (ine: string) => void;
  onVolver: () => void;
  precios: EnVivo<Precios>;
  demanda: EnVivo<Demanda>;
  mix: EnVivo<Mix>;
  tiempo: EnVivo<Record<string, TiempoActual>>;
}

export function Ficha(p: Props) {
  const { meta, geoProps, resumen } = p;
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    titulo.current?.focus({ preventScroll: true });
  }, [meta.codigo]);

  const elegido = p.sitio ? p.porIne.get(p.sitio) : undefined;
  const m = resumen ? (elegido?.provincia_codigo === meta.codigo ? elegido : p.porIne.get(resumen.mejor)) : undefined;
  const tiempo = p.tiempo.datos?.[meta.codigo];

  return (
    <article className="ficha" aria-labelledby="ficha-titulo">
      <header className="ficha-cab">
        <button type="button" className="volver" onClick={p.onVolver}>
          <Flecha /> Toda España <kbd>Esc</kbd>
        </button>
        <div className="ficha-titulo">
          <Flap texto={meta.codigo} largo={2} className="flap-codigo flap-xl" />
          <h2 id="ficha-titulo" ref={titulo} tabIndex={-1}>
            <Flap texto={meta.nombre} className="flap-xl" />
          </h2>
        </div>
        <p className="ficha-sub">
          Capital: {meta.capital}
          {geoProps?.n_municipios != null && <> · {num(geoProps.n_municipios)} municipios</>}
          {geoProps?.area_km2 != null && <> · {num(geoProps.area_km2)} km²</>}
          <Origen tipo="real" fuente="GISCO LAU 2024" />
        </p>
      </header>

      {!resumen || !m ? (
        <SinDatos {...p} actual={tiempo} />
      ) : (
        <ConDatos {...p} m={m} resumen={resumen} actual={tiempo} />
      )}
    </article>
  );
}

function SinDatos(p: Props & { actual: TiempoActual | undefined }) {
  return (
    <>
      <section className="veredicto veredicto-sin-datos">
        <div className="veredicto-estado">
          <Lampara estado="Sin datos" tam={22} />
          <Flap texto="SIN DATOS TODAVÍA" className="flap-l" />
        </div>
        <p className="explica">
          El modelo todavía no tiene ningún municipio de {p.meta.nombre}: por eso no se muestra estado, score ni
          cifras económicas. Cuando la tabla maestra con datos reales esté lista, se vuelve a generar con{" "}
          <code>npm run data</code> y esta provincia aparecerá con su análisis.
        </p>
      </section>
      <BloqueClimaVivo actual={p.actual} capital={p.meta.capital} vivo={p.tiempo} />
      <BloqueLuz {...p} m={undefined} />
    </>
  );
}

function ConDatos(p: Props & { m: Municipio; resumen: ResumenProvincia; actual: TiempoActual | undefined }) {
  const { m, resumen, datos } = p;
  const s = m.salidas;
  const e = m.entradas;
  const demo = m.sintetico;
  const origenDemo = demo ? <Origen tipo="demo" /> : undefined;
  const opex = [
    { k: "Energía", v: s.opex_energia_eur, c: "op-energia" },
    { k: "Personal", v: s.opex_personal_eur, c: "op-personal" },
    { k: "Mantenimiento", v: s.opex_mantenimiento_eur, c: "op-mant" },
    { k: "Impuestos locales", v: s.opex_impuestos_eur, c: "op-imp" },
    { k: "Agua", v: s.opex_agua_eur, c: "op-agua" },
  ];
  const totalOpex = s.opex_eur ?? 0;
  const estres = e.estres_hidrico_idx ?? null;
  const umbralEstres = Number(datos.umbrales.estres_hidrico_alto ?? 0.7);
  const sitios = resumen.municipios.map((ine) => p.porIne.get(ine)).filter((x): x is Municipio => Boolean(x));

  return (
    <>
      <section className="veredicto" aria-live="polite">
        <div className="veredicto-estado">
          <Lampara estado={m.estado} tam={26} />
          <Flap texto={ETIQUETA_ESTADO[m.estado]} className="flap-l" etiqueta={m.estado} />
        </div>
        <div className="veredicto-score">
          <Flap texto={num(m.score_global, 0)} largo={3} alinear="der" className="flap-cartel" etiqueta={`Score ${num(m.score_global, 1)} de 100`} />
          <span className="sobre">/100</span>
        </div>
        <p className="veredicto-pie">
          Score de <strong>{m.municipio}</strong>
          {resumen.n_municipios > 1 ? (
            <> · media de los {resumen.n_municipios} emplazamientos analizados: <strong>{num(resumen.score_medio, 1)}</strong></>
          ) : (
            <> · único emplazamiento analizado en la provincia</>
          )}
        </p>
        {demo && (
          <p className="sello-demo">
            <strong>Datos de demostración.</strong> Los indicadores de este municipio son sintéticos (inventados pero
            plausibles); el nombre, el código INE {m.codigo_ine} y las coordenadas son reales.
          </p>
        )}
      </section>

      {sitios.length > 1 && (
        <nav className="sitios" aria-label="Emplazamientos analizados en la provincia">
          {sitios.map((x) => (
            <button key={x.codigo_ine} type="button" aria-pressed={x.codigo_ine === m.codigo_ine} onClick={() => p.onSitio(x.codigo_ine)}>
              <Lampara estado={x.estado} tam={12} />
              <span>{x.municipio}</span>
              <span className="sitios-score">{num(x.score_global, 0)}</span>
            </button>
          ))}
        </nav>
      )}

      <section className="bloque" aria-labelledby="b-motivos">
        <h3 id="b-motivos">Por qué</h3>
        <ul className="motivos">
          {m.motivos.map((t) => {
            const tipo = tipoMotivo(t, m.estado);
            return (
              <li key={t} className={`motivo motivo-${tipo}`}>
                <Lampara
                  estado={tipo === "ko" ? "No viable" : tipo === "condicion" ? "Viable con condiciones" : tipo === "ok" ? "Viable" : "Sin datos"}
                  tam={13}
                />
                <span>{t}</span>
              </li>
            );
          })}
        </ul>
        <p className="nota">
          Filtros del embudo: M1 red eléctrica, M3 latencia, M4 regulación y suelo, M5 riesgos naturales, M6 agua y
          clima. Un filtro eliminatorio basta para «No viable».
        </p>
      </section>

      <section className="bloque" aria-labelledby="b-dinero">
        <h3 id="b-dinero">
          Rentabilidad <span className="h-nota">CPD de {num(datos.parametros.potencia_ti_mw)} MW de TI · {num(datos.parametros.vida_util_anos)} años · tasa {pct(datos.precios.tasa_descuento)}</span>
        </h3>
        <dl className="cifras cifras-dinero">
          <Cifra grande etiqueta="Inversión (CAPEX)" valor={<Flap texto={millones(s.capex_total_eur)} />} origen={origenDemo}
            nota={`${millones(datos.parametros.inversion_eur)} de obra y equipos + ${millones(s.coste_suelo_eur)} de suelo`} />
          <Cifra grande etiqueta="Coste anual (OPEX)" valor={<Flap texto={millones(s.opex_eur)} retardo={80} />} origen={origenDemo} />
          <Cifra grande etiqueta="VAN" valor={<Flap texto={millones(s.van_eur)} retardo={160} />} origen={origenDemo}
            nota={s.van_eur != null && s.van_eur >= 0 ? "Positivo: la inversión crea valor" : "Negativo: no compensa la inversión"} />
          <Cifra etiqueta="ROI" valor={<Flap texto={pct(s.roi)} retardo={220} />} origen={origenDemo} />
          <Cifra etiqueta="Recuperación (payback)" valor={<Flap texto={s.payback_anos == null ? "NO" : `${num(s.payback_anos, 1)} AÑOS`} retardo={280} />}
            origen={origenDemo} nota={s.payback_anos == null ? "No se recupera dentro de la vida útil" : undefined} />
          <Cifra etiqueta="Ingresos al año" valor={millones(s.ingresos_anuales_eur)} origen={origenDemo}
            nota={`alquiler ${millones(s.ingresos_alquiler_eur)} + energía repercutida ${millones(s.ingresos_energia_eur)}`} />
        </dl>
        <figure className="opex">
          <figcaption>Reparto del OPEX anual</figcaption>
          <div className="opex-barra" role="img" aria-label={opex.map((o) => `${o.k} ${millones(o.v)}`).join(", ")}>
            {opex.map((o) => (
              <span key={o.k} className={o.c} style={{ flexGrow: Math.max(0, (o.v ?? 0) / (totalOpex || 1)) }} />
            ))}
          </div>
          <ul className="opex-ley">
            {opex.map((o) => (
              <li key={o.k}>
                <i className={o.c} aria-hidden="true" />
                {o.k} <span>{millones(o.v)}</span>
              </li>
            ))}
          </ul>
        </figure>
      </section>

      <BloqueLuz {...p} m={m} />

      <section className="bloque" aria-labelledby="b-agua">
        <h3 id="b-agua">Agua y clima</h3>
        <dl className="cifras">
          <Cifra etiqueta="Agua de refrigeración" valor={num(s.agua_m3_anual)} unidad="m³/año" origen={<Origen tipo="demo" />}
            nota={`refrigeración ${REFRIGERACION[datos.parametros.tipo_refrigeracion] ?? datos.parametros.tipo_refrigeracion}, WUE ${num(datos.parametros.wue_l_kwh, 1)} l/kWh`} />
          <Cifra etiqueta="Estrés hídrico" valor={num(estres, 2)} unidad="índice 0–1" origen={origenDemo}
            nota={<Indice valor={estres} umbral={umbralEstres} etiquetaUmbral={`umbral ${num(umbralEstres, 1)}`} />} />
          <Cifra etiqueta="Temperatura media anual" valor={num(e.temp_media_c, 1)} unidad="°C" origen={origenDemo} />
          <Cifra etiqueta="Máxima histórica" valor={num(e.temp_max_hist_c, 1)} unidad="°C" origen={origenDemo} />
          <Cifra etiqueta="PUE aplicado" valor={num(s.pue_aplicado, 2)} origen={origenDemo}
            nota="energía total / energía de TI; cuanto más frío, menor" />
        </dl>
        <BloqueClimaVivo actual={p.actual} capital={p.meta.capital} vivo={p.tiempo} />
      </section>

      <section className="bloque" aria-labelledby="b-red">
        <h3 id="b-red">Red, conexión y entorno</h3>
        <dl className="cifras">
          <Cifra etiqueta="Latencia (ida y vuelta)" valor={num(s.latencia_rtt_ms, 2)} unidad="ms" origen={origenDemo}
            nota={`máximo aceptado ${num(datos.parametros.latencia_max_ms)} ms`} />
          <Cifra etiqueta="Subestación más cercana" valor={num(e.dist_subestacion_km, 1)} unidad={`km · ${num(e.tension_subestacion_kv)} kV`} origen={origenDemo} />
          <Cifra etiqueta="Capacidad de acceso" valor={num(e.capacidad_acceso_mw)} unidad="MW" origen={origenDemo}
            nota={`el CPD necesita ${num(s.potencia_total_mw, 1)} MW con refrigeración`} />
          <Cifra etiqueta="Cobertura de fibra" valor={num(e.cobertura_fibra_pct)} unidad="%" origen={origenDemo} />
          <Cifra etiqueta="Peligrosidad sísmica" valor={num(e.peligrosidad_sismica_g, 2)} unidad="g" origen={origenDemo} />
          <Cifra etiqueta="Suelo industrial libre" valor={num(e.suelo_industrial_ha)} unidad={`ha · ${num(e.precio_suelo_eur_m2)} €/m²`} origen={origenDemo} />
          <Cifra etiqueta="Emisiones del CPD" valor={num(s.co2_t)} unidad="t CO₂/año" origen={origenDemo}
            nota={`con ${pct(datos.parametros.pct_renovable)} de energía renovable contratada`} />
          {s.impacto_local_pct != null && (
            <Cifra etiqueta="Peso sobre el consumo municipal" valor={num(s.impacto_local_pct, 0)} unidad="%" origen={origenDemo} />
          )}
        </dl>
      </section>

      <section className="bloque" aria-labelledby="b-sub">
        <h3 id="b-sub">
          Puntuación por bloque <span className="h-nota">0–100, comparado con los {datos.fuente.n_municipios} municipios analizados</span>
        </h3>
        <div className="medidores">
          {BLOQUES.map((b) => (
            <Medidor key={b} etiqueta={NOMBRE_BLOQUE[b]} valor={m.sub[b]} peso={datos.pesos[b]} />
          ))}
        </div>
      </section>
    </>
  );
}

function BloqueLuz(p: Props & { m: Municipio | undefined }) {
  const { precios, demanda, mix, datos, m } = p;
  const pr = precios.datos;
  const ref = datos.precios.precio_electricidad_eur_mwh;
  const mediaHoy = pr?.spotMediaHoy ?? null;
  const recalculo = m && mediaHoy != null ? recalcularConPrecio(m, mediaHoy, datos) : null;
  return (
    <section className="bloque" aria-labelledby="b-luz">
      <h3 id="b-luz">
        Luz <span className="h-nota">precio y red: nacional (sistema peninsular), igual para todas las provincias</span>
      </h3>
      <dl className="cifras">
        <Cifra etiqueta="Precio que usa el modelo" valor={num(ref)} unidad="€/MWh" origen={<span className="origen">Supuesto</span>} />
        <Cifra
          etiqueta="Spot ahora"
          valor={pr?.spotAhora ? <Flap texto={num(pr.spotAhora.v, 1)} /> : "—"}
          unidad="€/MWh"
          origen={precios.error && !pr ? <Origen tipo="error" /> : <Origen tipo="vivo" momento={pr?.spotAhora?.t} fuente="REData" />}
        />
        <Cifra etiqueta="Media spot de hoy" valor={num(mediaHoy, 1)} unidad="€/MWh" origen={pr ? <Origen tipo="vivo" momento={precios.actualizado} /> : undefined}
          nota={pr?.spotMediaManana != null ? `mañana: ${num(pr.spotMediaManana, 1)} €/MWh` : undefined} />
        <Cifra etiqueta="Demanda peninsular" valor={num(demanda.datos?.ahora?.v)} unidad="MW"
          origen={demanda.error && !demanda.datos ? <Origen tipo="error" /> : <Origen tipo="vivo" momento={demanda.datos?.ahora?.t} />} />
        <Cifra etiqueta="Renovable ayer" valor={pct(mix.datos?.renovableAyer?.v)} origen={mix.datos ? <Origen tipo="vivo" momento={mix.actualizado} /> : mix.error ? <Origen tipo="error" /> : undefined}
          nota={mix.datos?.factorCo2Ayer ? `red: ${num(mix.datos.factorCo2Ayer.v, 3)} t CO₂ por MWh` : undefined} />
      </dl>
      {pr && <GraficoPrecio serie={pr.spot} referencia={ref} ahora={Date.now()} />}
      {precios.error && !pr && (
        <p className="aviso-vivo">
          No se ha podido leer el precio en directo de Red Eléctrica ({precios.error}). Las cifras usan el precio del
          modelo, {num(ref)} €/MWh. <button type="button" onClick={precios.reintentar}>Reintentar</button>
        </p>
      )}
      {recalculo && m && (
        <div className="recalculo">
          <p>
            <strong>Si todo el año la luz costara como hoy</strong> ({num(mediaHoy, 1)} €/MWh de media en lugar de {num(ref)}):
          </p>
          <dl className="cifras cifras-compactas">
            <Cifra etiqueta="Factura eléctrica" valor={millones(recalculo.coste_energia_eur)} unidad="/año" nota={`modelo: ${millones(m.salidas.coste_energia_eur)}`} />
            <Cifra etiqueta="OPEX" valor={millones(recalculo.opex_eur)} unidad="/año" nota={`modelo: ${millones(m.salidas.opex_eur)}`} />
            <Cifra etiqueta="VAN" valor={millones(recalculo.van_eur)} nota={`modelo: ${millones(m.salidas.van_eur)}`} />
            <Cifra etiqueta="Recuperación" valor={recalculo.payback_anos == null ? "no se recupera" : `${num(recalculo.payback_anos, 1)} años`}
              nota={`modelo: ${m.salidas.payback_anos == null ? "no se recupera" : `${num(m.salidas.payback_anos, 1)} años`}`} />
          </dl>
          <p className="nota">
            Mismas fórmulas que el modelo de Python; solo cambia el precio. El {pct(datos.precios.repercusion_energia_pct)} del
            coste eléctrico se repercute al cliente (colocation), por eso el efecto en el VAN es menor que en la factura.
          </p>
        </div>
      )}
    </section>
  );
}

function BloqueClimaVivo({ actual: tiempo, capital, vivo: t }: { actual: TiempoActual | undefined; capital: string; vivo: EnVivo<Record<string, TiempoActual>> }) {
  if (!tiempo) {
    return (
      <div className="vivo-clima">
        <p className="vivo-clima-t">Ahora en {capital}</p>
        <p className="aviso-vivo">
          {t.cargando ? "Cargando el tiempo actual…" : `Sin conexión con Open-Meteo${t.error ? ` (${t.error})` : ""}.`}
          {!t.cargando && (
            <>
              {" "}
              <button type="button" onClick={t.reintentar}>Reintentar</button>
            </>
          )}
        </p>
      </div>
    );
  }
  const libre = tiempo.temperatura_c < UMBRAL_FREE_COOLING_C;
  return (
    <div className="vivo-clima">
      <p className="vivo-clima-t">
        Ahora en {capital} <Origen tipo="vivo" momento={tiempo.hora} fuente="Open-Meteo" />
      </p>
      <dl className="cifras cifras-compactas">
        <Cifra etiqueta="Temperatura" valor={<Flap texto={num(tiempo.temperatura_c, 1)} />} unidad="°C" />
        <Cifra etiqueta="Humedad" valor={num(tiempo.humedad_pct)} unidad="%" />
        <Cifra etiqueta="Viento" valor={num(tiempo.viento_kmh)} unidad="km/h" />
        <Cifra
          etiqueta="Free cooling"
          valor={libre ? "Sí, ahora" : "No, ahora"}
          nota={`con aire exterior por debajo de ${UMBRAL_FREE_COOLING_C} °C se enfría sin compresores`}
        />
      </dl>
      <p className="nota">Medido el {diaHora(tiempo.hora)} en la capital de la provincia.</p>
    </div>
  );
}
