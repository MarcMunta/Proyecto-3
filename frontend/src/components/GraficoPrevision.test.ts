import { describe, expect, it } from "vitest";
import { ejeRedondo } from "./GraficoPrevision";

describe("ejeRedondo", () => {
  it("cubre el rango con marcas redondas (1, 2 o 5 × 10ⁿ)", () => {
    const eje = ejeRedondo(13, 287);
    expect(eje.inicio).toBeLessThanOrEqual(13);
    expect(eje.fin).toBeGreaterThanOrEqual(287);
    expect(eje.marcas).toEqual([0, 100, 200, 300]);
    expect(eje.decimales).toBe(0);
  });

  it("da decimales cuando el paso es menor que 1", () => {
    const eje = ejeRedondo(0.31, 1.27);
    expect(eje.marcas[0]).toBeLessThanOrEqual(0.31);
    expect(eje.marcas[eje.marcas.length - 1]).toBeGreaterThanOrEqual(1.27);
    expect(eje.decimales).toBe(1);
  });

  it("no se rompe con una serie plana", () => {
    const eje = ejeRedondo(50, 50);
    expect(eje.marcas.length).toBeGreaterThan(0);
    expect(eje.marcas.every(Number.isFinite)).toBe(true);
  });
});

describe("ejeRedondo con valores bajo cero", () => {
  it("baja de 0 cuando la serie tiene negativos (temperaturas)", () => {
    const eje = ejeRedondo(-1.2, 28.4);
    expect(eje.inicio).toBeLessThanOrEqual(-1.2);
    expect(eje.fin).toBeGreaterThanOrEqual(28.4);
    expect(eje.marcas).toContain(0);
  });
});
