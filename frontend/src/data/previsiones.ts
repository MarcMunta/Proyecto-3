/**
 * Previsión a 1 año (python -m cpd.modelos → data/curated/modelos/previsiones_1_anio.json, que npm run data copia
 * a public/data/previsiones.json): precio de la luz nacional, demanda eléctrica de cada comunidad, reservas de agua de
 * cada ámbito y temperatura media de cada provincia, mes a mes.
 */

export interface PuntoMes {
  /** AAAA-MM */
  mes: string;
  valor: number;
}

export interface PuntoPrevision extends PuntoMes {
  inferior: number | null;
  superior: number | null;
}

export interface SeriePrevista {
  modelo: string;
  miembros: string[];
  /** Error medio a 1 año del modelo en validación y test (MAPE en %, o MAE en la unidad de la serie). */
  errorValidacion: number | null;
  errorTest: number | null;
  /** Acierto (100 − WAPE, %) en validación y test, y si cumple el requisito (85 % ≤ acierto < 99,9 %). */
  aciertoValidacion: number | null;
  aciertoTest: number | null;
  historia: PuntoMes[];
  prevision: PuntoPrevision[];
}

export interface TemperaturaPrevista extends SeriePrevista {
  nombre: string;
  /** Media (°C) de los últimos 12 meses reales y de los 12 meses previstos, con su intervalo 10-90 %. */
  media12m: number | null;
  mediaPrevista: number | null;
  mediaInferior: number | null;
  mediaSuperior: number | null;
}

export interface RenovablePrevista extends TemperaturaPrevista {
  /** Acierto (100 − WAPE, %) de la media de los 12 meses previstos, en validación y test. */
  aciertoAnualValidacion: number | null;
  aciertoAnualTest: number | null;
}

export interface OperacionPrevista {
  pue: number | null;
  consumoMwh: number | null;
  /** t CO2/año con el mix de generación de su comunidad: previstas y del último año. */
  emisionesT: number | null;
  emisionesActualT: number | null;
  /** Reserva mínima prevista de los embalses del ámbito en los 12 meses siguientes (%) y su mes (AAAA-MM). */
  reservaMinimaPct: number | null;
  mesReservaMinima: string | null;
  /** Acierto de punta a punta (100 − WAPE, %) del consumo y de las emisiones anuales. */
  aciertoConsumo: number | null;
  aciertoEmisiones: number | null;
}

export interface ImpactoLocal {
  /** % del consumo previsto del CPD sobre la demanda eléctrica prevista de su comunidad, y habitantes equivalentes. */
  pctDemanda: number | null;
  habitantesElectricidad: number | null;
  /** % de la capacidad de acceso libre de la red de su comunidad que ocuparía la potencia máxima del CPD. */
  pctCapacidad: number | null;
  capacidadLibreMw: number | null;
  sinCapacidadLibre: boolean;
  /** % del agua distribuida por la red pública de su comunidad (INE) y habitantes equivalentes. */
  pctAgua: number | null;
  habitantesAgua: number | null;
  anioAgua: number | null;
  /** Acierto de punta a punta (100 − WAPE, %) del % eléctrico. */
  acierto: number | null;
}

export interface Socioeconomico {
  /** Construcción (una vez): empleos-año y M€ del CAPEX que se quedan en España. */
  empleoObra: number | null;
  inversionEspanaMeur: number | null;
  /** Operación (cada año): plantilla, empleo en proveedores, VAB total (M€) y multiplicador de empleo. */
  empleoDirecto: number | null;
  empleoIndirecto: number | null;
  vabTotalMeur: number | null;
  multiplicador: number | null;
  anioPib: number | null;
  /** Por provincia: VAB directo / PIB provincial (%) y empleo directo / paro registrado (%). */
  provincias: Map<string, { pctPib: number | null; pctParoDirecto: number | null }>;
}

