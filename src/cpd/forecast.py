"""Previsión mensual de demanda eléctrica a 10 años: modelo BASELINE.

Método (solo numpy y pandas):
1. Nivel anual: media mensual de cada año completo (12 meses).
2. Tendencia lineal: recta ajustada por mínimos cuadrados a los niveles anuales
   (tendencia(t) = a + b·t, con t en años decimales).
3. Estacionalidad: factor de cada mes = media de (observado / tendencia) en ese mes,
   normalizado para que la media de los 12 factores sea 1.
4. Previsión: prevision(t) = tendencia(t) × factor_mes.
5. Intervalo aproximado: ±1.96 × σ_residuos × sqrt(año de horizonte), donde σ_residuos es la
   desviación típica de los residuos dentro de muestra y el año de horizonte es ceil(h/12).
   El ancho crece con la raíz del horizonte como aproximación de la incertidumbre acumulada.

Es un modelo de referencia (baseline) para comparar después con SARIMA o Prophet.
No captura ciclos económicos, cambios de regulación ni efectos de la propia instalación del CPD.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MINIMO_MESES_HISTORIA: int = 24
Z_INTERVALO: float = 1.96


def _tendencia(a: float, b: float, t: np.ndarray) -> np.ndarray:
    """Evalúa la recta de tendencia en años decimales."""
    return a + b * t


def prever_mensual(serie: pd.Series, horizonte_meses: int = 120) -> pd.DataFrame:
    """Genera la previsión mensual a partir de una serie histórica mensual.

    Args:
        serie: valores mensuales con índice de fechas (cualquier día del mes; se normaliza al día 1).
        horizonte_meses: número de meses a prever (por defecto 120 = 10 años).

    Returns:
        DataFrame con columnas fecha (inicio de mes), prevision, inferior y superior.

    Raises:
        ValueError: si hay menos de 24 meses de historia, si el horizonte no es positivo
            o si no hay al menos dos años completos para ajustar la tendencia.
    """
    if horizonte_meses < 1:
        raise ValueError("El horizonte debe ser de al menos 1 mes")

    datos = pd.to_numeric(serie, errors="coerce").dropna().sort_index()
    if len(datos) < MINIMO_MESES_HISTORIA:
        raise ValueError(f"Se necesitan al menos {MINIMO_MESES_HISTORIA} meses de historia y hay {len(datos)}")
    datos.index = pd.DatetimeIndex(pd.to_datetime(datos.index)).to_period("M").to_timestamp()

    anios = datos.index.year.values
    meses = datos.index.month.values
    t_mensual = anios + (meses - 0.5) / 12  # años decimales de cada observación

    # 1-2. Tendencia lineal sobre el nivel anual (solo años completos)
    resumen_anual = datos.groupby(datos.index.year).agg(["mean", "count"])
    completos = resumen_anual[resumen_anual["count"] == 12]
    if len(completos) < 2:
        raise ValueError("Se necesitan al menos dos años completos para ajustar la tendencia")
    pendiente, intercepto = np.polyfit(completos.index.values + 0.5, completos["mean"].values, 1)

    # 3. Factores estacionales mensuales (media 1)
    tendencia_hist = _tendencia(intercepto, pendiente, t_mensual)
    ratio = datos.values / tendencia_hist
    factores = pd.Series(ratio, index=datos.index).groupby(datos.index.month).mean()
    factores = factores.reindex(range(1, 13)).fillna(1.0)
    factores = factores / factores.mean()

    # 5. Desviación típica de los residuos dentro de muestra
    ajuste_hist = tendencia_hist * factores.loc[meses].values
    sigma = float(np.std(datos.values - ajuste_hist, ddof=1))

    # 4. Previsión futura
    fechas = pd.date_range(datos.index[-1] + pd.offsets.MonthBegin(1), periods=horizonte_meses, freq="MS")
    t_futuro = fechas.year.values + (fechas.month.values - 0.5) / 12
    prevision = _tendencia(intercepto, pendiente, t_futuro) * factores.loc[fechas.month.values].values

    # Intervalo aproximado con crecimiento por año de horizonte
    anio_horizonte = np.ceil(np.arange(1, horizonte_meses + 1) / 12)
    ancho = Z_INTERVALO * sigma * np.sqrt(anio_horizonte)

    return pd.DataFrame({
        "fecha": fechas,
        "prevision": prevision,
        "inferior": prevision - ancho,
        "superior": prevision + ancho,
    })
