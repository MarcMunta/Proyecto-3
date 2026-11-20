import { describe, expect, it } from "vitest";
import { normalizarPrevisiones } from "./previsiones";

describe("normalizarPrevisiones", () => {
  it("lee precio y demanda por comunidad y descarta lo que no tiene forma válida", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const json = {
      generado: "2026-11-17T19:00:00+01:00",
      precio: {
        modelo: "combinacion",
        miembros: ["ets", "naive", 3],
        error_validacion: 29,
        error_test: "30",
        historia: [{ mes: "2026-09", valor: 143 }, { mes: "2026-10", valor: 167 }, { mes: "mal", valor: 1 }],
        prevision: [{ mes: "2026-11", valor: 171, inferior: 120, superior: null }],
        media_prevista: 153,
      },
      demanda: {
        modelo: "combinacion",
        miembros: ["ets"],
        error_validacion: 3.9,
        error_test: 4.4,
        ccaa: {
          "13": { nombre: "Madrid", historia: [{ mes: "2026-06", valor: 2.5e6 }], prevision: [{ mes: "2026-07", valor: 2.6e6, inferior: 2.4e6, superior: 2.8e6 }] },
          "99x": { nombre: "Mal", prevision: [{ mes: "2026-07", valor: 1 }] },
          "05": { nombre: "Sin previsión", prevision: [] },
        },
      },
    };
    const p = normalizarPrevisiones(json)!;
    expect(p.precio?.miembros).toEqual(["ets", "naive"]);
    expect(p.precio?.errorTest).toBe(30);
    expect(p.precio?.historia).toHaveLength(2);
    expect(p.precio?.prevision[0]).toEqual({ mes: "2026-11", valor: 171, inferior: 120, superior: null });
    expect([...p.demanda.keys()]).toEqual(["13"]);
    expect(p.demanda.get("13")?.nombre).toBe("Madrid");
  });

  it("devuelve null si no hay nada utilizable", () => {
    expect(normalizarPrevisiones({})).toBeNull();
    expect(normalizarPrevisiones(null)).toBeNull();
  });
});

describe("reservas, demanda a 10 años y control de acierto", () => {
  it("lee las tres partes nuevas del JSON", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      reservas: { modelo: "combinacion", acierto_validacion: 86.7, acierto_test: 85.3, ambitos: { Tajo: { historia: [{ mes: "2026-10", valor: 57 }], prevision: [{ mes: "2026-11", valor: 56, inferior: 50, superior: 62 }] } } },
      demanda_10_anios: { modelo: "combinacion", acierto: 97.3, historia: [{ anio: 2025, valor: 256 }], prevision: [{ anio: 2035, valor: 244, inferior: 221, superior: 269 }] },
      control_acierto: [{ modelo: "Precio de la luz a 1 año", estado: "no cumple (< 85 %)" }, { estado: "sin modelo" }],
    })!;
    expect(p.reservas.get("Tajo")?.aciertoTest).toBe(85.3);
    expect(p.demanda10?.prevision[0]).toEqual({ mes: "2035-01", valor: 244, inferior: 221, superior: 269 });
    expect(p.demanda10?.acierto).toBe(97.3);
    expect(p.control).toEqual([{ modelo: "Precio de la luz a 1 año", estado: "no cumple (< 85 %)" }]);
  });
});

describe("temperatura por provincia", () => {
  it("lee la serie, la media prevista y descarta códigos que no son de provincia", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      temperatura: {
        modelo: "combinacion", acierto_validacion: 93.8, acierto_test: 92.8, error_test: 1.17,
        provincias: {
          "42": { nombre: "Soria", historia: [{ mes: "2026-01", valor: -0.3 }], prevision: [{ mes: "2026-11", valor: 6.1, inferior: 4.8, superior: 7.5 }], media_12m_actual: 11.2, media_prevista: 11.4, media_inferior: 10.8, media_superior: 12.0 },
          Soria: { prevision: [{ mes: "2026-11", valor: 6 }] },
        },
      },
    })!;
    expect(p.temperatura.size).toBe(1);
    const soria = p.temperatura.get("42")!;
    expect(soria.historia[0]?.valor).toBe(-0.3);
    expect(soria.mediaPrevista).toBe(11.4);
    expect([soria.mediaInferior, soria.mediaSuperior]).toEqual([10.8, 12]);
    expect(soria.aciertoTest).toBe(92.8);
  });
});

describe("renovables por comunidad", () => {
  it("lee el % previsto y el acierto de la media anual", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      renovables: {
        modelo: "combinacion", acierto_validacion: 84.3, acierto_test: 89.5, acierto_anual_validacion: 88.7, acierto_anual_test: 93.6,
        ccaa: { "07": { nombre: "Castilla y León", historia: [{ mes: "2026-08", valor: 90 }], prevision: [{ mes: "2026-09", valor: 88, inferior: 80, superior: 95 }], media_12m_actual: 91, media_prevista: 92, media_inferior: 88, media_superior: 96 } },
      },
    })!;
    const cyl = p.renovables.get("07")!;
    expect(cyl.nombre).toBe("Castilla y León");
    expect([cyl.aciertoValidacion, cyl.aciertoAnualValidacion, cyl.aciertoAnualTest]).toEqual([84.3, 88.7, 93.6]);
    expect(cyl.mediaPrevista).toBe(92);
  });
});

