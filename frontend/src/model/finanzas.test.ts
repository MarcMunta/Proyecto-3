import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { Viabilidad } from "../data/types";
import { recalcularConPrecio, tipoMotivo } from "./finanzas";

const datos = JSON.parse(
  readFileSync(new URL("../../public/data/viabilidad.json", import.meta.url), "utf8"),
) as Viabilidad;

const cerca = (a: number | null, b: number | null) => {
  if (a == null || b == null) return expect(a).toBe(b);
  expect(Math.abs(a - b)).toBeLessThanOrEqual(Math.max(1, Math.abs(b) * 1e-6));
};

describe("recalcularConPrecio", () => {
  it("con el precio del modelo reproduce exactamente las cifras de Python", () => {
    const precio = datos.precios.precio_electricidad_eur_mwh;
    expect(datos.municipios.length).toBeGreaterThan(0);
    for (const m of datos.municipios) {
      const r = recalcularConPrecio(m, precio, datos)!;
      cerca(r.coste_energia_eur, m.salidas.coste_energia_eur);
      cerca(r.opex_eur, m.salidas.opex_eur);
      cerca(r.ingresos_anuales_eur, m.salidas.ingresos_anuales_eur);
      cerca(r.van_eur, m.salidas.van_eur);
      if (m.salidas.roi != null) expect(r.roi!).toBeCloseTo(m.salidas.roi, 6);
      if (m.salidas.payback_anos == null) expect(r.payback_anos).toBeNull();
      else expect(r.payback_anos!).toBeCloseTo(m.salidas.payback_anos, 6);
    }
  });

  it("una luz más cara baja el VAN", () => {
    const m = datos.municipios[0]!;
    const base = recalcularConPrecio(m, 75, datos)!;
    const cara = recalcularConPrecio(m, 150, datos)!;
    expect(cara.van_eur).toBeLessThan(base.van_eur);
    expect(cara.opex_eur).toBeGreaterThan(base.opex_eur);
  });
});

describe("tipoMotivo", () => {
  it("clasifica los textos del embudo", () => {
    expect(tipoMotivo("Zona inundable (M5): exclusión por riesgo de inundación", "No viable")).toBe("ko");
    expect(tipoMotivo("Peligrosidad sísmica 0.18 g >= 0.16 g: diseño sísmico reforzado (M5)", "No viable")).toBe("condicion");
    expect(tipoMotivo("Aviso: datos ausentes (x)", "Viable")).toBe("aviso");
    expect(tipoMotivo("Cumple todos los filtros eliminatorios (M1, M3, M4, M5, M6)", "Viable")).toBe("ok");
  });
});
