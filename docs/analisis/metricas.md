# Métricas de los modelos

> Generado por `python -m cpd.modelos` el 17/11/2026. No editar a mano: se sobrescribe al volver a ejecutar.

Fase 8 de [la metodología](../metodologia/03_Flujo_de_trabajo.md). Fichas de modelo:
[demanda por comunidad](../modelos/demanda_ccaa.md) y [probabilidad de CPD](../modelos/prob_cpd.md).

## Regresión: demanda eléctrica mensual por comunidad (MWh)

Métricas (recomendación, no vienen de clase: la clase pide medir la distancia al valor real [C3 p.10-11]):

- **MAPE** (métrica principal): error medio en % del valor real. Permite comparar comunidades de tamaños muy
  distintos. Un MAPE del 4 % equivale a equivocarse en unos 140 GWh al mes en Andalucía (que consume unos 3.500 GWh
  al mes) o en 0,7 GWh en Ceuta (unos 17 GWh al mes).
- **MAE**: error medio en GWh; lo dominan las comunidades grandes (Cataluña, Andalucía, Madrid).
- **RMSE**: como el MAE pero castiga más los errores grandes; si es mucho mayor que el MAE, hay meses con fallos
  grandes.

Todas las filas se calculan con los mismos meses y comunidades. Test: usado una vez, con el modelo reentrenado con
entrenamiento + validación.

### Demanda por comunidad a 1 mes vista

| Modelo | Configuración | MAPE validación | MAPE test | MAE test (GWh) | RMSE test (GWh) |
|---|---|---|---|---|---|
| Último valor (naive) | — | 8,59 % | 9,05 % | 107,6 | 183,6 |
| Mismo mes del año anterior (estacional) | — | 3,94 % | 4,88 % | 55,6 | 111,5 |
| Tendencia + estacionalidad (`forecast.py`) | — | 4,23 % | 6,43 % | 71,8 | 135,7 |
| Ridge (ML) | alpha=0.1 | 3,31 % | 4,40 % | 50,0 | 99,0 |
| Gradient boosting (ML) | learning_rate=0.1, max_depth=3 | 3,51 % | 4,31 % | 49,9 | 101,6 |

Modelo elegido con la validación: **Ridge (ML)** (alpha=0.1).

### Demanda por comunidad a 12 meses vista

| Modelo | Configuración | MAPE validación | MAPE test | MAE test (GWh) | RMSE test (GWh) |
|---|---|---|---|---|---|
| Último valor (naive) | — | 3,94 % | 4,88 % | 55,6 | 111,5 |
| Mismo mes del año anterior (estacional) | — | 3,94 % | 4,88 % | 55,6 | 111,5 |
| Tendencia + estacionalidad (`forecast.py`) | — | 4,63 % | 6,97 % | 75,7 | 140,2 |
| Ridge (ML) | alpha=0.1 | 4,44 % | 5,60 % | 63,7 | 119,8 |
| Gradient boosting (ML) | learning_rate=0.1, max_depth=None | 5,04 % | 6,36 % | 75,9 | 139,0 |

Modelo elegido con la validación: **Mismo mes del año anterior (estacional)** (—).

### Backtesting a 12 meses (cortes: 2022-07, 2023-07, 2024-07)

| Modelo | MAPE medio | Mejor corte | Peor corte |
|---|---|---|---|
| Mismo mes del año anterior (estacional) | 4,88 % | 3,94 % | 6,64 % |
| Último valor (naive) | 4,88 % | 3,94 % | 6,64 % |
| Ridge (ML) | 5,08 % | 3,97 % | 6,84 % |
| Tendencia + estacionalidad (`forecast.py`) | 5,47 % | 4,63 % | 6,85 % |
| Gradient boosting (ML) | 5,64 % | 4,73 % | 7,15 % |

## Clasificación: probabilidad de que una provincia tenga CPD

Validación cruzada estratificada repetida (5 × 20); cada provincia se evalúa con modelos que no la han visto.

| Modelo | Log-loss | ROC-AUC | Brier | Accuracy (umbral 0,5) | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Clase mayoritaria (baseline) | 0,584 | 0,500 (constante) | 0,197 | 73,1 % | 0,00 | 0,00 | 0,00 |
| Logística solo con población (baseline) | 0,377 | 0,882 | 0,115 | 86,5 % | 1,00 | 0,50 | 0,67 |
| Logística con todas las features (ML) | 0,394 | 0,855 | 0,117 | 84,6 % | 0,80 | 0,57 | 0,67 |
| Random forest (ML) | 0,422 | 0,885 | 0,124 | 84,6 % | 0,88 | 0,50 | 0,64 |

- **Log-loss** (métrica principal, porque el mapa muestra la probabilidad): castiga las probabilidades seguras y
  equivocadas. Cuanto más baja, mejor. La clase mayoritaria marca el mínimo que hay que superar.
- **ROC-AUC** [C3 p.19]: probabilidad de que una provincia con CPD reciba más probabilidad que una sin CPD.
  0,5 = azar; 1 = perfecto.
- **Paradoja de la exactitud** [C3 p.23]: predecir siempre "no tiene CPD" acierta el
  73,1 % sin servir para nada. Por eso no se elige el modelo por accuracy.

Modelo elegido (menor log-loss): **Logística solo con población (baseline)**.
