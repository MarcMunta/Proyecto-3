---
tags: [metodologia, plantillas, p3]
estado: borrador
actualizado: 2026-11-14
---

# 08 · Plantillas

Volver a [[00_Indice]]. Estas mismas plantillas están en `.github/` (issue y PR) para que GitHub las proponga automáticamente.

---

## 1. Tarea o issue

Archivo equivalente: `.github/ISSUE_TEMPLATE/tarea.md`.

```markdown
---
name: Tarea
about: Trabajo concreto del proyecto, ligado a la checklist
title: "[tipo] resumen corto"
labels: ""
assignees: ""
---

## Qué hay que hacer
Una frase clara en imperativo.

## Por qué
Requisito o pregunta que cierra (ID de [[06_Checklist_entrega]], p. ej. B6, I24).

## Fase de la metodología
Fase N de [[03_Flujo_de_trabajo]].

## Entradas
- Datos: (ruta en `data/…` y fecha)
- Código o notas previas: (ruta)

## Salidas
- Código: (ruta)
- Documento o figura: (ruta en `docs/…`)

## Hecho cuando
- [ ] (criterio verificable 1)
- [ ] (criterio verificable 2)
- [ ] Tests en verde (`pytest -q`, `npm test` si aplica)
- [ ] Checklist actualizada

## Reglas que aplican
R-…, de [[04_Reglas_de_datos]]; …

## Responsable y fecha
Responsable: · Fecha límite: dd/mm/aaaa
```

---

## 2. Descripción de pull request

Archivo equivalente: `.github/pull_request_template.md`.

```markdown
## Resumen
Qué cambia y por qué, en 2-3 frases.

## Tipo
- [ ] feat · [ ] fix · [ ] docs · [ ] test · [ ] refactor · [ ] data · [ ] chore

## Requisitos que cierra
IDs de [[06_Checklist_entrega]] (p. ej. B3, I67). Cambios de estado: ❌ → 🟡 / ✅.

## Datos (si la PR toca datos)
- Fuente y URL:
- Fecha de descarga:
- SHA-256 del fichero nuevo o modificado:
- Licencia:
- Columnas nuevas y unidades:

## Cómo probarlo
1. Comando o paso 1
2. Comando o paso 2
Resultado esperado:

## Comprobaciones
- [ ] `.\.venv\Scripts\python.exe -m pytest -q` en verde
- [ ] `cd frontend && npm test && npm run build` en verde (si toca frontend)
- [ ] Funciones nuevas con docstring en español y test
- [ ] Sin claves, `.env`, datos raw grandes ni datos personales en el diff
- [ ] Checklist actualizada
- [ ] Capturas si cambia la interfaz (escritorio y 375 px)

## Revisión
Revisor: (no puede ser quien abre la PR). Aprobación: ☐
```

---

## 3. Cabecera de notebook

Primera celda de cada notebook (`notebooks/`), en Markdown:

```markdown
# Título del análisis

- **Objetivo:** qué pregunta responde (una frase; ID de la checklist)
- **Entradas:** rutas exactas y fecha de los datos (`data/curated/…`)
- **Salidas:** figuras en `docs/figuras/`, tablas en `docs/analisis/`
- **Autor/a:** nombre · **Fecha:** dd/mm/aaaa
- **Reproducir:** "Restart & Run All" desde la raíz del repo. Tiempo aproximado: X min.
- **Limitaciones conocidas:** …
```

---

## 4. Sección de informe de análisis

Para cada análisis (correlación, EDA, previsión, visualización):

```markdown
### N.N · Título de la pregunta

**Pregunta.** ¿Qué queremos saber? (una frase)

**Datos.** Fuente, periodo, granularidad, nº de filas, tratamiento de nulos y atípicos.

**Método.** Qué técnica y por qué (p. ej., Spearman porque hay outliers en renta).

**Resultado.** Número o figura, con unidades. Figura 1 (ruta).

**Interpretación.** Qué significa y qué NO significa. Si hay correlación, escribir que no implica causalidad.

**Limitaciones.** Sesgos, cobertura, supuestos.

**Decisión que apoya.** Qué cambia en el proyecto por este resultado.
```

---

## 5. Model card (ficha de modelo)

Guardar como `docs/modelos/<nombre_modelo>.md`.

```markdown
# Model card · <nombre del modelo>

## Datos
- Fuente y tabla: (ruta)
- Periodo de entrenamiento: aaaa-mm a aaaa-mm
- Periodo de validación: aaaa-mm a aaaa-mm
- Periodo de test: aaaa-mm a aaaa-mm (usado una vez)
- Granularidad: (p. ej., provincia × mes)
- Features (lista y ventana): (enlace al diccionario de features)
- Tratamiento de nulos y escalado (ajustado solo con entrenamiento): …

## Objetivo
Qué predice, unidad, horizonte.

## Baseline
Nombre del baseline y su resultado en validación y test.

## Métrica principal
Nombre, fórmula en una línea, motivo de la elección y coste de errores.

## Resultados
| Modelo | MAE | RMSE | Otras | Validación | Test |
|---|---|---|---|---|---|
| Baseline | | | | | |
| Modelo ML | | | | | |

Matriz de confusión o curva ROC (si es clasificación), con umbral elegido y justificación.

## Sesgos y comprobaciones
- Paradoja de la exactitud: comprobada (sí/no) y resultado.
- Resultados por subgrupo (CCAA, tamaño de municipio…): …

## Limitaciones
Lo que el modelo no puede hacer (p. ej., no extrapola a municipios sin datos; incertidumbre a 10 años).

## Uso previsto y uso no previsto
- Previsto: …
- No previsto: decisiones de inversión sin revisión humana.

## Reproducción
Comando exacto, semilla, versión de librerías (`requirements.txt`), fecha de entrenamiento.
```

---

## 6. Entrada de decisión (acta corta)

```markdown
## Decisión DNN · título corto (dd/mm/aaaa)
- **Contexto:** qué problema hay.
- **Opciones consideradas:** A, B.
- **Decisión:** la elegida.
- **Motivo:** una o dos frases.
- **Consecuencias:** qué cambia en el código, datos o checklist. IDs afectados.
- **Quién decide:** equipo / responsable.
```
