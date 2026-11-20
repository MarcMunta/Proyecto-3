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
