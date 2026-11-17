# Métricas de los modelos

> Generado por `python -m cpd.modelos` el 17/11/2026. No editar a mano: se sobrescribe al volver a ejecutar.

Fase 8 de [la metodología](../metodologia/03_Flujo_de_trabajo.md). Fichas de modelo:
[demanda por comunidad](../modelos/demanda_ccaa.md), [probabilidad de CPD](../modelos/prob_cpd.md) y
[precio de la luz](../modelos/precio_luz.md).

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

## Regresión: precio medio mensual de la electricidad (spot, €/MWh)

Un solo modelo para los horizontes de 1 a 12 meses. Métrica principal: **MAE en €/MWh** (cada €/MWh de error es
coste de energía mal estimado; el MAPE se dispara en los meses con precios muy bajos). Validación
2024-11 a 2025-10; test 2025-11 a 2026-10, usado una vez.

| Modelo | Configuración | MAE validación | MAE test | RMSE test | MAE test h=1 | MAE test h=3 | MAE test h=6 | MAE test h=12 |
|---|---|---|---|---|---|---|---|---|
| Último valor (naive) | — | 36,8 | 39,1 | 50,0 | 20,7 | 38,8 | 43,9 | 43,4 |
| Media de los últimos 12 meses (la del simulador) | — | 23,5 | 35,7 | 47,5 | 32,3 | 35,9 | 38,1 | 33,9 |
| Mismo mes del año anterior (estacional) | — | 24,2 | 43,4 | 52,2 | 43,4 | 43,4 | 43,4 | 43,4 |
| Tendencia + estacionalidad (`forecast.py`) | — | 51,2 | 44,6 | 50,5 | 40,6 | 43,0 | 46,0 | 45,1 |
| Ridge (ML) | alpha=1000 | 41,9 | 31,3 | 38,1 | 18,6 | 27,0 | 31,9 | 36,1 |
| Gradient boosting (ML) | learning_rate=0.03, max_depth=3 | 65,6 | 35,7 | 44,7 | 24,9 | 34,3 | 38,3 | 38,5 |

Modelo elegido con la validación: **Media de los últimos 12 meses (la del simulador)** (—).

### Backtesting de la media de los 12 meses siguientes (orígenes trimestrales 2020-2023)

| Modelo | Error medio de la media anual (€/MWh) | Peor origen (€/MWh) |
|---|---|---|
| Último valor (naive) | 39,9 | 102,8 |
| Tendencia + estacionalidad (`forecast.py`) | 61,3 | 148,5 |
| Mismo mes del año anterior (estacional) | 62,0 | 135,9 |
| Media de los últimos 12 meses (la del simulador) | 62,0 | 135,9 |
| Ridge (ML) | 64,6 | 118,7 |
| Gradient boosting (ML) | 106,7 | 295,2 |

Es lo que usa el simulador: el precio medio del año siguiente. Detalle en la [ficha del modelo](../modelos/precio_luz.md).
