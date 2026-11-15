---
tags: [fuente, clase, visualizacion, correlacion, p3]
estado: revisada
actualizado: 2026-11-14
---

# Fuente · Clase 09/10/2026 · Data Visualization y Correlación

Archivo: `C:\Users\marcm\Downloads\20261009_Data_Visualization__Correlation.pptx.pdf` (26 páginas; revisadas en texto y en las diapositivas con imágenes). Volver a [[00_Indice]].

## Resumen

Repaso de gráficos (línea, barra, histograma, dispersión, box plot, heatmap, pie y pair plot) con su uso recomendado. Después, la correlación: definición (−1 a 1), los tres coeficientes (Pearson, Spearman, Kendall), y la advertencia de que correlación no implica causalidad. Incluye un examen con cuatro preguntas (python con CSV, gráfico, bases de datos relacionales frente a no relacionales, y grafos).

## Términos clave

Línea · barra · histograma · dispersión · box plot · mediana · cuartiles · outliers · heatmap · pie chart · pair plot · correlación · Pearson · Spearman · Kendall · lineal · monótona · outlier · falacia · causalidad · relacional · no relacional · grafo · influencer · notas (CSV) · OOP.

## Acciones (lo que pide la clase)

**Obligatorias del proyecto (según la clase y el enunciado):**
1. Usar el gráfico adecuado a cada pregunta (p. 6-13).
2. Calcular la correlación y saber qué tipo usar (Pearson si hay relación lineal y sin outliers; Spearman si es monótona o hay outliers; Kendall si la muestra es pequeña) (p. 23-24).
3. Comunicar la advertencia de causalidad en cada conclusión (p. 18-21).
4. Explorar relaciones con pair plot (p. 13).

**Ejercicios de clase (no entregables de P3):**
- Q1: script en Python que abra un CSV de notas y muestre la media de proyecto 1 y proyecto 3; después un gráfico. Se evalúa también OOP.
- Q2: gráfico para ver si hay correlación entre proyecto 1 y proyecto 3.
- Q3: diferencia entre bases de datos relacionales y no relacionales, con ejemplos.
- Q4: qué es un influencer en un grafo y qué estructuras de datos usa un buscador web.

**Recomendaciones (no viene de clase):**
- Usar Spearman además de Pearson cuando haya outliers, y comparar ambos.
- Practicar el EDA con uno de los datasets de ejemplo antes de usar datos propios.

## Enlaces

| Enlace | Dónde | Estado | Qué es |
|---|---|---|---|
| `https://github.com/mwaskom/seaborn-data/blob/master/penguins.csv` | p. 25 | Leído (cabecera) | Dataset de pingüinos: especie, isla, longitudes de pico y aleta, masa corporal, sexo. Unas 344 filas. |
| `https://github.com/mwaskom/seaborn-data/blob/master/tips.csv` | p. 25 | Leído (cabecera) | Dataset de propinas: total de la cuenta, propina, sexo, fumador, día, hora, tamaño del grupo. Unas 244 filas. |
| `https://archive.ics.uci.edu/dataset/17/breast-cancer-wisconsin-data-set` | p. 25 | Leído | Breast Cancer Wisconsin: 569 casos, 30 variables numéricas, clasificación maligno/benigno, sin valores ausentes. |
| `https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success` | p. 25 | Leído | Predicción de abandono y éxito académico: 4 424 estudiantes, 36 variables, tres clases (abandono, matriculado, graduado), clases desbalanceadas, sin ausentes. |

## Cómo se aplica a P3

- **EDA (fase 4):** histogramas, box plots, dispersión, heatmap y pair plot sobre el panel provincia × mes.
- **Correlación territorio–viabilidad (objetivo 6):** matriz con Pearson y Spearman, frente al score o frente a la demanda.
- **Informe de visualización (M4RA4):** cada gráfico con su unidad, su pregunta y su límite de interpretación.
- **Ejemplo de causalidad:** la clase muestra que dos series pueden subir juntas sin relación causal (p. 18-20). Hay que aplicarlo a las conclusiones de P3, por ejemplo: "más energía renovable" y "más viabilidad" no implican que una cause la otra.

## Notas de estado en el repo

Ver [[06_Checklist_entrega]], filas I12 a I26. Resumen: gráficos de línea y barra en la app (🟡); el resto de gráficos del EDA, correlación y causalidad no están hechos (❌).
