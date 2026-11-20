"""Previsión de la demanda eléctrica nacional a 10 años (pregunta P5) con backtesting plurianual.

Datos: demanda mensual nacional de REData 2007-2025 (`data/clean/ree_demanda_mensual.csv`, `python -m cpd.etl.ree
--inicio 2007 --fin 2025`), sumada por años completos (TWh).

Protocolo (R-6):
- **Orígenes:** el final de cada año desde 2011 hasta el penúltimo. En cada origen, cada modelo usa solo los años
  hasta el origen y prevé los 10 siguientes (o los que haya hasta el último dato).
- **Error:** MAPE de la demanda anual por horizonte (1 a 10 años). Hay muchos orígenes a 1 año y solo unos pocos a
  10 años: el error a 10 años es el más incierto de todos.
- **Candidatos:** sin cambio (último año), media de 3 años, deriva (cambio medio anual de los últimos 10 años),
  tendencia lineal (`np.polyfit`, como `cpd.forecast`), Holt con tendencia amortiguada (`statsmodels`) y la
  combinación de los 3 mejores. Elección: la combinación salvo que un modelo la mejore en más de un 5 % (igual que en
  `cpd.modelos.anual`).
- **Intervalo:** a cada horizonte se le aplica la dispersión del error relativo observada en el backtesting; donde hay
  menos de 8 orígenes se extrapola con la regla de la raíz del horizonte (σ_h = σ_1 · √h). El intervalo nunca se
  estrecha al alargar el plazo.

No modela la llegada de nuevos consumos grandes (centros de datos, electrificación, hidrógeno): es una previsión
tendencial. Se dice en el informe.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from cpd.modelos.anual import MARGEN_COMBINACION, MIEMBROS_COMBINACION
from cpd.modelos.metricas import acierto_pct

HORIZONTE_ANIOS: int = 10
PRIMER_ORIGEN: int = 2011
MIN_ORIGENES_INTERVALO: int = 8

ModeloAnual = Callable[[pd.Series, int], np.ndarray]


def demanda_anual(mensual: pd.Series) -> pd.Series:
    """Suma anual (TWh) de los años con 12 meses de dato.

    Args:
        mensual: demanda mensual (MWh) con índice de fechas.
    """
    serie = pd.to_numeric(mensual, errors="coerce").dropna()
    anios = serie.groupby(serie.index.year).agg(["sum", "count"])
    completos = anios[anios["count"] == 12]
    return (completos["sum"] / 1e6).rename("demanda_twh")


def _holt(historia: pd.Series, pasos: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ajuste = ExponentialSmoothing(np.log(historia.to_numpy(dtype=float)), trend="add", damped_trend=True, initialization_method="estimated").fit()
    return np.exp(ajuste.forecast(pasos))


def modelos() -> dict[str, ModeloAnual]:
    """Candidatos: función (historia anual hasta el origen, nº de años) → previsión de cada año (TWh)."""

    def sin_cambio(h: pd.Series, n: int) -> np.ndarray:
        return np.repeat(h.iloc[-1], n)

    def media_3(h: pd.Series, n: int) -> np.ndarray:
        return np.repeat(h.iloc[-3:].mean(), n)

    def deriva(h: pd.Series, n: int) -> np.ndarray:
        ventana = h.iloc[-11:]
        paso = (ventana.iloc[-1] - ventana.iloc[0]) / (len(ventana) - 1)
        return h.iloc[-1] + paso * np.arange(1, n + 1)

    def tendencia_lineal(h: pd.Series, n: int) -> np.ndarray:
        pendiente, corte = np.polyfit(h.index.to_numpy(dtype=float), h.to_numpy(dtype=float), 1)
        return corte + pendiente * (h.index[-1] + np.arange(1, n + 1))

    return {"sin_cambio": sin_cambio, "media_3_anios": media_3, "deriva": deriva, "tendencia_lineal": tendencia_lineal, "holt_amortiguado": _holt}


def backtesting(anual: pd.Series, candidatos: dict[str, ModeloAnual] | None = None) -> pd.DataFrame:
    """Previsiones de cada candidato desde cada origen, con el valor real.

    Returns:
        `modelo`, `origen` (año), `anio`, `horizonte_anios`, `prevision_twh`, `real_twh`.
    """
    candidatos = candidatos or modelos()
    filas = []
    for origen in range(PRIMER_ORIGEN, int(anual.index.max())):
        historia = anual.loc[:origen]
        pasos = min(HORIZONTE_ANIOS, int(anual.index.max()) - origen)
        for nombre, modelo in candidatos.items():
            prevision = modelo(historia, pasos)
            for h in range(1, pasos + 1):
                anio = origen + h
                filas.append({"modelo": nombre, "origen": origen, "anio": anio, "horizonte_anios": h, "prevision_twh": float(prevision[h - 1]), "real_twh": float(anual.loc[anio])})
    return pd.DataFrame(filas)


def evaluar(anual: pd.Series) -> dict[str, Any]:
    """Backtesting, combinación de los 3 mejores y elección (combinación salvo mejora clara de un modelo).

    Returns:
        `backtesting` (con la combinación), `por_horizonte` (MAPE por modelo y horizonte), `resumen` (MAPE medio de los
        horizontes 1 a 10, cada horizonte con el mismo peso), `miembros`, `elegido`.
    """
    bt = backtesting(anual)
    bt["ape"] = (bt["prevision_twh"] - bt["real_twh"]).abs() / bt["real_twh"] * 100
    por_h = bt.groupby(["modelo", "horizonte_anios"])["ape"].mean().rename("mape_pct").reset_index()
    resumen = por_h.groupby("modelo")["mape_pct"].mean().sort_values()
    miembros = list(resumen.index[:MIEMBROS_COMBINACION])
    combinacion = (
        bt[bt["modelo"].isin(miembros)]
        .groupby(["origen", "anio", "horizonte_anios"], as_index=False)
        .agg(prevision_twh=("prevision_twh", "mean"), real_twh=("real_twh", "first"))
        .assign(modelo="combinacion")
    )
    combinacion["ape"] = (combinacion["prevision_twh"] - combinacion["real_twh"]).abs() / combinacion["real_twh"] * 100
    bt = pd.concat([bt, combinacion], ignore_index=True)
    por_h = bt.groupby(["modelo", "horizonte_anios"]).agg(mape_pct=("ape", "mean"), origenes=("ape", "size")).reset_index()
    resumen = por_h.groupby("modelo")["mape_pct"].mean().sort_values()
    individual = resumen.drop("combinacion")
    elegido = str(individual.index[0]) if individual.iloc[0] < resumen["combinacion"] * (1 - MARGEN_COMBINACION) else "combinacion"
    # Acierto (100 − WAPE) de cada modelo con todos los puntos del backtesting (todos los horizontes).
    acierto = bt.groupby("modelo").apply(lambda d: acierto_pct(d["real_twh"], d["prevision_twh"]), include_groups=False)
    return {"backtesting": bt, "por_horizonte": por_h, "resumen": resumen, "miembros": miembros, "elegido": elegido, "acierto": acierto}


def prevision(anual: pd.Series, resultado: dict[str, Any], cuantiles: tuple[float, float] = (0.1, 0.9)) -> pd.DataFrame:
    """Previsión de los 10 años siguientes al último año completo, con intervalo por horizonte.

    Returns:
        `anio`, `horizonte_anios`, `prevision_twh`, `inferior_twh`, `superior_twh`, `modelo`, `origenes_intervalo`.
    """
    todos = modelos()
    nombres = resultado["miembros"] if resultado["elegido"] == "combinacion" else [resultado["elegido"]]
    previsto = np.mean([todos[n](anual, HORIZONTE_ANIOS) for n in nombres], axis=0)
    bt = resultado["backtesting"]
    propio = bt[bt["modelo"] == resultado["elegido"]].assign(log_error=lambda d: np.log(d["real_twh"] / d["prevision_twh"]))
    z_bajo, z_alto = (np.quantile(np.random.default_rng(0).standard_normal(200_000), q) for q in cuantiles)
    sigma_1 = float(propio.loc[propio["horizonte_anios"] == 1, "log_error"].std(ddof=1))
    filas = []
    bajo_previo, alto_previo = 0.0, 0.0
    for h in range(1, HORIZONTE_ANIOS + 1):
        errores = propio.loc[propio["horizonte_anios"] == h, "log_error"]
        if len(errores) >= MIN_ORIGENES_INTERVALO:
            bajo, alto = np.quantile(errores, cuantiles)
            fuente = len(errores)
        else:  # pocos orígenes: σ_h = σ_1 · √h (supuesto de error que se acumula como un paseo aleatorio)
            bajo, alto = z_bajo * sigma_1 * np.sqrt(h), z_alto * sigma_1 * np.sqrt(h)
            fuente = 0
        # La incertidumbre no puede bajar al alargar el plazo: el intervalo de h nunca es más estrecho que el de h − 1.
        bajo_previo, alto_previo = min(bajo, bajo_previo, 0.0), max(alto, alto_previo, 0.0)
        p = float(previsto[h - 1])
        filas.append(
            {
                "anio": int(anual.index.max()) + h,
                "horizonte_anios": h,
                "prevision_twh": p,
                "inferior_twh": p * np.exp(bajo_previo),
                "superior_twh": p * np.exp(alto_previo),
                "modelo": resultado["elegido"],
                "origenes_intervalo": fuente,
            }
        )
    return pd.DataFrame(filas)
