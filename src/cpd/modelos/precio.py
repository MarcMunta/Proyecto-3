"""Previsión del precio medio mensual de la electricidad (spot, España peninsular) a 1-12 meses vista.

Por qué importa: el coste de la energía es la mayor parte del OPEX de un CPD, y el simulador usa hoy como precio
la **media de los últimos 12 meses**. Este módulo comprueba si se puede prever mejor el precio del año siguiente.

Problema: con los datos conocidos hasta el mes `r`, prever el precio de cada mes `t = r + h` (`h` = 1 a 12) y su
media. Un solo modelo para todos los horizontes (el horizonte es una feature).

Partición temporal por mes objetivo (R-6), igual que en `cpd.modelos.demanda`: test = 12 últimos meses completos
(se usa una vez), validación = 12 anteriores, entrenamiento = el resto.

Métrica principal: **MAE en €/MWh** (el error se traslada directamente al coste de la energía; el MAPE se dispara
en los meses con precios muy bajos, p. ej. 16 €/MWh en febrero de 2026).

Modelos: baselines «último mes» (naive), «media de 12 meses» (lo que usa el simulador), «mismo mes del año anterior»
(estacional) y tendencia + estacionalidad (`cpd.forecast`); ML: Ridge y gradient boosting (recomendación, no viene
de clase).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cpd.features.precio import columnas_features, construir_features_precio
from cpd.forecast import prever_mensual
from cpd.modelos.demanda import Periodos, asignar_particion, comprobar_particiones
from cpd.modelos.metricas import metricas_regresion

SEMILLA: int = 42
BASELINES: tuple[str, ...] = ("naive", "media_12m", "estacional", "tendencia_estacionalidad")
HORIZONTES_INFORME: tuple[int, ...] = (1, 3, 6, 12)


def definir_periodos(mensual: pd.DataFrame, meses_test: int = 12, meses_validacion: int = 12) -> Periodos:
    """Partición por mes objetivo a partir del último mes con precio."""
    fin = mensual["precio_eur_mwh"].dropna().index.max()
    inicio_test = fin - pd.DateOffset(months=meses_test - 1)
    return Periodos(inicio_test - pd.DateOffset(months=meses_validacion), inicio_test, fin)


def candidatos_ml() -> dict[str, list[tuple[str, Any]]]:
    """Familias ML y sus configuraciones (se elige una por familia con la validación)."""
    return {
        "ridge": [(f"alpha={a:g}", make_pipeline(StandardScaler(), Ridge(alpha=a))) for a in (1.0, 10.0, 100.0, 1000.0)],
        "gradient_boosting": [
            (
                f"learning_rate={lr:g}, max_depth={d}",
                HistGradientBoostingRegressor(learning_rate=lr, max_depth=d, max_iter=200, min_samples_leaf=30, random_state=SEMILLA),
            )
            for lr in (0.03, 0.1)
            for d in (2, 3)
        ],
    }


def prevision_baseline(nombre: str, filas: pd.DataFrame, mensual: pd.DataFrame) -> np.ndarray:
    """Previsión (€/MWh) de un baseline para cada fila (origen r, mes t).

    - `naive`: el precio del mes `r`.
    - `media_12m`: la media de los 12 meses hasta `r` (lo que usa el simulador).
    - `estacional`: el precio del mismo mes del año anterior (`t − 12`).
    - `tendencia_estacionalidad`: `cpd.forecast.prever_mensual` ajustado con la serie hasta `r`.
    """
    nivel = filas["nivel_eur_mwh"].to_numpy(dtype=float)
    if nombre == "naive":
        return np.exp(filas["f_ultimo"].to_numpy(dtype=float)) * nivel
    if nombre == "media_12m":
        return nivel
    if nombre == "estacional":
        return np.exp(filas["f_mismo_mes_anio_anterior"].to_numpy(dtype=float)) * nivel
    if nombre == "tendencia_estacionalidad":
        serie = mensual["precio_eur_mwh"].dropna()
        cache: dict[pd.Timestamp, pd.Series | None] = {}
        salida = np.full(len(filas), np.nan)
        for i, (mes, origen) in enumerate(filas[["mes", "mes_origen"]].itertuples(index=False)):
            if origen not in cache:
                try:
                    cache[origen] = prever_mensual(serie.loc[:origen], horizonte_meses=12).set_index("fecha")["prevision"]
                except ValueError:
                    cache[origen] = None
            prevista = cache[origen]
            if prevista is not None and mes in prevista.index:
                salida[i] = prevista.loc[mes]
        return salida
    raise ValueError(f"Baseline desconocido: {nombre}")


def _ajustar(modelo: Any, filas: pd.DataFrame, columnas: list[str]) -> Any:
    copia = clone(modelo)
    copia.fit(filas[columnas].to_numpy(dtype=float), filas["objetivo_log_ratio"].to_numpy(dtype=float))
    return copia


def _predecir(modelo: Any, filas: pd.DataFrame, columnas: list[str]) -> np.ndarray:
    return np.exp(modelo.predict(filas[columnas].to_numpy(dtype=float))) * filas["nivel_eur_mwh"].to_numpy(dtype=float)


def _metricas(datos: pd.DataFrame, prevision: np.ndarray) -> dict[str, float]:
    valido = ~np.isnan(prevision)
    return {"n": int(valido.sum()), **metricas_regresion(datos["precio_eur_mwh"].to_numpy()[valido], prevision[valido])}


def evaluar(mensual: pd.DataFrame, periodos: Periodos) -> dict[str, Any]:
    """Elige con validación y evalúa en test (una vez) baselines y modelos ML para todos los horizontes.

    Returns:
        `metricas` (modelo × partición × horizonte, con «todos»), `predicciones` (validación y test, €/MWh),
        `seleccion` (MAE de validación de cada configuración ML), `elegido` y `residuos_log` por horizonte del
        elegido en validación (para el intervalo).
    """
    tabla = construir_features_precio(mensual)
    tabla["particion"] = asignar_particion(tabla["mes"], periodos)
    filas = tabla.dropna(subset=["objetivo_log_ratio"])
    filas = filas[filas["particion"] != "posterior"]
    comprobar_particiones(filas)
    columnas = columnas_features(tabla)
    entrenamiento = filas[filas["particion"] == "entrenamiento"]
    validacion = filas[filas["particion"] == "validacion"]
    test = filas[filas["particion"] == "test"]

    previsiones: dict[str, dict[str, np.ndarray]] = {}
    configuracion: dict[str, str] = {}
    familia: dict[str, str] = {}
    for nombre in BASELINES:
        previsiones[nombre] = {"validacion": prevision_baseline(nombre, validacion, mensual), "test": prevision_baseline(nombre, test, mensual)}
        configuracion[nombre], familia[nombre] = "—", "baseline"

    seleccion = []
    for nombre_familia, configs in candidatos_ml().items():
        mejor: tuple[float, str, Any] | None = None
        for etiqueta, modelo in configs:
            error = _metricas(validacion, _predecir(_ajustar(modelo, entrenamiento, columnas), validacion, columnas))["mae"]
            seleccion.append({"familia": nombre_familia, "configuracion": etiqueta, "mae_validacion_eur_mwh": error})
            if mejor is None or error < mejor[0]:
                mejor = (error, etiqueta, modelo)
        assert mejor is not None
        _, etiqueta, modelo = mejor
        previsiones[nombre_familia] = {
            "validacion": _predecir(_ajustar(modelo, entrenamiento, columnas), validacion, columnas),
            # Test: reentrenado con entrenamiento + validación; se evalúa una sola vez.
            "test": _predecir(_ajustar(modelo, pd.concat([entrenamiento, validacion]), columnas), test, columnas),
        }
        configuracion[nombre_familia], familia[nombre_familia] = etiqueta, "ml"

    metricas, predicciones = [], []
    for nombre, por_particion in previsiones.items():
        for particion, datos in (("validacion", validacion), ("test", test)):
            prevision = por_particion[particion]
            grupos = [("todos", np.ones(len(datos), dtype=bool))] + [
                (str(h), (datos["horizonte_meses"] == h).to_numpy()) for h in HORIZONTES_INFORME
            ]
            for etiqueta_h, mascara in grupos:
                metricas.append(
                    {"modelo": nombre, "familia": familia[nombre], "configuracion": configuracion[nombre], "particion": particion,
                     "horizonte": etiqueta_h, **_metricas(datos[mascara], prevision[mascara])}
                )
            predicciones.append(
                datos[["mes", "mes_origen", "horizonte_meses", "precio_eur_mwh"]].assign(modelo=nombre, particion=particion, prevision_eur_mwh=prevision)
            )
    metricas_df = pd.DataFrame(metricas)
    en_validacion = metricas_df.query("particion == 'validacion' and horizonte == 'todos'").set_index("modelo")["mae"]
    elegido = str(en_validacion.idxmin())
    residuos = pd.Series(np.log(validacion["precio_eur_mwh"].to_numpy()) - np.log(previsiones[elegido]["validacion"]), index=validacion.index)
    residuos_por_h = residuos.groupby(validacion["horizonte_meses"]).apply(lambda r: r.dropna().to_numpy())
    return {
        "metricas": metricas_df,
        "predicciones": pd.concat(predicciones, ignore_index=True),
        "seleccion": pd.DataFrame(seleccion),
        "elegido": {"modelo": elegido, "familia": familia[elegido], "configuracion": configuracion[elegido]},
        "residuos_log": residuos_por_h.to_dict(),
        "columnas": columnas,
        "n_filas": {"entrenamiento": len(entrenamiento), "validacion": len(validacion), "test": len(test)},
    }


def _modelo_de(nombre: str, configuracion: str) -> Any:
    return dict(candidatos_ml()[nombre])[configuracion]


def media_anual_por_origen(mensual: pd.DataFrame, configuraciones: dict[str, str], origenes: list[pd.Timestamp]) -> pd.DataFrame:
    """Precio medio previsto para los 12 meses siguientes a cada origen frente al real (backtesting).

    En cada origen `r` los modelos ML se reentrenan con los meses objetivo ≤ `r` (lo que se sabría entonces).

    Returns:
        Una fila por origen y modelo con `real_eur_mwh`, `prevision_eur_mwh` y `error_eur_mwh` (previsión − real).
    """
    tabla = construir_features_precio(mensual)
    columnas = columnas_features(tabla)
    conocidas = tabla.dropna(subset=["objetivo_log_ratio"])
    filas = []
    for origen in origenes:
        siguientes = tabla[tabla["mes_origen"] == origen]
        if len(siguientes) < 12 or siguientes["precio_eur_mwh"].isna().any():
            continue
        real = float(siguientes["precio_eur_mwh"].mean())
        previsiones = {nombre: prevision_baseline(nombre, siguientes, mensual) for nombre in BASELINES}
        entrenamiento = conocidas[conocidas["mes"] <= origen]
        for nombre, etiqueta in configuraciones.items():
            previsiones[nombre] = _predecir(_ajustar(_modelo_de(nombre, etiqueta), entrenamiento, columnas), siguientes, columnas)
        for nombre, prevision in previsiones.items():
            if np.isnan(prevision).any():
                continue
            media = float(np.mean(prevision))
            filas.append({"origen": origen.strftime("%Y-%m"), "modelo": nombre, "real_eur_mwh": real, "prevision_eur_mwh": media, "error_eur_mwh": media - real})
    return pd.DataFrame(filas)


def resumen_anual(prevision: pd.DataFrame, backtest: pd.DataFrame, mensual: pd.DataFrame, cuantiles: tuple[float, float] = (0.1, 0.9)) -> dict[str, Any]:
    """Precio medio previsto para los próximos 12 meses, con un rango sacado del backtesting del modelo elegido.

    El rango aplica a la previsión los cuantiles del cociente real / previsto de la media anual en los orígenes del
    backtesting (2020-2023: incluye la crisis de 2021-2022, así que es ancho a propósito).

    Returns:
        Diccionario con `media_prevista_eur_mwh`, `inferior_eur_mwh`, `superior_eur_mwh`, `ultimo_mes_eur_mwh`
        (escenario «el precio se queda como el último mes»), `ultimo_mes`, `modelo` y `origenes_backtesting`.
    """
    modelo = str(prevision["modelo"].iloc[0])
    media = float(prevision["prevision_eur_mwh"].mean())
    propio = backtest[backtest["modelo"] == modelo]
    cociente = propio["real_eur_mwh"] / propio["prevision_eur_mwh"]
    bajo, alto = (np.quantile(cociente, cuantiles) if len(cociente) else (np.nan, np.nan))
    ultimo = mensual["precio_eur_mwh"].dropna()
    return {
        "modelo": modelo,
        "media_prevista_eur_mwh": media,
        "inferior_eur_mwh": media * bajo,
        "superior_eur_mwh": media * alto,
        "ultimo_mes": ultimo.index.max().strftime("%Y-%m"),
        "ultimo_mes_eur_mwh": float(ultimo.iloc[-1]),
        "media_12m_actual_eur_mwh": float(ultimo.tail(12).mean()),
        "origenes_backtesting": int(len(propio)),
        "cuantiles": list(cuantiles),
    }


def prevision_final(mensual: pd.DataFrame, resultado: dict[str, Any], cuantiles: tuple[float, float] = (0.05, 0.95)) -> tuple[pd.DataFrame, Any]:
    """Precio previsto para los 12 meses siguientes al último dato, con el modelo elegido reentrenado con todo.

    El intervalo de cada mes sale de los cuantiles de los errores (en log) del elegido en validación para ese
    horizonte.

    Returns:
        (previsión con `mes`, `horizonte_meses`, `prevision_eur_mwh`, `inferior_eur_mwh`, `superior_eur_mwh`, `modelo`;
        modelo ajustado o None si el elegido es un baseline).
    """
    elegido = resultado["elegido"]
    tabla = construir_features_precio(mensual, meses_futuros=12)
    ultimo = mensual["precio_eur_mwh"].dropna().index.max()
    futuro = tabla[(tabla["mes_origen"] == ultimo)].sort_values("mes").copy()
    columnas = resultado["columnas"]
    ajustado = None
    if elegido["familia"] == "ml":
        ajustado = _ajustar(_modelo_de(elegido["modelo"], elegido["configuracion"]), tabla.dropna(subset=["objetivo_log_ratio"]), columnas)
        prevision = _predecir(ajustado, futuro, columnas)
    else:
        prevision = prevision_baseline(elegido["modelo"], futuro, mensual)
    bajo = np.array([np.quantile(resultado["residuos_log"][h], cuantiles[0]) for h in futuro["horizonte_meses"]])
    alto = np.array([np.quantile(resultado["residuos_log"][h], cuantiles[1]) for h in futuro["horizonte_meses"]])
    salida = futuro[["mes", "horizonte_meses"]].assign(
        prevision_eur_mwh=prevision,
        inferior_eur_mwh=prevision * np.exp(bajo),
        superior_eur_mwh=prevision * np.exp(alto),
        modelo=elegido["modelo"],
        configuracion=elegido["configuracion"],
        ultimo_dato_real=ultimo.strftime("%Y-%m"),
        media_12m_actual_eur_mwh=float(mensual["precio_eur_mwh"].loc[:ultimo].tail(12).mean()),
        generado_en=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    return salida.reset_index(drop=True), ajustado
