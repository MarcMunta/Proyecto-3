import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { normalizarDatosApis } from "./datosApis";
import { fecha } from "../components/CatalogoDatos";

const real = JSON.parse(readFileSync(new URL("../../public/data/datos.json", import.meta.url), "utf8")) as unknown;

describe("panel de datos y APIs", () => {
  it("acepta el datos.json generado por Python con fuentes, base de datos y capas", () => {
    const datos = normalizarDatosApis(real);
    expect(datos).not.toBeNull();
    expect(datos!.apis.length).toBe(datos!.kpis.fuentes);
    expect(datos!.apis.every((a) => a.dominio && a.url_ejemplo?.startsWith("http"))).toBe(true);
    expect(datos!.capas.map((c) => c.capa)).toEqual(["bronze", "silver", "gold"]);
    expect(new Set(datos!.bbdd.objetos.map((o) => o.esquema))).toEqual(new Set(["dw", "fuentes", "gold", "meta", "modelo"]));
  });

  it("rechaza ficheros sin la forma esperada", () => {
    expect(normalizarDatosApis(null)).toBeNull();
    expect(normalizarDatosApis([])).toBeNull();
    expect(normalizarDatosApis({ kpis: {}, apis: [] })).toBeNull();
    const sinBbdd = { ...(real as Record<string, unknown>), bbdd: undefined };
    expect(normalizarDatosApis(sinBbdd)).toBeNull();
  });

  it("muestra las fechas en formato español", () => {
    expect(fecha("2026-11-18T17:43:48")).toBe("18/11/2026 17:43");
    expect(fecha("2026-11-18", false)).toBe("18/11/2026");
    expect(fecha(null)).toBe("—");
  });
});
