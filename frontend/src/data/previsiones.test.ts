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
