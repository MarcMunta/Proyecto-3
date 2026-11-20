"""Ingeniería de variables (fase 6 de la metodología) para los modelos de `cpd.modelos`.

- `demanda`: features de la demanda eléctrica mensual por comunidad autónoma (lags, ventanas, estacionalidad).
- `provincia`: features estáticas por provincia para la probabilidad de que haya un CPD.

Regla de fuga (R-8): cada feature se calcula solo con datos que se conocerían en la fecha de la predicción.
"""
