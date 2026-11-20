---
tags: [clase, proyecto-3, decisiones]
actualizado: 2026-11-17
---

# Decisiones y reglas de trabajo

Volver a [[00 Índice]]. Fuente oficial: `docs/metodologia/01_Objetivo_y_alcance.md` (tabla de decisiones D1-D8).

## Decisiones del equipo

- **D7 · Precio de la luz del simulador (17/11/2026):** el simulador mantiene como precio base la **media spot de los últimos 12 meses**. La previsión a 1 año se enseña como escenario del VAN (con el precio previsto el VAN sale negativo en todas las provincias: el precio pesa más que la ubicación).
- **D8 · Acierto mínimo (17/11/2026):** todo modelo debe acertar **al menos un 85 %** (objetivo 90 %) y **ninguno puede llegar al 99,9 %** (indicaría fuga de información). Un modelo que no cumple solo se enseña como escenario orientativo, con aviso.
- **Precio de la luz (17/11/2026):** se queda como orientativo y fuera del VAN; no se fuerza el 85 %. Futuros de OMIP como mejora posible.
- **Renovables (17/11/2026):** se enseñan dos cifras, mes a mes (orientativo) y % medio de 12 meses (cumple).

## Regla: no forzar resultados (pedida por el usuario)

> «No quiero que fuerces el resultado, quiero que salga Aragón con nuestros datos, si no sale, se añaden datos que antes no estaban, todo debe ser por datos reales, ya que en un futuro podría cambiar la cosa.»

Cómo se aplica:
1. **Nunca se ajustan pesos** para que gane una provincia.
2. Cada dato nuevo se añade con su **regla fijada antes de ver el ranking** (qué bloque, qué dirección) y sin cambiar pesos.
3. Solo **datos reales y actualizables** (si mañana cambia la realidad, cambia el resultado).
4. Las noticias (p. ej. inversiones en Aragón) se usan solo como **comprobación externa**, nunca como dato del modelo.

## Otras reglas del proyecto

- Ningún dato se inventa (R-1). Los datos demo se marcan como «DEMO sintético».
- Textos en español de España. Lo que no viene de clase se marca «recomendación (no viene de clase)».
- Ramas `feature/…`, nunca `main`. Commits pequeños y solo cuando el usuario lo pide.
- Tras cada tarea: `pytest`, `npm test`, `npm run build` y actualizar checklist 06 y estado 07.


## Decisiones del equipo

- **Futuros de OMIP (18/11/2026):** no se usan para el precio de la luz. No están en abierto; sacarlos de su web choca con sus condiciones de uso, y el mercado de futuros también falló mucho en 2022-2024, así que no aseguran el 85 %. El precio sigue como escenario orientativo, fuera del VAN (D7).
