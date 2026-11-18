"""Modelos del gas y del tiempo: entradas del precio de la luz (añadidos el 18/11/2026). **Son inestables.**

El precio de la luz en España lo marca casi siempre la central de gas de ciclo combinado, y baja cuando hay mucho
viento, sol o agua. Por eso, para intentar mejorar el modelo del precio, se prevén por separado:

- **Gas** (MIBGAS, spot medio mensual, €/MWh): último valor, ETS sobre el logaritmo y los **futuros del gas**
  (mes siguiente, trimestre y año) como previsión del mercado.
- **Tiempo**, a través de la generación eléctrica de España por tecnología (REData): **eólica** (viento),
  **solar** (sol) e **hidráulica** (lluvia y embalses; con el Ridge sobre anomalías de la reserva).
- **Precio estructural**: log(precio) = f(log(gas), cuota de eólica, solar, hidráulica, nuclear, ciclo combinado y
  carbón, ciclo combinado × gas, mes), ajustado con los meses reales hasta el origen y alimentado con las previsiones
  del gas y de cada tecnología (ETS). Es un candidato más del precio.

Inestables: el gas y el tiempo de dentro de un año no se pueden saber; sus aciertos cambian mucho entre validación y
test. Además, ni con el gas y la generación **reales** de cada mes el precio se explica del todo (diagnóstico): falta
el precio del CO2 (sin fuente abierta: EEX es de pago), la demanda horaria y las interconexiones.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cpd.modelos import anual
from cpd.modelos.metricas import acierto_pct

TECNOLOGIAS_TIEMPO: tuple[str, ...] = ("eolica", "solar", "hidraulica")
CUOTAS: tuple[str, ...] = ("eolica", "solar", "hidraulica", "nuclear", "ciclo_combinado", "carbon")
COLUMNAS_PRECIO: list[str] = ["lgas", *CUOTAS, "cc_gas", "mes_sin", "mes_cos"]


def _ets_log(serie: pd.Series, pasos: int, meses: int) -> np.ndarray:
    """ETS amortiguada sobre el logaritmo con los últimos `meses` meses."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    valores = np.log(np.maximum(serie.iloc[-meses:].to_numpy(dtype=float), 1e-3))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ajuste = ExponentialSmoothing(valores, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12, initialization_method="estimated").fit()
    return np.exp(ajuste.forecast(pasos))


def candidatos_gas(gas: pd.DataFrame) -> dict[str, anual.Candidato]:
    """Candidatos del gas spot mensual (€/MWh): último valor, ETS (log) y futuros del gas negociados en el origen
    (M+1 para el mes siguiente, Q+1 hasta 4 meses, Y+1 el resto)."""
    spot = gas["gas_spot_eur_mwh"].dropna()

    def naive(origen: pd.Timestamp) -> pd.DataFrame:
        filas = anual._filas_futuras("GAS", origen)
        filas["prevision"] = float(spot.loc[:origen].iloc[-1])
        return filas

    def ets(origen: pd.Timestamp) -> pd.DataFrame:
        filas = anual._filas_futuras("GAS", origen)
        filas["prevision"] = _ets_log(spot.loc[:origen], anual.HORIZONTE, 96)
        return filas

    def futuros(origen: pd.Timestamp) -> pd.DataFrame:
        filas = anual._filas_futuras("GAS", origen)
        ultimo = gas.loc[:origen].ffill().iloc[-1]
        filas["prevision"] = [
            ultimo["gas_m1_eur_mwh"] if h == 1 else ultimo["gas_q1_eur_mwh"] if h <= 4 else ultimo["gas_y1_eur_mwh"] for h in filas["horizonte_meses"]
        ]
        return filas.dropna(subset=["prevision"])

    return {"naive": naive, "ets": ets, "futuros_gas": futuros}


def reales_gas(gas: pd.DataFrame) -> pd.DataFrame:
    """Gas spot mensual (€/MWh) en el formato de evaluación."""
    spot = gas["gas_spot_eur_mwh"].dropna()
    return pd.DataFrame({"serie": "GAS", "mes": spot.index, "real": spot.to_numpy()})


def reales_tecnologia(detalle: pd.DataFrame, tecnologia: str) -> pd.DataFrame:
    """Generación nacional mensual (MWh) de una tecnología en el formato de evaluación."""
    s = detalle.set_index("fecha")[tecnologia]
    return pd.DataFrame({"serie": tecnologia, "mes": pd.DatetimeIndex(s.index), "real": s.to_numpy()})


def candidatos_tecnologia(reales: pd.DataFrame, reserva_nacional: pd.Series) -> dict[str, anual.Candidato]:
    """Candidatos de una tecnología: los de las renovables en MWh y, para la hidráulica, el Ridge con los embalses."""
    candidatos = anual.candidatos_renovables(reales, maximo=np.inf, con_log=True)
    if reales["serie"].iloc[0] == "hidraulica":
        candidatos["ridge_anomalias"] = anual.candidato_ridge_anomalias(reales, reserva_nacional, logaritmo=True)
    return candidatos


