import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import metaJson from "./provincias.json";
import { desdeDemo, normalizarReal } from "./prediccion";
import type { ProvinciaMeta, Viabilidad } from "./types";

const META = metaJson as ProvinciaMeta[];
const demo = JSON.parse(readFileSync(new URL("../../public/data/viabilidad.json", import.meta.url), "utf8")) as Viabilidad;

// Filas de PRUEBA con el formato del contrato (valores inventados solo para el test).
const filas = [
  { codigo_provincia: "28", provincia: "Madrid", ccaa: "Comunidad de Madrid", rentabilidad_clase: "alta", score_viabilidad: 81, estado: "Viable", van_eur: 1e7, roi: 0.5, payback_anos: 9, capex_eur: null, motivos: ["ok"], generado_en: "2026-11-20T10:00:00+01:00" },
  { codigo_provincia: 8, provincia: "Barcelona", rentabilidad_clase: "rara", score_viabilidad: "70", estado: "Quizá", van_eur: "no-num", motivos: "x" },
  { codigo_provincia: "99", provincia: "Nada" },
  null,
];

describe("normalizarReal", () => {
  it("normaliza códigos, deja en null lo ausente o inválido y descarta filas sin provincia", () => {
    const p = normalizarReal(filas, META)!;
    expect(p.tipo).toBe("real");
    expect([...p.provincias.keys()].sort()).toEqual(["08", "28"]);
    const mad = p.provincias.get("28")!;
    expect(mad.clase).toBe("alta");
    expect(mad.capex_eur).toBeNull();
    expect(mad.motivos).toEqual(["ok"]);
    const bcn = p.provincias.get("08")!;
    expect(bcn.clase).toBeNull();
    expect(bcn.estado).toBeNull();
    expect(bcn.score).toBe(70);
    expect(bcn.van_eur).toBeNull();
    expect(bcn.motivos).toEqual([]);
    expect(p.generado).toBe("2026-11-20T10:00:00+01:00");
  });

  it("devuelve null si el fichero no es una lista utilizable", () => {
    expect(normalizarReal({}, META)).toBeNull();
    expect(normalizarReal([], META)).toBeNull();
    expect(normalizarReal([{ codigo_provincia: "00" }], META)).toBeNull();
  });
});

describe("provincias_simuladas.json (simulación con datos reales, npm run data)", () => {
  const ruta = new URL("../../public/data/provincias_simuladas.json", import.meta.url);
  it.skipIf(!existsSync(ruta))("carga las 52 provincias, todas con clase, sin sello de demostración", () => {
    const p = normalizarReal(JSON.parse(readFileSync(ruta, "utf8")), META, "simulacion")!;
    expect(p.tipo).toBe("simulacion");
    expect(p.provincias.size).toBe(52);
    for (const prov of p.provincias.values()) {
      expect(prov.clase).not.toBeNull();
      expect(prov.van_eur).not.toBeNull();
    }
    expect(p.actualizado).toBeTruthy();
    expect(p.mesReferencia).toMatch(/^\d{4}-\d{2}$/);
  });
});

describe("desdeDemo", () => {
  it("da clase a cada provincia con datos: No viable = no rentable, el resto por tercios de VAN", () => {
    const p = desdeDemo(demo, META);
    expect(p.tipo).toBe("demo");
    expect(p.provincias.size).toBe(Object.keys(demo.provincias).length);
    for (const prov of p.provincias.values()) {
      expect(prov.clase).not.toBeNull();
      if (prov.estado === "No viable") expect(prov.clase).toBe("no_rentable");
      else expect(prov.clase).not.toBe("no_rentable");
    }
    const viables = [...p.provincias.values()].filter((x) => x.estado !== "No viable");
    const vanAlta = Math.min(...viables.filter((x) => x.clase === "alta").map((x) => x.van_eur!));
    const vanBaja = Math.max(...viables.filter((x) => x.clase === "baja").map((x) => x.van_eur!));
    expect(vanAlta).toBeGreaterThanOrEqual(vanBaja);
    expect(p.clasesMunicipio.size).toBe(demo.municipios.length);
  });
});
