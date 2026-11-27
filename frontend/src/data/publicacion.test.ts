import { describe, expect, it } from "vitest";
import { EDAD_MAXIMA_PUBLICACION_MS, esVersionSegura, punteroObsoleto, validarFicheroPublicado, validarPunteroPublicacion } from "./publicacion";

describe("publicación versionada", () => {
  it("acepta un puntero y sus dos ficheros de la misma versión", () => {
    const puntero = validarPunteroPublicacion({ schema_version: 1, version: "2026-11-23T180000Z-a1b2", generado_en: "2026-11-23T18:00:00Z", origen_modelos: "regenerados", fecha_panel: "2026-10", avisos: ["Cobertura parcial"] });
    expect(puntero?.version).toBe("2026-11-23T180000Z-a1b2");
    expect(puntero?.avisos).toEqual(["Cobertura parcial"]);
    expect(validarFicheroPublicado({ schema_version: 1, version: puntero?.version, provincias: [] }, puntero!.version)).toBe(true);
  });

  it("rechaza rutas inseguras, esquemas desconocidos y mezclas de versiones", () => {
    expect(esVersionSegura("../../secreto")).toBe(false);
    expect(esVersionSegura("..")).toBe(false);
    expect(validarPunteroPublicacion({ schema_version: 2, version: "v1", generado_en: "ahora" })).toBeNull();
    expect(validarFicheroPublicado({ schema_version: 1, version: "v2" }, "v1")).toBe(false);
  });

  it("marca como obsoleto un puntero antiguo, futuro o sin fecha ISO válida", () => {
    const ahora = Date.parse("2026-11-23T12:00:00Z");
    const base = { schema_version: 1 as const, version: "v1", generado_en: "2026-11-23T11:00:00Z" };
    expect(punteroObsoleto(base, ahora)).toBe(false);
    expect(punteroObsoleto({ ...base, generado_en: new Date(ahora - EDAD_MAXIMA_PUBLICACION_MS - 1).toISOString() }, ahora)).toBe(true);
    expect(punteroObsoleto({ ...base, generado_en: "sin-fecha" }, ahora)).toBe(true);
    expect(punteroObsoleto({ ...base, generado_en: "2026-11-23T12:06:00Z" }, ahora)).toBe(true);
  });
});
