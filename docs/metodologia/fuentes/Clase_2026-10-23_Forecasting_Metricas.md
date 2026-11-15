---
tags: [fuente, clase, forecasting, metricas, p3]
estado: revisada
actualizado: 2026-11-14
---

# Fuente · Clase 23/10/2026 · Forecasting y métricas

Archivo: `C:\Users\marcm\Downloads\20261023_Big_Data_forecasting_2_METRICS.pptx.pdf` (25 páginas; revisadas en texto y en las diapositivas clave). Volver a [[00_Indice]].

## Resumen

Explica por qué fallan las previsiones (datos mal preparados, mala estacionalidad, variables externas mal integradas, fuga de información, horizonte o ventana temporal mal elegidos, métricas mal interpretadas). Después presenta cómo medir la calidad: métricas de regresión (distancia al valor real) y de clasificación (accuracy, precision, recall, F-score, ROC-AUC, log-loss), la matriz de confusión, la curva ROC con TPR y FPR, la paradoja de la exactitud y el sesgo de los datos.

## Términos clave

Previsión (forecasting) · horizonte · ventana temporal · estacionalidad · variables externas · fuga de información · métricas de regresión · métricas de clasificación · accuracy · precision · recall · F-score · ROC-AUC · log-loss · matriz de confusión · TP · TN · FP · FN · error tipo I y tipo II · TPR · FPR · umbral · paradoja de la exactitud · coste de un error · sesgo (bias) · ejemplo AutoPredict.

## Acciones (lo que pide la clase)

**Obligatorias del proyecto (según la clase y el enunciado):**
1. Revisar las causas de fallo de la previsión antes de dar un resultado (p. 4).
2. Elegir métricas según el tipo de problema: regresión (distancia) o clasificación (p. 9-13).
3. Calcular la matriz de confusión y las métricas derivadas (p. 14-17).
4. Usar ROC-AUC para comparar modelos y elegir umbral (p. 19).
5. No aprobar un modelo solo por accuracy: comprobar la paradoja de la exactitud (p. 23).
6. Comprobar sesgos de los datos, "con código" (p. 22-24).
7. Tener en cuenta que no todos los errores cuestan lo mismo (p. 8).

**Ejercicio de clase (no entregable):** AutoPredict, en el que cada alumno elige un Pokémon en secreto y el profesor predice; después se completa una tabla de aciertos y se calcula la métrica.

**Recomendaciones (no viene de clase):**
- Para regresión, usar MAE y RMSE, con MAPE solo sin ceros. La clase no nombra estas fórmulas.
- Usar backtesting (varias fechas de corte en el pasado) para evaluar la previsión.

## Enlaces

| Enlace | Dónde | Estado | Qué es |
|---|---|---|---|
| `https://docs.google.com/spreadsheets/d/1Dm4tyKZBjCid1-4bGuKkrsF64Jyt2WYngBStSIMwa7w/edit?usp=sharing` | Anotación del PDF (diapositiva de AutoPredict, probablemente p. 18) | Lectura parcial | Hoja de cálculo "PREDICTION" con 15 predicciones de inicial de Pokémon (Squirtle, Charmander, Bulbasaur), columna de acierto, matriz 3×3 y métricas. Se leen precisión ≈ 0,364 y exactitud ≈ 0,267. Las otras métricas y las pestañas "Full 1–3" y "COSTES" no se ven sin cargar la hoja completa. |

## Cómo se aplica a P3

- **Fase 7 (modelado):** el baseline de `forecast.py` debe compararse con modelos ML con la misma división temporal. La clase sobre fallos de previsión sirve como lista de comprobación antes de dar un resultado.
- **Fase 8 (métricas):** para la previsión de demanda, MAE y RMSE. Para una clasificación de viabilidad (si se modela), matriz de confusión, precision, recall, ROC-AUC y umbral.
- **Riesgo de fuga (R-8):** la clase lo menciona como causa de fallo. Revisar cada feature.
- **Sesgo (R-6 y fase 8):** comprobar sesgos por subgrupos (CCAA, tamaño de municipio).
- **Coste de errores:** escribirlo en la model card ([[08_Plantillas]]). Para el CPD, un falso "viable" tiene un coste de inversión mucho mayor que un falso "no viable".

## Notas de estado en el repo

Ver [[06_Checklist_entrega]], filas I27 a I48. Resumen: horizonte y estacionalidad del baseline (🟡); todas las métricas de clasificación y regresión, la matriz, el umbral y la comprobación de sesgos están pendientes (❌).
