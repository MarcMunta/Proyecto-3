"""Sostenibilidad operativa del CPD a medio plazo (10 años) por provincia (objetivo A3, añadido el 18/11/2026).

A 1 año ya se prevén el PUE, el consumo y las emisiones (`cpd.modelos.operacion`). A medio plazo lo que cambia la
operación de un CPD es el **clima** (temperatura → PUE → consumo) y el **agua** disponible. Se prevén a 10 años:

- **Temperatura media anual por provincia** (°C): NASA POWER mensual desde 1981 (`clima_mensual_largo.csv`).
- **Reserva media anual de los embalses por ámbito** (%): MITECO desde 1988 (`reservas_ambito_mensual.csv`).

y se encadena la temperatura con las fórmulas del simulador (`pue_estimado`, `consumo_anual_mwh`).

Protocolo (mismo criterio que el resto, R-6):
- **Test**: el último origen con los 10 años siguientes conocidos (p. ej. 2015 → 2016-2025). Ningún modelo lo ve.
- **Validación**: orígenes anteriores cuyos 10 años previstos terminan antes del test (p. ej. 1995-2005 → hasta 2015),
  para que la elección no mire ningún año del test.
- **Candidatos**: último año, media de 10 años, media larga (30 años o toda la historia), tendencia lineal de 30 años,
  media de 10 años más la tendencia de 30 y Holt amortiguado; y la combinación de los 3 mejores por MAE de validación
  (la combinación salvo que un modelo la mejore en más de un 5 %, como en `cpd.modelos.anual`).
- **Acierto** = 100 × (1 − WAPE) con todos los años y horizontes; también el MAE en °C o en puntos de reserva.
- **Intervalo 10-90 %** por horizonte con los errores de validación del modelo elegido; nunca se estrecha al alargar.

Emisiones a 10 años: no se prevén. El mix por comunidad solo existe desde 2015 (11 años): no se puede validar un
horizonte de 10 años, y depende sobre todo de decisiones políticas (PNIEC), no de la historia.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from cpd import simulator as sim
from cpd.modelos.anual import MARGEN_COMBINACION, MIEMBROS_COMBINACION
from cpd.modelos.metricas import acierto_pct

HORIZONTE_ANIOS: int = 10
VENTANA_LARGA: int = 30
PRIMER_ORIGEN_TEMPERATURA: int = 1995
PRIMER_ORIGEN_RESERVAS: int = 1997
CUANTILES: tuple[float, float] = (0.1, 0.9)

ModeloAnual = Callable[[pd.Series, int], np.ndarray]


def anual_completo(mensual: pd.DataFrame, columna_fecha: str, columna_serie: str, columna_valor: str) -> pd.DataFrame:
    """Media anual de cada serie con los años que tienen los 12 meses.

    Returns:
        Tabla ancha: índice año (int), una columna por serie (NaN en los años incompletos).
    """
    datos = mensual.assign(anio=pd.to_datetime(mensual[columna_fecha]).dt.year).dropna(subset=[columna_valor])
    agregado = datos.groupby([columna_serie, "anio"])[columna_valor].agg(["mean", "count"])
    agregado = agregado[agregado["count"] == 12]["mean"].unstack(columna_serie)
    return agregado.sort_index()


def _holt_aditivo(h: pd.Series, n: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ajuste = ExponentialSmoothing(h.to_numpy(dtype=float), trend="add", damped_trend=True, initialization_method="estimated").fit()
    return ajuste.forecast(n)


def _pendiente(h: pd.Series) -> float:
    ventana = h.iloc[-VENTANA_LARGA:]
    return float(np.polyfit(ventana.index.to_numpy(dtype=float), ventana.to_numpy(dtype=float), 1)[0])


def candidatos() -> dict[str, ModeloAnual]:
    """Candidatos: función (historia anual hasta el origen, nº de años) → previsión de cada año."""

    def sin_cambio(h: pd.Series, n: int) -> np.ndarray:
        return np.repeat(float(h.iloc[-1]), n)

    def media_10(h: pd.Series, n: int) -> np.ndarray:
        return np.repeat(float(h.iloc[-10:].mean()), n)

    def media_larga(h: pd.Series, n: int) -> np.ndarray:
        return np.repeat(float(h.iloc[-VENTANA_LARGA:].mean()), n)

    def tendencia_30(h: pd.Series, n: int) -> np.ndarray:
        ventana = h.iloc[-VENTANA_LARGA:]
        pendiente, corte = np.polyfit(ventana.index.to_numpy(dtype=float), ventana.to_numpy(dtype=float), 1)
        return corte + pendiente * (h.index[-1] + np.arange(1, n + 1))

    def media_10_con_tendencia(h: pd.Series, n: int) -> np.ndarray:
        # La media de 10 años está centrada 4,5 años antes del origen: se le suma la pendiente de 30 años hasta cada año.
        return float(h.iloc[-10:].mean()) + _pendiente(h) * (4.5 + np.arange(1, n + 1))

    return {
        "sin_cambio": sin_cambio, "media_10_anios": media_10, "media_larga": media_larga, "tendencia_30_anios": tendencia_30,
        "media_10_con_tendencia": media_10_con_tendencia, "holt_amortiguado": _holt_aditivo,
    }


def backtesting(anual: pd.DataFrame, origenes: list[int], modelos: dict[str, ModeloAnual] | None = None) -> pd.DataFrame:
    """Previsión a 10 años de cada serie y candidato desde cada origen, con el valor real.

    Returns:
        `modelo`, `serie`, `origen`, `anio`, `horizonte_anios`, `prevision`, `real`.
    """
    modelos = modelos or candidatos()
    ultimo = int(anual.index.max())
    filas = []
    for serie in anual.columns:
        s = anual[serie].dropna()
        for origen in origenes:
            historia = s.loc[:origen]
            pasos = min(HORIZONTE_ANIOS, ultimo - origen)
            if len(historia) < 10 or pasos < 1 or historia.index[-1] != origen:
                continue
            for nombre, modelo in modelos.items():
                previsto = modelo(historia, pasos)
                for h in range(1, pasos + 1):
                    anio = origen + h
                    if anio in s.index:
                        filas.append({"modelo": nombre, "serie": serie, "origen": origen, "anio": anio, "horizonte_anios": h, "prevision": float(previsto[h - 1]), "real": float(s.loc[anio])})
    return pd.DataFrame(filas)


def _con_combinacion(bt: pd.DataFrame, miembros: list[str]) -> pd.DataFrame:
    combinacion = (
        bt[bt["modelo"].isin(miembros)]
        .groupby(["serie", "origen", "anio", "horizonte_anios"], as_index=False)
        .agg(prevision=("prevision", "mean"), real=("real", "first"))
        .assign(modelo="combinacion")
    )
    return pd.concat([bt, combinacion], ignore_index=True)


def evaluar(anual: pd.DataFrame, primer_origen: int, modelos: dict[str, ModeloAnual] | None = None) -> dict[str, Any]:
    """Validación y test a 10 años, combinación de los 3 mejores y elección solo con la validación.

    Returns:
        `predicciones` (con `particion`), `metricas` (modelo × partición: MAE y acierto), `miembros`, `elegido`,
        `acierto_validacion`, `acierto_test`, `mae_validacion`, `mae_test`, `origenes_validacion`, `origen_test`.
    """
    ultimo = int(anual.index.max())
    origen_test = ultimo - HORIZONTE_ANIOS
    origenes_val = list(range(primer_origen, origen_test - HORIZONTE_ANIOS + 1))
    val = backtesting(anual, origenes_val, modelos)
    test = backtesting(anual, [origen_test], modelos)
    mae_val = val.assign(e=(val["prevision"] - val["real"]).abs()).groupby("modelo")["e"].mean().sort_values()
    miembros = list(mae_val.index[:MIEMBROS_COMBINACION])
    pred = pd.concat([_con_combinacion(val, miembros).assign(particion="validacion"), _con_combinacion(test, miembros).assign(particion="test")], ignore_index=True)
    filas = []
    for (modelo, particion), d in pred.groupby(["modelo", "particion"]):
        filas.append({"modelo": modelo, "particion": particion, "mae": float((d["prevision"] - d["real"]).abs().mean()), "acierto": acierto_pct(d["real"], d["prevision"])})
    metricas = pd.DataFrame(filas)
    m = metricas.set_index(["modelo", "particion"])
    individual = m.xs("validacion", level="particion")["mae"].drop("combinacion").sort_values()
    elegido = str(individual.index[0]) if individual.iloc[0] < m.loc[("combinacion", "validacion"), "mae"] * (1 - MARGEN_COMBINACION) else "combinacion"
    return {
        "predicciones": pred, "metricas": metricas, "miembros": miembros, "elegido": elegido,
        "acierto_validacion": float(m.loc[(elegido, "validacion"), "acierto"]), "acierto_test": float(m.loc[(elegido, "test"), "acierto"]),
        "mae_validacion": float(m.loc[(elegido, "validacion"), "mae"]), "mae_test": float(m.loc[(elegido, "test"), "mae"]),
        "origenes_validacion": origenes_val, "origen_test": origen_test,
    }


def acierto_media_decada(resultado: dict[str, Any]) -> dict[str, float]:
    """Acierto (100 − WAPE) de la **media de los 10 años** previstos frente a la media real, por serie y origen, con el
    modelo elegido. Es la cifra que importa para una inversión a 10 años (el agua media de la década), no el año suelto;
    se informa además del acierto año a año, que no se esconde."""
    pred = resultado["predicciones"]
    pred = pred[pred["modelo"] == resultado["elegido"]]
    salida = {}
    for particion, d in pred.groupby("particion"):
        medias = d.groupby(["serie", "origen"]).agg(prevision=("prevision", "mean"), real=("real", "mean"), n=("real", "size"))
        medias = medias[medias["n"] == HORIZONTE_ANIOS]
        salida[particion] = acierto_pct(medias["real"], medias["prevision"])
    return {"acierto_decada_validacion": salida["validacion"], "acierto_decada_test": salida["test"]}


def prevision(anual: pd.DataFrame, resultado: dict[str, Any], modelos: dict[str, ModeloAnual] | None = None, limites: tuple[float, float] | None = None) -> pd.DataFrame:
    """Previsión de los 10 años siguientes al último año completo de cada serie, con intervalo 10-90 %.

    El intervalo suma a la previsión los cuantiles del error (real − previsto) de validación del modelo elegido en cada
    horizonte (todas las series juntas) y nunca se estrecha al alargar el plazo. `limites` recorta valores imposibles
    (p. ej. 0-100 % de reserva).

    Returns:
        `serie`, `anio`, `horizonte_anios`, `prevision`, `inferior`, `superior`.
    """
    modelos = modelos or candidatos()
    nombres = resultado["miembros"] if resultado["elegido"] == "combinacion" else [resultado["elegido"]]
    pred = resultado["predicciones"]
    errores = pred[(pred["modelo"] == resultado["elegido"]) & (pred["particion"] == "validacion")].assign(e=lambda d: d["real"] - d["prevision"])
    bandas, bajo_previo, alto_previo = {}, 0.0, 0.0
    for h in range(1, HORIZONTE_ANIOS + 1):
        bajo, alto = np.quantile(errores.loc[errores["horizonte_anios"] == h, "e"], CUANTILES)
        bajo_previo, alto_previo = min(bajo, bajo_previo, 0.0), max(alto, alto_previo, 0.0)
        bandas[h] = (bajo_previo, alto_previo)
    filas = []
    for serie in anual.columns:
        s = anual[serie].dropna()
        previsto = np.mean([modelos[n](s, HORIZONTE_ANIOS) for n in nombres], axis=0)
        for h in range(1, HORIZONTE_ANIOS + 1):
            p = float(previsto[h - 1])
            filas.append({"serie": serie, "anio": int(s.index[-1]) + h, "horizonte_anios": h, "prevision": p, "inferior": p + bandas[h][0], "superior": p + bandas[h][1]})
    tabla = pd.DataFrame(filas)
    if limites is not None:
        tabla[["prevision", "inferior", "superior"]] = tabla[["prevision", "inferior", "superior"]].clip(*limites)
    return tabla


def consumo_cpd(temp_media_c: pd.Series | np.ndarray, params: sim.CPDParams) -> np.ndarray:
    """Consumo anual (MWh) del CPD de referencia con una temperatura media anual (°C), vía el PUE del simulador."""
    return np.array([sim.consumo_anual_mwh(params.potencia_ti_mw, params.factor_carga, sim.pue_estimado(float(t), params.tipo_refrigeracion)) for t in temp_media_c])


def validar_consumo(resultado_temperatura: dict[str, Any], params: sim.CPDParams) -> dict[str, float]:
    """Acierto (100 − WAPE) del consumo del CPD calculado con la temperatura prevista frente a la real, de punta a punta,
    en validación y en test."""
    pred = resultado_temperatura["predicciones"]
    pred = pred[pred["modelo"] == resultado_temperatura["elegido"]]
    salida = {}
    for particion, d in pred.groupby("particion"):
        salida[particion] = acierto_pct(consumo_cpd(d["real"], params), consumo_cpd(d["prevision"], params))
    return {"acierto_validacion": salida["validacion"], "acierto_test": salida["test"]}


def operacion_10_anios(prev_temperatura: pd.DataFrame, temp_reciente: pd.Series, params: sim.CPDParams) -> pd.DataFrame:
    """PUE y consumo del CPD por provincia: media de los últimos 10 años (real) y previstos para el último de los 10.

    Args:
        prev_temperatura: salida de `prevision` para la temperatura (serie = provincia).
        temp_reciente: temperatura media de los últimos 10 años por provincia (°C).

    Returns:
        `codigo_provincia`, `temp_10a_c`, `temp_final_c` (año 10), `pue_10a`, `pue_final`, `consumo_10a_mwh`,
        `consumo_final_mwh`, `cambio_consumo_pct`.
    """
    final = prev_temperatura[prev_temperatura["horizonte_anios"] == HORIZONTE_ANIOS].set_index("serie")["prevision"]
    tabla = pd.DataFrame({"temp_10a_c": temp_reciente, "temp_final_c": final}).dropna()
    tabla["pue_10a"] = [sim.pue_estimado(t, params.tipo_refrigeracion) for t in tabla["temp_10a_c"]]
    tabla["pue_final"] = [sim.pue_estimado(t, params.tipo_refrigeracion) for t in tabla["temp_final_c"]]
    tabla["consumo_10a_mwh"] = consumo_cpd(tabla["temp_10a_c"], params)
    tabla["consumo_final_mwh"] = consumo_cpd(tabla["temp_final_c"], params)
    tabla["cambio_consumo_pct"] = 100 * (tabla["consumo_final_mwh"] / tabla["consumo_10a_mwh"] - 1)
    return tabla.rename_axis("codigo_provincia").reset_index()