export interface MedioPlazo {
  /** Año de la previsión (el décimo tras el último año completo). */
  anioFinal: number;
  /** Temperatura media anual (°C): media de los últimos 10 años y prevista para el año final, con intervalo 10-90 %. */
  temp10a: number | null;
  tempFinal: number | null;
  tempInferior: number | null;
  tempSuperior: number | null;
  pue10a: number | null;
  pueFinal: number | null;
  cambioConsumoPct: number | null;
  /** Reserva media prevista de los embalses del ámbito en la próxima década (%). */
  reservaDecadaPct: number | null;
  ambito: string | null;
  /** Diagnóstico de la temperatura en el décimo año, medido en el periodo de test. */
  maeTemperaturaFinal: number | null;
  coberturaTemperaturaFinalPct: number | null;
  aciertoReservaDecadaTest: number | null;
}

export interface EvaluacionModelo {
  modelo: string;
  estado: string;
  definicion: string | null;
  aciertoValidacion: number | null;
  aciertoTest: number | null;
  metodo: { nombre: string; miembros: string[] } | null;
}

export interface Previsiones {
  generado: string | null;
  precio: (SeriePrevista & {
    mediaPrevista: number | null;
    futuroGasAnio: number | null;
    aciertoAnualValidacion: number | null;
    aciertoAnualTest: number | null;
  }) | null;
  /** Por código INE de comunidad (dos dígitos). */
  demanda: Map<string, SeriePrevista & { nombre: string }>;
  demandaModelo: { modelo: string; miembros: string[]; errorValidacion: number | null; errorTest: number | null } | null;
  /** Reserva de los embalses por ámbito hidrográfico (%). */
  reservas: Map<string, SeriePrevista>;
  /** Temperatura media mensual (°C) por código INE de provincia, y la media del último año y de los 12 meses previstos. */
  temperatura: Map<string, TemperaturaPrevista>;
  /** % de generación renovable mensual por código INE de comunidad, con el acierto de la media de 12 meses. */
  renovables: Map<string, RenovablePrevista>;
  /** Operación prevista del CPD de referencia en los 12 meses siguientes, por código INE de provincia (objetivo A3). */
  operacion: Map<string, OperacionPrevista>;
  /** Demanda nacional anual (TWh): historia y previsión a 10 años (`mes` = «AAAA-01»). */
  demanda10: (SeriePrevista & { acierto: number | null }) | null;
  /** Clima y agua a 10 años para la operación del CPD, por código INE de provincia (objetivo A3, medio plazo). */
  medioPlazo: Map<string, MedioPlazo>;
  /** Impacto previsto del CPD sobre la electricidad, la red y el agua de su comunidad, por provincia (P2). */
  impacto: Map<string, ImpactoLocal>;
  /** Empleo, inversión inducida y PIB (tablas input-output del INE; E39-E41). */
  socioeconomico: Socioeconomico | null;
  /** Atracción empresarial (E42): sociedades creadas al año por 10.000 habitantes, previstas, y aciertos del total anual. */
  empresas: {
    hasta: string | null;
    aciertoAnualTest: number | null;
    provincias: Map<string, { por10000: number | null; cambioPct: number | null }>;
  } | null;
  /** Energía de la red otorgada y en trámite frente a la demanda actual de cada comunidad (%), escenarios P5. */
  redOtorgada: Map<string, { pctOtorgada: number | null; pctPendiente: number | null; factor: number | null }>;
  /** Requisito de acierto por modelo. */
  control: EvaluacionModelo[];
  escenarioDemanda: { mwOtorgados: number | null; factor: number | null; twhOtorgados: number | null } | null;
}

/** Mínimo de acierto exigido a los modelos (cpd.modelos.metricas.ACIERTO_MINIMO). */
export const ACIERTO_MINIMO = 85;

const numero = (v: unknown): number | null => {
  const n = typeof v === "number" ? v : typeof v === "string" && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
};
const texto = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v.trim() : null);
const esMes = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}$/.test(v);

