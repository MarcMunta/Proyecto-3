"""Riesgo sísmico por provincia (P8): probabilidad de al menos un terremoto de magnitud ≥ 3 el año siguiente.

Datos: tabla `sismos` (EMSC, por provincia y año desde 2015). Un año sin fila es un año sin terremotos (dentro del
rango descargado la ausencia de eventos es cero, ver `cpd.fuentes.curado`). El año en curso no se usa (incompleto).

Para cada año objetivo `a` las variables solo usan años anteriores (`< a`):
- `f_ultimo`: hubo algún M ≥ 3 el año anterior (0/1);
- `f_frecuencia`: fracción de años anteriores con algún M ≥ 3;
- `f_actividad`: log(1 + terremotos medios al año, de cualquier magnitud);
- `f_magnitud_max`: magnitud máxima registrada;
- `f_ab_max` y `f_municipios_008`: peligrosidad oficial de la norma NCSE-02 (aceleración máxima de la provincia y
  log(1 + municipios con ab ≥ 0,08 g)); fijas, no cambian con el año.

Candidatos: clase mayoritaria (nunca), persistencia (como el año anterior) y regresión logística con las variables.
Backtesting año a año: cada año se entrena con los anteriores. Validación: años hasta el penúltimo; test: el último
año completo. Se elige con la log-loss de validación (C3: el accuracy solo puede engañar con clases desequilibradas).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cpd.modelos.metricas import metricas_clasificacion

FEATURES: list[str] = ["f_ultimo", "f_frecuencia", "f_actividad", "f_magnitud_max", "f_ab_max", "f_municipios_008"]
ANIOS_MINIMOS: int = 3  # años de historia antes del primer año objetivo


def panel_anual(sismos: pd.DataFrame, provincias: list[str], hoy: dt.date | None = None) -> pd.DataFrame:
    """Provincia × año completo con `n_terremotos`, `n_m3` y `magnitud_max` (0 si no hubo ninguno)."""
    anio_actual = (hoy or dt.date.today()).year
    datos = sismos.assign(codigo_provincia=sismos["codigo_provincia"].astype(str).str.zfill(2))
    anios = range(int(datos["anio"].min()), anio_actual)
    rejilla = pd.MultiIndex.from_product([provincias, anios], names=["codigo_provincia", "anio"]).to_frame(index=False)
    tabla = rejilla.merge(datos, on=["codigo_provincia", "anio"], how="left")
    return pd.DataFrame(
        {
            "codigo_provincia": tabla["codigo_provincia"],
            "anio": tabla["anio"],
            "n_terremotos": tabla["n_terremotos"].fillna(0),
            "n_m3": tabla["n_terremotos_m3_plus"].fillna(0),
            "magnitud_max": tabla["magnitud_max"].fillna(0),
        }
    )


def features(panel: pd.DataFrame, anio: int, peligrosidad: pd.DataFrame | None = None) -> pd.DataFrame:
    """Variables de cada provincia para el año objetivo `anio`, solo con años anteriores, y el objetivo (si existe).

    `peligrosidad`: tabla `peligrosidad_sismica` (NCSE-02); sin ella, las dos variables fijas valen lo mínimo (0,04 g y 0).
    """
    pasado = panel[panel["anio"] < anio]
    por_provincia = pasado.groupby("codigo_provincia")
    tabla = pd.DataFrame(
        {
            "f_ultimo": pasado[pasado["anio"] == anio - 1].set_index("codigo_provincia")["n_m3"].gt(0).astype(float),
            "f_frecuencia": por_provincia["n_m3"].apply(lambda s: float((s > 0).mean())),
            "f_actividad": np.log1p(por_provincia["n_terremotos"].mean()),
            "f_magnitud_max": por_provincia["magnitud_max"].max(),
        }
    ).fillna(0.0)
    norma = peligrosidad.set_index("codigo_provincia") if peligrosidad is not None else pd.DataFrame()
    tabla["f_ab_max"] = norma.get("aceleracion_sismica_max_g", pd.Series(dtype=float)).reindex(tabla.index).fillna(0.04).to_numpy()
    tabla["f_municipios_008"] = np.log1p(norma.get("municipios_ab_008_o_mas", pd.Series(dtype=float)).reindex(tabla.index).fillna(0)).to_numpy()
    objetivo = panel[panel["anio"] == anio].set_index("codigo_provincia")["n_m3"].gt(0).astype(int)
    return tabla.join(objetivo.rename("objetivo"), how="left").assign(anio=anio)


def _prever(nombre: str, entrenamiento: pd.DataFrame, filas: pd.DataFrame) -> np.ndarray:
    """Probabilidad de algún M ≥ 3 en `filas` con el candidato `nombre` entrenado con `entrenamiento`."""
    if nombre == "mayoritaria":
        return np.full(len(filas), float(entrenamiento["objetivo"].mean()))
    if nombre == "persistencia":
        return np.clip(filas["f_ultimo"].to_numpy(dtype=float), 0.02, 0.98)
    modelo = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
    modelo.fit(entrenamiento[FEATURES].to_numpy(dtype=float), entrenamiento["objetivo"].to_numpy(dtype=int))
    return modelo.predict_proba(filas[FEATURES].to_numpy(dtype=float))[:, 1]


CANDIDATOS: tuple[str, ...] = ("mayoritaria", "persistencia", "logistica")


def evaluar(panel: pd.DataFrame, peligrosidad: pd.DataFrame | None = None) -> dict[str, Any]:
    """Backtesting año a año de los candidatos, elección con la validación y probabilidad para el año siguiente.

    Returns:
        `predicciones` (provincia × año × modelo), `metricas` (modelo × partición, umbral 0,5), `elegido`,
        `anios_validacion`, `anio_test` y `prevision` (probabilidad del año siguiente al último completo).
    """
    anios = sorted(panel["anio"].unique())
    objetivo_anios = anios[ANIOS_MINIMOS:]
    test = objetivo_anios[-1]
    filas = []
    for anio in objetivo_anios:
        entrenamiento = pd.concat([features(panel, a, peligrosidad) for a in anios[ANIOS_MINIMOS - 1 : anios.index(anio)] if a >= anios[1]])
        entrenamiento = entrenamiento.dropna(subset=["objetivo"])
        objetivo = features(panel, anio, peligrosidad)
        for nombre in CANDIDATOS:
            filas.append(objetivo.assign(modelo=nombre, prob=_prever(nombre, entrenamiento, objetivo), particion="test" if anio == test else "validacion"))
    pred = pd.concat(filas).reset_index()
    metricas = pd.DataFrame(
        [
            {"modelo": m, "particion": p, **metricas_clasificacion(d["objetivo"], d["prob"], umbral=0.5)}
            for (m, p), d in pred.groupby(["modelo", "particion"])
        ]
    )
    validacion = metricas[metricas["particion"] == "validacion"].set_index("modelo")
    elegido = str(validacion["log_loss"].idxmin())
    entrenamiento = pd.concat([features(panel, a, peligrosidad) for a in anios[1:]]).dropna(subset=["objetivo"])
    siguiente = features(panel, anios[-1] + 1, peligrosidad)
    prevision = siguiente.assign(prob=_prever(elegido, entrenamiento, siguiente))[["anio", "prob", *FEATURES]]
    return {
        "predicciones": pred,
        "metricas": metricas,
        "elegido": elegido,
        "anios_validacion": f"{objetivo_anios[0]}-{objetivo_anios[-2]}",
        "anio_test": int(test),
        "prevision": prevision.reset_index(),
    }
