"""Previsión de la demanda eléctrica mensual por comunidad autónoma (fase 7, pregunta P5).

Problema: prever la demanda (MWh) de cada comunidad en el mes `t` con los datos conocidos hasta `t − h`, para
`h` = 1 mes (corto plazo) y `h` = 12 meses (un año vista). Previsión directa: un modelo por horizonte.

Partición temporal (R-6), definida a partir del último mes con dato real común a todas las comunidades:
- test: los 12 últimos meses (se usa una sola vez, con el modelo reentrenado con entrenamiento + validación);
- validación: los 12 meses anteriores (para elegir hiperparámetros y modelo);
- entrenamiento: todo lo anterior.

Modelos comparados con las mismas filas y particiones:
- baselines: «último valor» (naive), «mismo mes del año anterior» (estacional) y tendencia + estacionalidad
  (`cpd.forecast.prever_mensual`, reajustado en cada origen);
- ML: regresión Ridge (con escalado ajustado solo con entrenamiento, R-7) y gradient boosting de árboles
  (`HistGradientBoostingRegressor`). Recomendación, no viene de clase.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cpd.features.demanda import columnas_features, construir_features_demanda
from cpd.forecast import prever_mensual
from cpd.modelos.metricas import metricas_regresion

HORIZONTES: tuple[int, ...] = (1, 12)
SEMILLA: int = 42
BASELINES: tuple[str, ...] = ("naive", "estacional", "tendencia_estacionalidad")


@dataclass(frozen=True)
class Periodos:
    """Límites de la partición temporal (meses de inicio, incluidos)."""

    inicio_validacion: pd.Timestamp
    inicio_test: pd.Timestamp
    fin_test: pd.Timestamp

    def como_texto(self) -> dict[str, str]:
        """Periodos en formato AAAA-MM para los informes."""
        mes = lambda t: pd.Timestamp(t).strftime("%Y-%m")  # noqa: E731
        anterior = lambda t: (pd.Timestamp(t) - pd.DateOffset(months=1)).strftime("%Y-%m")  # noqa: E731
        return {
            "entrenamiento_hasta": anterior(self.inicio_validacion),
            "validacion": f"{mes(self.inicio_validacion)} a {anterior(self.inicio_test)}",
            "test": f"{mes(self.inicio_test)} a {mes(self.fin_test)}",
        }


def definir_periodos(serie: pd.DataFrame, meses_test: int = 12, meses_validacion: int = 12) -> Periodos:
    """Partición temporal a partir del último mes con dato real que tienen todas las comunidades.

    Args:
        serie: salida de `cpd.features.demanda.preparar_serie_modelo` (con `imputado`).
        meses_test: meses del periodo de test.
        meses_validacion: meses del periodo de validación.
    """
    reales = serie[~serie["imputado"]] if "imputado" in serie.columns else serie
    fin = reales.groupby("codigo_ccaa")["mes"].max().min()
    inicio_test = fin - pd.DateOffset(months=meses_test - 1)
    return Periodos(inicio_test - pd.DateOffset(months=meses_validacion), inicio_test, fin)


def asignar_particion(meses: pd.Series, periodos: Periodos) -> pd.Series:
    """`entrenamiento`, `validacion`, `test` o `posterior` (después del test) según el mes objetivo."""
    return pd.Series(
        np.select(
            [meses < periodos.inicio_validacion, meses < periodos.inicio_test, meses <= periodos.fin_test],
            ["entrenamiento", "validacion", "test"],
            default="posterior",
        ),
        index=meses.index,
    )


def comprobar_particiones(tabla: pd.DataFrame) -> None:
    """Comprueba R-6: fecha máxima de entrenamiento < mínima de validación ≤ máxima de validación < mínima de test.

    Raises:
        AssertionError: si las particiones se solapan o falta alguna.
    """
    rango = tabla.groupby("particion")["mes"].agg(["min", "max"])
    for nombre in ("entrenamiento", "validacion", "test"):
        assert nombre in rango.index, f"Falta la partición {nombre}"
    assert rango.loc["entrenamiento", "max"] < rango.loc["validacion", "min"], "Entrenamiento y validación se solapan"
    assert rango.loc["validacion", "max"] < rango.loc["test", "min"], "Validación y test se solapan"


def candidatos_ml() -> dict[str, list[tuple[str, Any]]]:
    """Familias de modelos ML y sus configuraciones (se elige una por familia con la validación)."""
    return {
        "ridge": [(f"alpha={a:g}", make_pipeline(StandardScaler(), Ridge(alpha=a))) for a in (0.1, 1.0, 10.0, 100.0)],
        "gradient_boosting": [
            (
                f"learning_rate={lr:g}, max_depth={d}",
                HistGradientBoostingRegressor(learning_rate=lr, max_depth=d, max_iter=300, min_samples_leaf=20, random_state=SEMILLA),
            )
            for lr in (0.05, 0.1)
            for d in (3, None)
        ],
    }


def _a_mwh(log_ratio: np.ndarray | pd.Series, nivel: pd.Series) -> np.ndarray:
    """Convierte `log(demanda / nivel)` en MWh."""
    return np.exp(np.asarray(log_ratio, dtype=float)) * nivel.to_numpy(dtype=float)


def prevision_baseline(nombre: str, filas: pd.DataFrame, serie: pd.DataFrame, horizonte: int) -> np.ndarray:
    """Previsión (MWh) de un baseline para las filas de la tabla de features.

    - `naive`: la demanda del mes `t − h` (último valor conocido).
    - `estacional`: la demanda del mismo mes del año anterior (`t − 12`); requiere `h ≤ 12`.
    - `tendencia_estacionalidad`: `cpd.forecast.prever_mensual` ajustado con la serie hasta `t − h`.
    """
    if nombre == "naive":
        return _a_mwh(filas[f"f_lag_{horizonte}"], filas["nivel_mwh"])
    if nombre == "estacional":
        if horizonte > 12:
            raise ValueError("El baseline estacional necesita un horizonte de 12 meses o menos")
        return _a_mwh(filas["f_lag_12"], filas["nivel_mwh"])
    if nombre == "tendencia_estacionalidad":
        historias = {c: g.set_index("mes")["demanda_mwh"].sort_index() for c, g in serie.groupby("codigo_ccaa")}
        cache: dict[tuple[str, pd.Timestamp], pd.Series | None] = {}
        salida = np.full(len(filas), np.nan)
        for i, (codigo, mes, referencia) in enumerate(filas[["codigo_ccaa", "mes", "mes_referencia"]].itertuples(index=False)):
            clave = (codigo, referencia)
            if clave not in cache:
                try:
                    prevision = prever_mensual(historias[codigo].loc[:referencia], horizonte_meses=horizonte)
                    cache[clave] = prevision.set_index("fecha")["prevision"]
                except ValueError:
                    cache[clave] = None
            serie_prevista = cache[clave]
            if serie_prevista is not None and mes in serie_prevista.index:
                salida[i] = serie_prevista.loc[mes]
        return salida
    raise ValueError(f"Baseline desconocido: {nombre}")


def _ajustar(modelo: Any, filas: pd.DataFrame, columnas: list[str]) -> Any:
    from sklearn.base import clone

    copia = clone(modelo)
    copia.fit(filas[columnas].to_numpy(dtype=float), filas["objetivo_log_ratio"].to_numpy(dtype=float))
    return copia


def _predecir(modelo: Any, filas: pd.DataFrame, columnas: list[str]) -> np.ndarray:
    return _a_mwh(modelo.predict(filas[columnas].to_numpy(dtype=float)), filas["nivel_mwh"])


def evaluar_horizonte(serie: pd.DataFrame, horizonte: int, periodos: Periodos) -> dict[str, Any]:
    """Entrena, elige con validación y evalúa en test (una vez) los baselines y los modelos ML de un horizonte.

    Args:
        serie: serie preparada (`preparar_serie_modelo`).
        horizonte: meses de antelación.
        periodos: partición temporal (`definir_periodos`).

    Returns:
        Diccionario con `metricas` (una fila por modelo y partición), `predicciones` (validación y test, MWh),
        `elegido` (nombre, familia y configuración del mejor modelo en validación), `seleccion` (MAPE de validación de
        cada configuración ML) y `residuos_validacion_log` del modelo elegido (para el intervalo).
    """
    tabla = construir_features_demanda(serie, horizonte)
    tabla["particion"] = asignar_particion(tabla["mes"], periodos)
    filas = tabla.dropna(subset=["objetivo_log_ratio"])
    filas = filas[filas["particion"] != "posterior"]
    comprobar_particiones(filas)
    columnas = columnas_features(tabla)
    entrenamiento = filas[filas["particion"] == "entrenamiento"]
    validacion = filas[filas["particion"] == "validacion"]
    test = filas[filas["particion"] == "test"]
    entrenamiento_val = pd.concat([entrenamiento, validacion])

    previsiones: dict[str, dict[str, np.ndarray]] = {}
    configuracion: dict[str, str] = {}
    familia: dict[str, str] = {}
    for nombre in BASELINES:
        previsiones[nombre] = {
            "validacion": prevision_baseline(nombre, validacion, serie, horizonte),
            "test": prevision_baseline(nombre, test, serie, horizonte),
        }
        configuracion[nombre] = "—"
        familia[nombre] = "baseline"

    seleccion = []
    for nombre_familia, configs in candidatos_ml().items():
        mejor: tuple[float, str, Any] | None = None
        for etiqueta, modelo in configs:
            ajustado = _ajustar(modelo, entrenamiento, columnas)
            error = metricas_regresion(validacion["demanda_mwh"], _predecir(ajustado, validacion, columnas))["mape_pct"]
            seleccion.append({"horizonte_meses": horizonte, "familia": nombre_familia, "configuracion": etiqueta, "mape_validacion_pct": error})
            if mejor is None or error < mejor[0]:
                mejor = (error, etiqueta, modelo)
        assert mejor is not None
        _, etiqueta, modelo = mejor
        previsiones[nombre_familia] = {
            "validacion": _predecir(_ajustar(modelo, entrenamiento, columnas), validacion, columnas),
            # Test: se reentrena con entrenamiento + validación y se evalúa una sola vez.
            "test": _predecir(_ajustar(modelo, entrenamiento_val, columnas), test, columnas),
        }
        configuracion[nombre_familia] = etiqueta
        familia[nombre_familia] = "ml"

    metricas, predicciones = [], []
    for nombre, por_particion in previsiones.items():
        for particion, datos in (("validacion", validacion), ("test", test)):
            prevision = por_particion[particion]
            valido = ~np.isnan(prevision)
            fila = {
                "horizonte_meses": horizonte,
                "modelo": nombre,
                "familia": familia[nombre],
                "configuracion": configuracion[nombre],
                "particion": particion,
                "n": int(valido.sum()),
                **metricas_regresion(datos["demanda_mwh"].to_numpy()[valido], prevision[valido]),
            }
            metricas.append(fila)
            predicciones.append(
                datos[["codigo_ccaa", "ccaa", "mes", "demanda_mwh"]].assign(
                    horizonte_meses=horizonte, modelo=nombre, particion=particion, prevision_mwh=prevision
                )
            )
    metricas_df = pd.DataFrame(metricas)
    en_validacion = metricas_df[metricas_df["particion"] == "validacion"].set_index("modelo")["mape_pct"]
    empatados = en_validacion[en_validacion <= en_validacion.min() + 1e-9].index
    # Con h = 12 el naive y el estacional son el mismo modelo: se nombra «estacional», que explica mejor qué hace.
    elegido = "estacional" if "estacional" in empatados else str(empatados[0])
    prev_val = previsiones[elegido]["validacion"]
    residuos = np.log(validacion["demanda_mwh"].to_numpy()) - np.log(prev_val)
    return {
        "horizonte": horizonte,
        "metricas": metricas_df,
        "predicciones": pd.concat(predicciones, ignore_index=True),
        "seleccion": pd.DataFrame(seleccion),
        "elegido": {"modelo": elegido, "familia": familia[elegido], "configuracion": configuracion[elegido]},
        "residuos_validacion_log": residuos[~np.isnan(residuos)],
        "columnas": columnas,
        "n_filas": {"entrenamiento": len(entrenamiento), "validacion": len(validacion), "test": len(test)},
    }


def backtesting(serie: pd.DataFrame, horizonte: int, configuracion_ml: dict[str, str], cortes: list[pd.Timestamp]) -> pd.DataFrame:
    """Repite la evaluación con varios orígenes del pasado (recomendación, no viene de clase).

    Para cada corte `c`, se entrena con los meses objetivo anteriores a `c` y se evalúan los 12 meses desde `c`.
    Las configuraciones ML son las elegidas en la validación principal.

    Returns:
        Una fila por corte y modelo con MAE, RMSE y MAPE.
    """
    tabla = construir_features_demanda(serie, horizonte).dropna(subset=["objetivo_log_ratio"])
    columnas = columnas_features(tabla)
    modelos = {nombre: dict(candidatos_ml()[nombre])[etiqueta] for nombre, etiqueta in configuracion_ml.items()}
    filas = []
    for corte in cortes:
        fin = corte + pd.DateOffset(months=11)
        entrenamiento = tabla[tabla["mes"] < corte]
        evaluacion = tabla[(tabla["mes"] >= corte) & (tabla["mes"] <= fin)]
        if entrenamiento.empty or evaluacion.empty:
            continue
        previsiones = {nombre: prevision_baseline(nombre, evaluacion, serie, horizonte) for nombre in BASELINES}
        for nombre, modelo in modelos.items():
            previsiones[nombre] = _predecir(_ajustar(modelo, entrenamiento, columnas), evaluacion, columnas)
        for nombre, prevision in previsiones.items():
            valido = ~np.isnan(prevision)
            filas.append(
                {
                    "horizonte_meses": horizonte,
                    "corte": corte.strftime("%Y-%m"),
                    "modelo": nombre,
                    **metricas_regresion(evaluacion["demanda_mwh"].to_numpy()[valido], prevision[valido]),
                }
            )
    return pd.DataFrame(filas)


def prevision_final(serie: pd.DataFrame, resultado: dict[str, Any], cuantiles: tuple[float, float] = (0.05, 0.95)) -> tuple[pd.DataFrame, Any]:
    """Previsión de los próximos `h` meses de cada comunidad con el modelo elegido, reentrenado con todos los datos.

    El intervalo sale de los cuantiles de los residuos (en log) del modelo elegido en validación.

    Returns:
        (previsión con `codigo_ccaa`, `ccaa`, `mes`, `prevision_mwh`, `inferior_mwh`, `superior_mwh`, `modelo`;
        modelo ajustado, o None si el elegido es un baseline).
    """
    horizonte = resultado["horizonte"]
    elegido = resultado["elegido"]
    tabla = construir_features_demanda(serie, horizonte, meses_futuros=horizonte)
    reales = serie[~serie["imputado"]].groupby("codigo_ccaa")["mes"].max()
    ultimo = serie.groupby("codigo_ccaa")["mes"].max()
    futuro = tabla[tabla["mes"] > tabla["codigo_ccaa"].map(ultimo)].copy()
    columnas = resultado["columnas"]
    ajustado = None
    if elegido["familia"] == "ml":
        modelo = dict(candidatos_ml()[elegido["modelo"]])[elegido["configuracion"]]
        ajustado = _ajustar(modelo, tabla.dropna(subset=["objetivo_log_ratio"]), columnas)
        prevision = _predecir(ajustado, futuro, columnas)
    else:
        prevision = prevision_baseline(elegido["modelo"], futuro, serie, horizonte)
    bajo, alto = np.quantile(resultado["residuos_validacion_log"], cuantiles)
    salida = futuro[["codigo_ccaa", "ccaa", "mes"]].assign(
        prevision_mwh=prevision,
        inferior_mwh=prevision * np.exp(bajo),
        superior_mwh=prevision * np.exp(alto),
        modelo=elegido["modelo"],
        configuracion=elegido["configuracion"],
        ultimo_dato_real=lambda d: d["codigo_ccaa"].map(reales).dt.strftime("%Y-%m"),
        generado_en=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    return salida.reset_index(drop=True), ajustado


def resumen_por_ccaa(serie: pd.DataFrame, prevision: pd.DataFrame) -> pd.DataFrame:
    """Demanda de los últimos 12 meses frente a la prevista para los 12 siguientes, por comunidad (MWh)."""
    filas = []
    for codigo, grupo in serie.sort_values("mes").groupby("codigo_ccaa"):
        ultimos = grupo.tail(12)
        futuro = prevision[prevision["codigo_ccaa"] == codigo]
        if len(ultimos) < 12 or futuro.empty:
            continue
        total_prev = float(futuro["prevision_mwh"].sum())
        total_ult = float(ultimos["demanda_mwh"].sum())
        filas.append(
            {
                "codigo_ccaa": codigo,
                "ccaa": grupo["ccaa"].iloc[0],
                "ultimos_12m_desde": ultimos["mes"].min().strftime("%Y-%m"),
                "ultimos_12m_hasta": ultimos["mes"].max().strftime("%Y-%m"),
                "ultimos_12m_mwh": total_ult,
                "meses_imputados_ultimos_12m": int(ultimos["imputado"].sum()),
                "prevision_12m_mwh": total_prev,
                "prevision_12m_inferior_mwh": float(futuro["inferior_mwh"].sum()),
                "prevision_12m_superior_mwh": float(futuro["superior_mwh"].sum()),
                "variacion_pct": (total_prev / total_ult - 1) * 100,
            }
        )
    return pd.DataFrame(filas)
