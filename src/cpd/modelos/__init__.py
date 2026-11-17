"""Modelos de predicción del proyecto (fases 7 y 8 de la metodología).

- `demanda`: previsión de la demanda eléctrica mensual por comunidad autónoma (regresión, serie temporal).
- `prob_cpd`: probabilidad de que una provincia tenga un centro de datos (clasificación, transversal).
- `metricas`: métricas de regresión y clasificación (MAE, RMSE, MAPE, ROC-AUC, log-loss…).
- `eda`: análisis exploratorio del panel (figuras e informe).

Se ejecuta todo con `python -m cpd.modelos` (ver `cpd/modelos/__main__.py`).
"""
