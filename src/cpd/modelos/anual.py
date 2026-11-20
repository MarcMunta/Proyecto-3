"""Previsión a 1 año (12 meses, mes a mes) con el menor error posible: demanda por comunidad y precio de la luz.

Protocolo común (fases 7 y 8; R-6):
- **Orígenes de validación:** 24 orígenes mensuales consecutivos (dos años). En cada origen `r` cada modelo se
  entrena solo con datos hasta `r` y prevé los 12 meses siguientes. Sus meses objetivo terminan antes del test.
- **Test:** un único origen, 12 meses antes del último dato; se mira una vez.
- **Candidatos:** baselines, modelos estadísticos (ETS de Holt-Winters amortiguado), ML (Ridge, gradient boosting)
  y la **combinación** (media) de los 3 mejores en validación. Combinar modelos suele reducir el error porque sus
  errores no coinciden (recomendación, no viene de clase).
- **Elección:** la combinación, salvo que un modelo individual tenga más de un 5 % menos de error medio en
  validación (MAPE para la demanda, MAE en €/MWh para el precio).
- **Intervalo:** cuantiles 10-90 % del error relativo del modelo elegido en validación, por horizonte.

Todas las comparaciones usan exactamente las mismas filas (serie, mes, origen) para todos los modelos.
"""

from __future__ import annotations

import datetime as dt
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cpd.features import demanda as fdem
from cpd.features import precio as fpre
from cpd.modelos.metricas import metricas_regresion

SEMILLA: int = 42
HORIZONTE: int = 12
MIEMBROS_COMBINACION: int = 3
# Un modelo solo sustituye a la combinación si mejora su error de validación en más de un 5 %: con pocos orígenes
# (y muy correlacionados) una diferencia menor puede ser casualidad, y la combinación es más robusta.
MARGEN_COMBINACION: float = 0.05

# Función de un candidato: origen r → DataFrame con serie, mes, horizonte_meses, prevision (solo datos ≤ r).
Candidato = Callable[[pd.Timestamp], pd.DataFrame]


@dataclass(frozen=True)
class Origenes:
    """Orígenes de validación (varios) y de test (uno)."""

    validacion: tuple[pd.Timestamp, ...]
    test: pd.Timestamp
    fin: pd.Timestamp

    def como_texto(self) -> dict[str, str]:
        """Orígenes y meses objetivo en AAAA-MM."""
        mes = lambda t: pd.Timestamp(t).strftime("%Y-%m")  # noqa: E731
        return {
            "origenes_validacion": f"{mes(self.validacion[0])} a {mes(self.validacion[-1])} ({len(self.validacion)} orígenes)",
            "meses_validacion": f"{mes(self.validacion[0] + pd.DateOffset(months=1))} a {mes(self.validacion[-1] + pd.DateOffset(months=HORIZONTE))}",
            "origen_test": mes(self.test),
            "meses_test": f"{mes(self.test + pd.DateOffset(months=1))} a {mes(self.fin)}",
        }


ORIGENES_VALIDACION: int = 24


def definir_origenes(fin: pd.Timestamp, n_validacion: int = ORIGENES_VALIDACION) -> Origenes:
    """Test = origen `fin − 12`; validación = los `n_validacion` orígenes que terminan en `fin − 24`, de forma que
    ningún mes objetivo de validación cae en el test.

    Se usan 24 orígenes (dos años) y no 12: con 12 orígenes consecutivos la validación solo veía un periodo de
    precios estable y elegía un modelo (gradient boosting) que luego fue el peor en test. Esta decisión se tomó
    después de ver ese primer test, así que el test del precio no es del todo independiente (se dice en el informe).
    """
    test = fin - pd.DateOffset(months=HORIZONTE)
    ultimo = fin - pd.DateOffset(months=2 * HORIZONTE)
    validacion = tuple(ultimo - pd.DateOffset(months=k) for k in range(n_validacion - 1, -1, -1))
    return Origenes(validacion, test, fin)