def _variables_precio(tabla: pd.DataFrame) -> pd.DataFrame:
    """Variables del precio estructural a partir de gas (€/MWh) y generación por tecnología (MWh) de cada mes."""
    X = pd.DataFrame(index=tabla.index)
    X["lgas"] = np.log(tabla["gas"])
    for c in CUOTAS:
        X[c] = tabla[c] / tabla["total"]
    X["cc_gas"] = X["ciclo_combinado"] * X["lgas"]
    X["mes_sin"], X["mes_cos"] = np.sin(2 * np.pi * X.index.month / 12), np.cos(2 * np.pi * X.index.month / 12)
    return X


def tabla_conductores(gas: pd.DataFrame, detalle: pd.DataFrame) -> pd.DataFrame:
    """Gas spot y generación por tecnología por mes (solo meses con los dos)."""
    datos = detalle.assign(fecha=pd.to_datetime(detalle["fecha"])).set_index("fecha")[[*CUOTAS, "total"]]
    return datos.join(gas["gas_spot_eur_mwh"].rename("gas"), how="inner").dropna()


def _vacio() -> pd.DataFrame:
    return pd.DataFrame(
        {"serie": pd.Series(dtype=str), "mes": pd.Series(dtype="datetime64[ns]"), "horizonte_meses": pd.Series(dtype=int), "prevision": pd.Series(dtype=float)}
    )


def candidato_precio_estructural(gas: pd.DataFrame, detalle: pd.DataFrame, precio: pd.Series) -> anual.Candidato:
    """Precio estructural con el gas y la generación **previstos** en el origen (ver docstring del módulo)."""
    conductores = tabla_conductores(gas, detalle)
    spot = gas["gas_spot_eur_mwh"].dropna()

    def prever(origen: pd.Timestamp) -> pd.DataFrame:
        historia = conductores.loc[:origen]
        if len(historia) < 48 or origen > conductores.index.max():
            return _vacio()
        X = _variables_precio(historia)
        y = np.log(precio.reindex(X.index))
        conocidos = y.notna()
        modelo = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(X[conocidos][COLUMNAS_PRECIO], y[conocidos])
        filas = anual._filas_futuras("ES", origen)
        futuro = pd.DataFrame(index=pd.DatetimeIndex(filas["mes"]))
        futuro["gas"] = _ets_log(spot.loc[:origen], anual.HORIZONTE, 96)
        for c in (*CUOTAS, "total"):
            futuro[c] = _ets_log(historia[c].clip(lower=1.0), anual.HORIZONTE, 60)
        filas["prevision"] = np.exp(modelo.predict(_variables_precio(futuro)[COLUMNAS_PRECIO]))
        return filas

    return prever


def diagnostico_precio(gas: pd.DataFrame, detalle: pd.DataFrame, precio: pd.Series, desde: str, hasta: str) -> float:
    """Acierto (%) del precio estructural con el gas y la generación **reales** de cada mes (no es una previsión: usa
    datos del propio mes). Cada mes se predice con un modelo entrenado solo con los meses anteriores. Sirve para saber
    cuánto del precio explican el gas y el tiempo si se supieran."""
    X = _variables_precio(tabla_conductores(gas, detalle))
    y = np.log(precio.reindex(X.index))
    previsto = {}
    for t in X.index[36:]:
        anteriores = X.index[(X.index < t) & y.notna().to_numpy()]
        modelo = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(X.loc[anteriores, COLUMNAS_PRECIO], y.loc[anteriores])
        previsto[t] = float(np.exp(modelo.predict(X.loc[[t], COLUMNAS_PRECIO]))[0])
    serie = pd.Series(previsto).loc[desde:hasta]
    return acierto_pct(precio.reindex(serie.index), serie)


def evaluar_todo(gas: pd.DataFrame, detalle: pd.DataFrame, reserva_nacional: pd.Series) -> dict[str, Any]:
    """Backtesting a 1 año del gas y de las tres tecnologías del tiempo (mismo protocolo que el resto)."""
    reales_g = reales_gas(gas)
    res_gas = anual.evaluar(candidatos_gas(gas), reales_g, anual.definir_origenes(reales_g["mes"].max()), "mae")
    tiempo = {}
    for t in TECNOLOGIAS_TIEMPO:
        reales_t = reales_tecnologia(detalle, t)
        tiempo[t] = anual.evaluar(candidatos_tecnologia(reales_t, reserva_nacional), reales_t, anual.definir_origenes(reales_t["mes"].max()), "mae")
    return {"gas": res_gas, "tiempo": tiempo}
