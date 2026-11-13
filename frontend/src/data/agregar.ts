import type { Agregado, EstadoMapa, Municipio, ProvinciaMeta, ResumenProvincia, Viabilidad } from "./types";

/** Score que representa a la provincia: el del mejor emplazamiento o la media de los analizados. */
export function scoreProvincia(
  r: ResumenProvincia | undefined,
  agregado: Agregado,
  porIne: Map<string, Municipio>,
): number | null {
  if (!r) return null;
  if (agregado === "media") return r.score_medio;
  return porIne.get(r.mejor)?.score_global ?? r.score_max;
}

export interface FilaTablero {
  meta: ProvinciaMeta;
  resumen: ResumenProvincia | undefined;
  estado: EstadoMapa;
  score: number | null;
}

/** Filas del tablero: primero las provincias con datos (por score), luego las que no tienen (alfabético). */
export function filasTablero(
  meta: ProvinciaMeta[],
  datos: Viabilidad,
  agregado: Agregado,
  porIne: Map<string, Municipio>,
): FilaTablero[] {
  const orden: Record<EstadoMapa, number> = { Viable: 0, "Viable con condiciones": 1, "No viable": 2, "Sin datos": 3 };
  return meta
    .map((m) => {
      const r = datos.provincias[m.codigo];
      return { meta: m, resumen: r, estado: r ? r.estado : "Sin datos", score: scoreProvincia(r, agregado, porIne) } as FilaTablero;
    })
    .sort((a, b) => {
      if (!a.resumen !== !b.resumen) return a.resumen ? -1 : 1;
      if (!a.resumen) return a.meta.nombre.localeCompare(b.meta.nombre, "es");
      return (b.score ?? -1) - (a.score ?? -1) || orden[a.estado] - orden[b.estado];
    });
}