function puntos(v: unknown): PuntoMes[] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((p) => {
    const valor = numero((p as Record<string, unknown>)?.valor);
    const mes = (p as Record<string, unknown>)?.mes;
    return esMes(mes) && valor != null ? [{ mes, valor }] : [];
  });
}

function puntosPrevision(v: unknown): PuntoPrevision[] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((p) => {
    const fila = p as Record<string, unknown>;
    const valor = numero(fila?.valor);
    return esMes(fila?.mes) && valor != null ? [{ mes: fila.mes, valor, inferior: numero(fila.inferior), superior: numero(fila.superior) }] : [];
  });
}

const miembros = (v: unknown): string[] => (Array.isArray(v) ? v.filter((m): m is string => typeof m === "string") : []);

/** Valida el JSON de previsiones; lo que no tenga forma válida se descarta (nunca se rellena). */
export function normalizarPrevisiones(json: unknown): Previsiones | null {
  if (!json || typeof json !== "object") return null;
  const raiz = json as Record<string, Record<string, unknown> | undefined>;
  const p = raiz.precio;
  const precio =
    p && texto(p.modelo)
      ? {
          modelo: texto(p.modelo)!,
          miembros: miembros(p.miembros),
          errorValidacion: numero(p.error_validacion),
          errorTest: numero(p.error_test),
          aciertoValidacion: numero(p.acierto_validacion),
          aciertoTest: numero(p.acierto_test),
          historia: puntos(p.historia),
          prevision: puntosPrevision(p.prevision),
          mediaPrevista: numero(p.media_prevista),
          futuroGasAnio: numero(p.futuro_gas_anio),
          aciertoAnualValidacion: numero(p.acierto_anual_validacion),
          aciertoAnualTest: numero(p.acierto_anual_test),
        }
      : null;
  const d = raiz.demanda;
  const demanda = new Map<string, SeriePrevista & { nombre: string }>();
  let demandaModelo: Previsiones["demandaModelo"] = null;
  if (d && texto(d.modelo)) {
    demandaModelo = { modelo: texto(d.modelo)!, miembros: miembros(d.miembros), errorValidacion: numero(d.error_validacion), errorTest: numero(d.error_test) };
    const porCcaa = d.ccaa && typeof d.ccaa === "object" ? (d.ccaa as Record<string, Record<string, unknown>>) : {};
    for (const [codigo, c] of Object.entries(porCcaa)) {
      if (!/^\d{2}$/.test(codigo) || !c) continue;
      const prevision = puntosPrevision(c.prevision);
      if (!prevision.length) continue;
      demanda.set(codigo, { ...demandaModelo, aciertoValidacion: numero(d.acierto_validacion), aciertoTest: numero(d.acierto_test), nombre: texto(c.nombre) ?? codigo, historia: puntos(c.historia), prevision });
    }
  }
  const reservas = new Map<string, SeriePrevista>();
  const r = raiz.reservas;
  if (r && texto(r.modelo)) {
    const porAmbito = r.ambitos && typeof r.ambitos === "object" ? (r.ambitos as Record<string, Record<string, unknown>>) : {};
    for (const [ambito, a] of Object.entries(porAmbito)) {
      const prevision = puntosPrevision(a?.prevision);
      if (!prevision.length) continue;
      reservas.set(ambito, {
        modelo: texto(r.modelo)!, miembros: miembros(r.miembros), errorValidacion: numero(r.error_validacion), errorTest: numero(r.error_test),
        aciertoValidacion: numero(r.acierto_validacion), aciertoTest: numero(r.acierto_test), historia: puntos(a.historia), prevision,
      });
    }
  }
  const temperatura = new Map<string, TemperaturaPrevista>();
  const t = raiz.temperatura;
  if (t && texto(t.modelo)) {
    const porProvincia = t.provincias && typeof t.provincias === "object" ? (t.provincias as Record<string, Record<string, unknown>>) : {};
    for (const [codigo, a] of Object.entries(porProvincia)) {
      const prevision = puntosPrevision(a?.prevision);
      if (!/^\d{2}$/.test(codigo) || !prevision.length) continue;
      temperatura.set(codigo, {
        modelo: texto(t.modelo)!, miembros: miembros(t.miembros), errorValidacion: numero(t.error_validacion), errorTest: numero(t.error_test),
        aciertoValidacion: numero(t.acierto_validacion), aciertoTest: numero(t.acierto_test), historia: puntos(a.historia), prevision,
        nombre: texto(a.nombre) ?? codigo, media12m: numero(a.media_12m_actual), mediaPrevista: numero(a.media_prevista),
        mediaInferior: numero(a.media_inferior), mediaSuperior: numero(a.media_superior),
      });
    }
  }
  const renovables = new Map<string, RenovablePrevista>();
  const v = raiz.renovables;
  if (v && texto(v.modelo)) {
    const porCcaa = v.ccaa && typeof v.ccaa === "object" ? (v.ccaa as Record<string, Record<string, unknown>>) : {};
    for (const [codigo, a] of Object.entries(porCcaa)) {
      const prevision = puntosPrevision(a?.prevision);
      if (!/^\d{2}$/.test(codigo) || !prevision.length) continue;
      renovables.set(codigo, {
        modelo: texto(v.modelo)!, miembros: miembros(v.miembros), errorValidacion: numero(v.error_validacion), errorTest: numero(v.error_test),
        aciertoValidacion: numero(v.acierto_validacion), aciertoTest: numero(v.acierto_test), historia: puntos(a.historia), prevision,
        nombre: texto(a.nombre) ?? codigo, media12m: numero(a.media_12m_actual), mediaPrevista: numero(a.media_prevista),
        mediaInferior: numero(a.media_inferior), mediaSuperior: numero(a.media_superior),
        aciertoAnualValidacion: numero(v.acierto_anual_validacion), aciertoAnualTest: numero(v.acierto_anual_test),
      });
    }
  }
  const operacion = new Map<string, OperacionPrevista>();
  const o = raiz.operacion;
  if (o && o.provincias && typeof o.provincias === "object") {
    for (const [codigo, f] of Object.entries(o.provincias as Record<string, Record<string, unknown>>)) {
      if (!/^\d{2}$/.test(codigo) || !f) continue;
      operacion.set(codigo, {
        pue: numero(f.pue_previsto), consumoMwh: numero(f.consumo_previsto_mwh), emisionesT: numero(f.emisiones_previsto_t),
        emisionesActualT: numero(f.emisiones_actual_t), reservaMinimaPct: numero(f.reserva_minima_prevista_pct),
        mesReservaMinima: esMes(f.mes_reserva_minima) ? f.mes_reserva_minima : null,
        aciertoConsumo: numero(o.acierto_consumo), aciertoEmisiones: numero(o.acierto_emisiones),
      });
    }
  }
  const diez = raiz.demanda_10_anios;
  const anual = (v: unknown) =>
    Array.isArray(v) ? v.map((x) => ({ ...(x as Record<string, unknown>), mes: `${(x as Record<string, unknown>)?.anio}-01` })) : [];
  const demanda10 =
    diez && texto(diez.modelo)
      ? {
          modelo: texto(diez.modelo)!, miembros: miembros(diez.miembros), errorValidacion: numero(diez.mape_medio), errorTest: null,
          aciertoValidacion: numero(diez.acierto), aciertoTest: null, acierto: numero(diez.acierto),
          historia: puntos(anual(diez.historia)), prevision: puntosPrevision(anual(diez.prevision)),
        }
      : null;
  const medioPlazo = new Map<string, MedioPlazo>();
  const mp = raiz.medio_plazo;
  const anioFinal = numero(mp?.anio_final);
  if (mp && anioFinal != null && mp.provincias && typeof mp.provincias === "object") {
    const t10 = (mp.temperatura ?? {}) as Record<string, unknown>;
    const r10 = (mp.reservas ?? {}) as Record<string, unknown>;
    const diagnostico = Array.isArray(t10.diagnosticos_horizonte)
      ? t10.diagnosticos_horizonte.find((d) => d?.particion === "test" && d.horizonte_anios === 10)
      : null;
    for (const [codigo, f] of Object.entries(mp.provincias as Record<string, Record<string, unknown>>)) {
      if (!/^\d{2}$/.test(codigo) || !f) continue;
      medioPlazo.set(codigo, {
        anioFinal, temp10a: numero(f.temp_10a_c), tempFinal: numero(f.temp_final_c), tempInferior: numero(f.temp_final_inferior_c),
        tempSuperior: numero(f.temp_final_superior_c), pue10a: numero(f.pue_10a), pueFinal: numero(f.pue_final),
        cambioConsumoPct: numero(f.cambio_consumo_pct), reservaDecadaPct: numero(f.reserva_decada_prevista_pct), ambito: texto(f.ambito),
        maeTemperaturaFinal: numero(diagnostico?.mae),
        coberturaTemperaturaFinalPct: numero(diagnostico?.cobertura_banda_10_90_pct),
        aciertoReservaDecadaTest: numero(r10.acierto_decada_test),
      });
    }
  }
  const impacto = new Map<string, ImpactoLocal>();
  const il = raiz.impacto_local;
  if (il && il.provincias && typeof il.provincias === "object") {
    for (const [codigo, f] of Object.entries(il.provincias as Record<string, Record<string, unknown>>)) {
      if (!/^\d{2}$/.test(codigo) || !f) continue;
      impacto.set(codigo, {
        pctDemanda: numero(f.pct_demanda_ccaa), habitantesElectricidad: numero(f.habitantes_eq_electricidad),
        pctCapacidad: numero(f.pct_capacidad_disponible), capacidadLibreMw: numero(f.capacidad_disponible_mw),
        sinCapacidadLibre: f.sin_capacidad_libre === true, pctAgua: numero(f.pct_agua_ccaa), habitantesAgua: numero(f.habitantes_eq_agua),
        anioAgua: numero(il.anio_agua), acierto: numero(il.acierto_validacion),
      });
    }
  }
  let socioeconomico: Socioeconomico | null = null;
  const se = raiz.impacto_socioeconomico;
  if (se && se.operacion && typeof se.operacion === "object") {
    const op = se.operacion as Record<string, Record<string, unknown> | unknown>;
    const obra = (se.construccion ?? {}) as Record<string, unknown>;
    const dir = (op.directo ?? {}) as Record<string, unknown>;
    const ind = (op.indirecto ?? {}) as Record<string, unknown>;
    const provincias = new Map<string, { pctPib: number | null; pctParoDirecto: number | null }>();
    if (se.provincias && typeof se.provincias === "object") {
      for (const [codigo, f] of Object.entries(se.provincias as Record<string, Record<string, unknown>>)) {
        if (/^\d{2}$/.test(codigo) && f) provincias.set(codigo, { pctPib: numero(f.pct_pib), pctParoDirecto: numero(f.pct_paro_directo) });
      }
    }
    socioeconomico = {
      empleoObra: numero(obra.empleo_anio), inversionEspanaMeur: numero(obra.en_espana_meur), empleoDirecto: numero(dir.empleo_etc),
      empleoIndirecto: numero(ind.empleo_etc), vabTotalMeur: numero(op.vab_total_meur), multiplicador: numero(op.multiplicador_empleo),
      anioPib: numero(se.anio_pib), provincias,
    };
  }
  let empresas: Previsiones["empresas"] = null;
  const em = raiz.empresas;
  if (em && em.provincias && typeof em.provincias === "object") {
    const provincias = new Map<string, { por10000: number | null; cambioPct: number | null }>();
    for (const [codigo, f] of Object.entries(em.provincias as Record<string, Record<string, unknown>>)) {
      if (/^\d{2}$/.test(codigo) && f) provincias.set(codigo, { por10000: numero(f.por_10000_hab), cambioPct: numero(f.cambio_pct) });
    }
    empresas = { hasta: esMes(em.hasta) ? em.hasta : null, aciertoAnualTest: numero(em.acierto_anual_test), provincias };
  }
  const redOtorgada = new Map<string, { pctOtorgada: number | null; pctPendiente: number | null; factor: number | null }>();
  const es = raiz.escenarios_demanda;
  if (es && es.ccaa && typeof es.ccaa === "object") {
    for (const [codigo, f] of Object.entries(es.ccaa as Record<string, Record<string, unknown>>)) {
      if (/^\d{2}$/.test(codigo) && f) {
        redOtorgada.set(codigo, { pctOtorgada: numero(f.pct_otorgada), pctPendiente: numero(f.pct_pendiente), factor: numero(es.factor_utilizacion) });
      }
    }
  }
  const gasTiempo = raiz.gas_tiempo?.modelos as Record<string, Record<string, unknown>> | undefined;
  const medioDatos = raiz.medio_plazo;
  const prefijos: [string, Record<string, unknown> | undefined][] = [
    ["Precio de la luz", p],
    ["Demanda por comunidad", d],
    ["Demanda nacional", raiz.demanda_10_anios],
    ["Reservas de agua a 1 año", r],
    ["Reservas de agua a 10 años", medioDatos?.reservas as Record<string, unknown> | undefined],
    ["Temperatura por provincia a 1 año", t],
    ["Temperatura por provincia a 10 años", medioDatos?.temperatura as Record<string, unknown> | undefined],
    ["Renovables por comunidad", raiz.renovables],
    ["Generación renovable", raiz.cobertura_renovable],
    ["Atracción empresarial", em],
    ["Gas natural", gasTiempo?.gas],
    ["Eólica de España", gasTiempo?.eolica],
    ["Solar de España", gasTiempo?.solar],
    ["Hidráulica de España", gasTiempo?.hidraulica],
  ];
  const filasControl = (json as Record<string, unknown>).control_acierto;
  const control = Array.isArray(filasControl) ? filasControl.flatMap((c): EvaluacionModelo[] => {
    const modelo = texto(c?.modelo);
    const estado = texto(c?.estado);
    if (!modelo || !estado) return [];
    const datos = prefijos.find(([prefijo]) => modelo.startsWith(prefijo))?.[1];
    const nombre = texto(datos?.modelo);
    return [{
      modelo, estado, definicion: texto(c.definicion),
      aciertoValidacion: numero(c.acierto_validacion), aciertoTest: numero(c.acierto_test),
      metodo: nombre ? { nombre, miembros: miembros(datos?.miembros) } : null,
    }];
  }) : [];
  const escenarioDemanda = es ? {
    mwOtorgados: numero(es.otorgada_mw), factor: numero(es.factor_utilizacion), twhOtorgados: numero(es.otorgada_twh_anio),
  } : null;
  if (!control.length && !precio && !demanda.size && !reservas.size && !temperatura.size && !renovables.size && !operacion.size && !demanda10 && !medioPlazo.size && !impacto.size && !socioeconomico && !redOtorgada.size && !empresas && !escenarioDemanda) return null;
  return {
    generado: texto((json as Record<string, unknown>).generado), precio, demanda, demandaModelo, reservas, temperatura, renovables, operacion,
    demanda10: demanda10?.prevision.length ? demanda10 : null, medioPlazo, impacto, socioeconomico, empresas, redOtorgada, control, escenarioDemanda,
  };
}