def _ets(log_serie: pd.Series, pasos: int) -> np.ndarray:
    """Holt-Winters con tendencia amortiguada y estacionalidad aditiva sobre el logaritmo (statsmodels)."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = ExponentialSmoothing(
            log_serie.to_numpy(dtype=float), trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
            initialization_method="estimated",
        ).fit()
    return np.exp(modelo.forecast(pasos))


def _filas_futuras(serie: str, origen: pd.Timestamp) -> pd.DataFrame:
    meses = pd.date_range(origen + pd.DateOffset(months=1), periods=HORIZONTE, freq="MS")
    return pd.DataFrame({"serie": serie, "mes": meses, "horizonte_meses": range(1, HORIZONTE + 1)})


# ---------------------------------------------------------------------------------------------- demanda por CCAA


def candidatos_demanda(serie: pd.DataFrame) -> dict[str, Candidato]:
    """Candidatos para la demanda mensual de cada comunidad (MWh).

    Args:
        serie: salida de `cpd.features.demanda.preparar_serie_modelo` (`codigo_ccaa`, `mes`, `demanda_mwh`).
    """
    por_ccaa = {c: g.set_index("mes")["demanda_mwh"].sort_index() for c, g in serie.groupby("codigo_ccaa")}
    tablas = {h: fdem.construir_features_demanda(serie, h, meses_futuros=HORIZONTE) for h in range(1, HORIZONTE + 1)}

    def _hasta(origen: pd.Timestamp) -> dict[str, pd.Series]:
        return {c: s.loc[:origen] for c, s in por_ccaa.items() if len(s.loc[:origen]) >= 36 and s.index.max() >= origen}

    def estacional(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = s.reindex(filas["mes"] - pd.DateOffset(months=12)).to_numpy()
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def estacional_tendencia(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            ultimo, anterior = s.iloc[-12:].sum(), s.iloc[-24:-12].sum()
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = s.reindex(filas["mes"] - pd.DateOffset(months=12)).to_numpy() * (ultimo / anterior)
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def ets(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = _ets(np.log(s.iloc[-96:]), HORIZONTE)  # 8 años como máximo
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def ridge(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for h, tabla in tablas.items():
            columnas = fdem.columnas_features(tabla)
            entrenamiento = tabla[(tabla["mes"] <= origen)].dropna(subset=["objetivo_log_ratio"])
            prever = tabla[tabla["mes_referencia"] == origen]
            if entrenamiento.empty or prever.empty:
                continue
            modelo = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(entrenamiento[columnas], entrenamiento["objetivo_log_ratio"])
            partes.append(
                pd.DataFrame(
                    {
                        "serie": prever["codigo_ccaa"].to_numpy(),
                        "mes": prever["mes"].to_numpy(),
                        "horizonte_meses": h,
                        "prevision": np.exp(modelo.predict(prever[columnas])) * prever["nivel_mwh"].to_numpy(),
                    }
                )
            )
        return pd.concat(partes, ignore_index=True)

    return {"estacional": estacional, "estacional_tendencia": estacional_tendencia, "ets": ets, "ridge": ridge}


def reales_demanda(serie: pd.DataFrame) -> pd.DataFrame:
    """Valores reales para evaluar (sin los meses imputados: nunca se evalúa contra un dato inventado)."""
    datos = serie[~serie["imputado"]] if "imputado" in serie.columns else serie
    return datos.rename(columns={"codigo_ccaa": "serie", "demanda_mwh": "real"})[["serie", "mes", "real"]]


# ------------------------------------------------------------------------------------------------ precio de la luz


def candidatos_precio(mensual: pd.DataFrame) -> dict[str, Candidato]:
    """Candidatos para el precio spot medio mensual (€/MWh). Si `mensual` tiene las columnas de gas
    (`cpd.features.precio.series_gas`), los modelos de ML las usan."""
    precio = mensual["precio_eur_mwh"].dropna()
    tabla = fpre.construir_features_precio(mensual, meses_futuros=HORIZONTE)
    columnas = fpre.columnas_features(tabla)
    columnas_gas = [c for c in columnas if c.startswith("f_gas")]

    def _salida(filas: pd.DataFrame, prevision: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame({"serie": "ES", "mes": filas["mes"].to_numpy(), "horizonte_meses": filas["horizonte_meses"].to_numpy(), "prevision": prevision})

    def _baseline(nombre: str) -> Candidato:
        def prever(origen: pd.Timestamp) -> pd.DataFrame:
            filas = _filas_futuras("ES", origen)
            hasta = precio.loc[:origen]
            if nombre == "media_12m":
                filas["prevision"] = hasta.iloc[-12:].mean()
            elif nombre == "naive":
                filas["prevision"] = hasta.iloc[-1]
            else:  # estacional
                filas["prevision"] = hasta.reindex(filas["mes"] - pd.DateOffset(months=12)).to_numpy()
            return filas

        return prever

    def ets(origen: pd.Timestamp) -> pd.DataFrame:
        filas = _filas_futuras("ES", origen)
        filas["prevision"] = _ets(np.log(precio.loc[:origen]), HORIZONTE)
        return filas

    def _ml(modelo: Any, cols: list[str]) -> Candidato:
        def prever(origen: pd.Timestamp) -> pd.DataFrame:
            entrenamiento = tabla[tabla["mes"] <= origen].dropna(subset=["objetivo_log_ratio"])
            filas = tabla[tabla["mes_origen"] == origen]
            if len(entrenamiento) < 24 or filas.empty:  # sin historia suficiente (p. ej. antes de los futuros de gas)
                return pd.DataFrame(columns=["serie", "mes", "horizonte_meses", "prevision"])
            ajustado = clone(modelo).fit(entrenamiento[cols].to_numpy(dtype=float), entrenamiento["objetivo_log_ratio"].to_numpy(dtype=float))
            return _salida(filas, np.exp(ajustado.predict(filas[cols].to_numpy(dtype=float))) * filas["nivel_eur_mwh"].to_numpy())

        return prever

    candidatos: dict[str, Candidato] = {n: _baseline(n) for n in ("media_12m", "naive", "estacional")}
    candidatos["ets"] = ets
    candidatos["ridge"] = _ml(make_pipeline(StandardScaler(), Ridge(alpha=100.0)), columnas)
    if columnas_gas:
        base = ["f_mes_sin", "f_mes_cos", "f_horizonte", "f_ultimo"]
        candidatos["ridge_gas"] = _ml(make_pipeline(StandardScaler(), Ridge(alpha=10.0)), base + columnas_gas)
        candidatos["gradient_boosting"] = _ml(
            HistGradientBoostingRegressor(learning_rate=0.05, max_depth=2, max_iter=200, min_samples_leaf=30, random_state=SEMILLA), columnas
        )
    return candidatos


def reales_precio(mensual: pd.DataFrame) -> pd.DataFrame:
    """Precio real mensual (€/MWh) en el formato de evaluación."""
    precio = mensual["precio_eur_mwh"].dropna()
    return pd.DataFrame({"serie": "ES", "mes": precio.index, "real": precio.to_numpy()})


# ------------------------------------------------------------------------------------------------------ evaluación


def _metricas(datos: pd.DataFrame) -> dict[str, float]:
    return {"n": len(datos), **metricas_regresion(datos["real"], datos["prevision"])}


def evaluar(candidatos: dict[str, Candidato], reales: pd.DataFrame, origenes: Origenes, metrica: str) -> dict[str, Any]:
    """Backtesting de 1 año de todos los candidatos, combinación de los mejores y elección con la validación.

    Args:
        candidatos: nombre → función de previsión desde un origen.
        reales: `serie`, `mes`, `real`.
        origenes: salida de `definir_origenes`.
        metrica: `mape_pct` o `mae` (la que decide).

    Returns:
        `predicciones` (todas, con `real`), `metricas` (modelo × partición), `por_horizonte` (modelo × partición × h),
        `ranking` (validación), `miembros` de la combinación, `elegido` y `residuos_log` (por horizonte, elegido).
    """
    partes = []
    for nombre, prever in candidatos.items():
        for particion, lista in (("validacion", origenes.validacion), ("test", (origenes.test,))):
            for origen in lista:
                p = prever(origen)
                if p is not None and not p.empty:
                    partes.append(p.assign(modelo=nombre, origen=origen, particion=particion))
    pred = pd.concat(partes, ignore_index=True).merge(reales, on=["serie", "mes"], how="inner").dropna(subset=["prevision", "real"])
    # Mismas filas para todos: solo (serie, mes, origen) que tienen todos los modelos.
    claves = ["serie", "mes", "origen", "particion"]
    completos = pred.groupby(claves)["modelo"].nunique() == len(candidatos)
    pred = pred.set_index(claves).loc[completos[completos].index].reset_index()

    ranking = pred[pred["particion"] == "validacion"].groupby("modelo").apply(lambda d: _metricas(d)[metrica], include_groups=False).sort_values()
    miembros = list(ranking.index[:MIEMBROS_COMBINACION])
    combinacion = (
        pred[pred["modelo"].isin(miembros)]
        .groupby([*claves, "horizonte_meses"], as_index=False)
        .agg(prevision=("prevision", "mean"), real=("real", "first"))
        .assign(modelo="combinacion")
    )
    pred = pd.concat([pred, combinacion], ignore_index=True)

    metricas = pred.groupby(["modelo", "particion"]).apply(lambda d: pd.Series(_metricas(d)), include_groups=False).reset_index()
    por_horizonte = (
        pred.groupby(["modelo", "particion", "horizonte_meses"]).apply(lambda d: pd.Series(_metricas(d)), include_groups=False).reset_index()
    )
    en_validacion = metricas[metricas["particion"] == "validacion"].set_index("modelo")[metrica].sort_values()
    # Regla: la combinación, salvo que un modelo solo la mejore claramente (más de MARGEN_COMBINACION) en validación.
    mejor_individual = en_validacion.drop("combinacion")
    if mejor_individual.iloc[0] < en_validacion["combinacion"] * (1 - MARGEN_COMBINACION):
        elegido = str(mejor_individual.index[0])
    else:
        elegido = "combinacion"
    val = pred[(pred["modelo"] == elegido) & (pred["particion"] == "validacion")]
    residuos = (np.log(val["real"]) - np.log(val["prevision"])).groupby(val["horizonte_meses"]).apply(lambda r: r.to_numpy())
    return {
        "predicciones": pred,
        "metricas": metricas,
        "por_horizonte": por_horizonte,
        "ranking": en_validacion,
        "miembros": miembros,
        "elegido": elegido,
        "residuos_log": residuos.to_dict(),
        "metrica": metrica,
        "origenes": origenes.como_texto(),
    }


def intervalo_media_anual(resultado: dict[str, Any], cuantiles: tuple[float, float] = (0.1, 0.9)) -> pd.DataFrame:
    """Rango de la media de los 12 meses: cuantiles, por serie, del cociente real / previsto de la media anual del
    modelo elegido en los orígenes de validación (con todas las series juntas si una tiene pocos orígenes).

    Returns:
        `serie`, `factor_inferior`, `factor_superior` (multiplican la media prevista).
    """
    pred = resultado["predicciones"]
    val = pred[(pred["modelo"] == resultado["elegido"]) & (pred["particion"] == "validacion")]
    medias = val.groupby(["serie", "origen"]).agg(real=("real", "mean"), prevision=("prevision", "mean"), n=("real", "size"))
    medias = medias[medias["n"] == HORIZONTE]
    cociente = medias["real"] / medias["prevision"]
    global_bajo, global_alto = np.quantile(cociente, cuantiles)
    filas = []
    for serie, c in cociente.groupby(level="serie"):
        bajo, alto = (np.quantile(c, cuantiles) if len(c) >= 6 else (global_bajo, global_alto))
        filas.append({"serie": serie, "factor_inferior": float(bajo), "factor_superior": float(alto)})
    return pd.DataFrame(filas)


def prevision_final(
    candidatos: dict[str, Candidato], resultado: dict[str, Any], origen_por_serie: dict[str, pd.Timestamp], cuantiles: tuple[float, float] = (0.1, 0.9)
) -> pd.DataFrame:
    """Previsión de los 12 meses siguientes al último dato de cada serie con el modelo elegido (o la combinación).

    Returns:
        `serie`, `mes`, `horizonte_meses`, `prevision`, `inferior`, `superior`, `modelo`, `origen`, `generado_en`.
    """
    nombres = resultado["miembros"] if resultado["elegido"] == "combinacion" else [resultado["elegido"]]
    partes = []
    for origen in sorted(set(origen_por_serie.values())):
        series = [s for s, o in origen_por_serie.items() if o == origen]
        juntas = pd.concat([candidatos[n](origen).assign(miembro=n) for n in nombres])
        juntas = juntas[juntas["serie"].isin(series)]
        partes.append(juntas.groupby(["serie", "mes", "horizonte_meses"], as_index=False)["prevision"].mean().assign(origen=origen))
    salida = pd.concat(partes, ignore_index=True)
    bajo = salida["horizonte_meses"].map(lambda h: np.quantile(resultado["residuos_log"][h], cuantiles[0]))
    alto = salida["horizonte_meses"].map(lambda h: np.quantile(resultado["residuos_log"][h], cuantiles[1]))
    return salida.assign(
        inferior=salida["prevision"] * np.exp(bajo),
        superior=salida["prevision"] * np.exp(alto),
        modelo=resultado["elegido"],
        generado_en=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    )