describe("operación del CPD", () => {
  it("lee la operación prevista por provincia y sus aciertos", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      operacion: {
        acierto_consumo: 99.6, acierto_emisiones: 88.1,
        provincias: { "50": { pue_previsto: 1.46, consumo_previsto_mwh: 511000, emisiones_previsto_t: 9000, emisiones_actual_t: 9500, reserva_minima_prevista_pct: 41.2, mes_reserva_minima: "2027-09" }, XX: { pue_previsto: 1 } },
      },
    })!;
    expect(p.operacion.size).toBe(1);
    expect(p.operacion.get("50")).toMatchObject({ pue: 1.46, emisionesT: 9000, reservaMinimaPct: 41.2, mesReservaMinima: "2027-09", aciertoEmisiones: 88.1 });
  });
});

describe("medio plazo (10 años)", () => {
  it("lee el clima y el agua a 10 años por provincia y descarta códigos no válidos", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      medio_plazo: {
        anio_final: 2035,
        temperatura: { acierto_test: 94.8 },
        reservas: { acierto_decada_test: 86.6 },
        provincias: {
          "50": { temp_10a_c: 15.4, temp_final_c: 15.7, temp_final_inferior_c: 15.1, temp_final_superior_c: 16.5, pue_10a: 1.3, pue_final: 1.31, cambio_consumo_pct: 0.4, ambito: "Ebro", reserva_decada_prevista_pct: 61.2 },
          XX: { temp_final_c: 1 },
        },
      },
    })!;
    expect(p.medioPlazo.size).toBe(1);
    expect(p.medioPlazo.get("50")).toMatchObject({ anioFinal: 2035, tempFinal: 15.7, pueFinal: 1.31, reservaDecadaPct: 61.2, ambito: "Ebro", aciertoTemperaturaTest: 94.8, aciertoReservaDecadaTest: 86.6 });
  });
});

describe("impacto local (P2)", () => {
  it("lee el impacto por provincia y marca la red sin capacidad libre", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      impacto_local: {
        acierto_validacion: 96.1, anio_agua: 2024,
        provincias: {
          "50": { pct_demanda_ccaa: 4.4, habitantes_eq_electricidad: 61300, pct_capacidad_disponible: 82, capacidad_disponible_mw: 89, sin_capacidad_libre: false, pct_agua_ccaa: 0.18, habitantes_eq_agua: 2470 },
          "28": { pct_demanda_ccaa: 1.7, pct_capacidad_disponible: null, capacidad_disponible_mw: 0, sin_capacidad_libre: true, pct_agua_ccaa: 0.04 },
          XX: { pct_demanda_ccaa: 1 },
        },
      },
    })!;
    expect(p.impacto.size).toBe(2);
    expect(p.impacto.get("50")).toMatchObject({ pctDemanda: 4.4, pctCapacidad: 82, capacidadLibreMw: 89, sinCapacidadLibre: false, pctAgua: 0.18, anioAgua: 2024, acierto: 96.1 });
    expect(p.impacto.get("28")).toMatchObject({ sinCapacidadLibre: true, pctCapacidad: null, capacidadLibreMw: 0 });
  });
});

describe("impacto socioeconómico (E39-E41)", () => {
  it("lee el empleo de la obra y de la operación y el peso en el PIB por provincia", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({
      impacto_socioeconomico: {
        anio_pib: 2024,
        construccion: { empleo_anio: 3400, en_espana_meur: 295 },
        operacion: { directo: { empleo_etc: 60 }, indirecto: { empleo_etc: 217 }, vab_total_meur: 78.2, multiplicador_empleo: 4.6 },
        provincias: { "42": { pct_pib: 1.54, pct_paro_directo: 2.2 }, XX: { pct_pib: 9 } },
      },
    })!;
    expect(p.socioeconomico).toMatchObject({ empleoObra: 3400, inversionEspanaMeur: 295, empleoDirecto: 60, empleoIndirecto: 217, multiplicador: 4.6, anioPib: 2024 });
    expect(p.socioeconomico!.provincias.size).toBe(1);
    expect(p.socioeconomico!.provincias.get("42")).toEqual({ pctPib: 1.54, pctParoDirecto: 2.2 });
  });
});

describe("escenarios de demanda (P5)", () => {
  it("lee el peso de la red otorgada sobre la demanda de cada comunidad", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({ escenarios_demanda: { factor_utilizacion: 0.8, ccaa: { "02": { pct_otorgada: 242.7, pct_pendiente: 200 }, X: {} } } })!;
    expect(p.redOtorgada.size).toBe(1);
    expect(p.redOtorgada.get("02")).toEqual({ pctOtorgada: 242.7, pctPendiente: 200, factor: 0.8 });
  });
});

describe("atracción empresarial (E42)", () => {
  it("lee las sociedades nuevas por 10.000 habitantes de cada provincia", () => {
    // Datos de PRUEBA (valores inventados solo para el test).
    const p = normalizarPrevisiones({ empresas: { hasta: "2025-12", acierto_anual_test: 92.6, provincias: { "50": { por_10000_hab: 20.4, cambio_pct: 3.1 }, X: {} } } })!;
    expect(p.empresas).toMatchObject({ hasta: "2025-12", aciertoAnualTest: 92.6 });
    expect(p.empresas!.provincias.get("50")).toEqual({ por10000: 20.4, cambioPct: 3.1 });
    expect(p.empresas!.provincias.size).toBe(1);
  });
});
