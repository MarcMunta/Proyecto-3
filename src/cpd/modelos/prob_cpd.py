"""Probabilidad de que una provincia tenga un centro de datos (`prob_cpd`, clasificación binaria).

Etiqueta: `tiene_cpd` = 1 si la provincia tiene al menos un centro de datos en PeeringDB (14 de 52 provincias).
Features: `cpd.features.provincia.features_estaticas_provincia` (sin `n_ixp` ni `distancia_ixp_km`, por fuga).

Validación: con 52 filas y sin fechas de apertura de los CPD no hay validación temporal posible. Se deja fuera una
comunidad autónoma completa en cada pliegue (LOCO): cada provincia se predice con un modelo que no ha visto ninguna
provincia de su comunidad. La imputación y el escalado se ajustan dentro de cada pliegue, solo con sus datos de
entrenamiento (R-7).

Modelos comparados (mismos pliegues):
- `mayoritaria`: predice siempre la proporción de provincias con CPD (comprueba la paradoja de la exactitud);
- `solo_poblacion`: regresión logística con una sola variable, la población (baseline de sentido común);
- `logistica`: regresión logística con todas las features, con la regularización `C` elegida en una validación
  cruzada interna (anidada) para no elegirla con los mismos datos con que se evalúa;
- `bosque`: random forest poco profundo (recomendación, no viene de clase);
- `logistica_winsor`: la logística con todas las features y **winsorizing** de los percentiles 1 y 99 dentro de cada
  pliegue (técnica de clase I58; añadido el 18/11/2026);
- `poblacion_polinomica`: población y población² (**transformación polinómica**, I59);
- `poblacion_frecuencia_ccaa`: población y **frequency encoding** de la comunidad (I61);
- `poblacion_target_ccaa`: población y **target encoding** de la comunidad (I62), dentro de cada pliegue y con validación
  cruzada interna para no usar la propia etiqueta (añadidos el 18/11/2026).

Interpretación: es una **propensión** ("las provincias con estas características suelen tener CPD"), no la
probabilidad de que se construya uno nuevo. No implica causalidad.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GridSearchCV, GroupKFold, LeaveOneGroupOut, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import PolynomialFeatures, StandardScaler, TargetEncoder

from cpd.features.provincia import FEATURES_PROVINCIA
from cpd.modelos.metricas import matriz_confusion, metricas_clasificacion, umbral_youden

SEMILLA: int = 42
PLIEGUES: int = 5


class Winsorizador(BaseEstimator, TransformerMixin):
    """**Winsorizing** (técnica de clase I58, C4 p.8; añadido el 18/11/2026): recorta cada columna a sus percentiles
    `inferior` y `superior` calculados **solo con los datos de entrenamiento** del pliegue (sin fuga, R-7). Alternativa a
    borrar atípicos: el valor extremo se queda, pero no arrastra el ajuste (p. ej. terremotos por año, asimetría 7,2)."""

    def __init__(self, inferior: float = 0.01, superior: float = 0.99) -> None:
        self.inferior = inferior
        self.superior = superior

    def fit(self, X: Any, y: Any = None) -> Winsorizador:
        datos = np.asarray(X, dtype=float)
        self.limite_inferior_ = np.nanquantile(datos, self.inferior, axis=0)
        self.limite_superior_ = np.nanquantile(datos, self.superior, axis=0)
        return self

    def transform(self, X: Any) -> np.ndarray:
        return np.clip(np.asarray(X, dtype=float), self.limite_inferior_, self.limite_superior_)


def anadir_codificaciones(tabla: pd.DataFrame) -> pd.DataFrame:
    """Columnas de la comunidad autónoma para las técnicas de codificación de clase (añadido el 18/11/2026):

    - `ccaa_codigo`: número de la comunidad (orden alfabético), entrada del **target encoding** (I62), que se calcula
      dentro de cada pliegue;
    - `ccaa_frecuencia`: **frequency encoding** (I61), fracción de provincias que tiene la comunidad. No usa la
      etiqueta, así que se puede calcular con todas las filas sin fuga.
    """
    datos = tabla.copy()
    datos["ccaa_codigo"] = datos["ccaa"].map({c: i for i, c in enumerate(sorted(datos["ccaa"].dropna().unique()))}).astype(float)
    datos["ccaa_frecuencia"] = datos.groupby("ccaa")["ccaa"].transform("size") / len(datos)
    return datos


def modelos_candidatos() -> dict[str, tuple[Any, list[str]]]:
    """Cada modelo con las columnas que usa. Los pipelines imputan (mediana) y escalan dentro del pliegue."""
    logistica = GridSearchCV(
        make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000)),
        param_grid={"logisticregression__C": [0.03, 0.1, 0.3, 1.0, 3.0]},
        scoring=_log_loss_grupo,
        error_score="raise",
        cv=GroupKFold(n_splits=4),
    )
    logistica_winsor = GridSearchCV(
        make_pipeline(SimpleImputer(strategy="median"), Winsorizador(), StandardScaler(), LogisticRegression(max_iter=2000)),
        param_grid={"logisticregression__C": [0.03, 0.1, 0.3, 1.0, 3.0]},
        scoring=_log_loss_grupo,
        error_score="raise",
        cv=GroupKFold(n_splits=4),
    )
    # Target encoding (I62): la propensión media de la comunidad, aprendida SOLO con el entrenamiento del pliegue y con
    # validación cruzada interna (TargetEncoder de scikit-learn), para que una provincia no vea su propia etiqueta.
    poblacion_target = make_pipeline(
        ColumnTransformer(
            [
                ("poblacion", SimpleImputer(strategy="median"), [0]),
                ("ccaa", TargetEncoder(target_type="binary", smooth="auto", cv=StratifiedKFold(n_splits=4, shuffle=True, random_state=SEMILLA)), [1]),
            ]
        ),
        StandardScaler(),
        LogisticRegression(max_iter=2000),
    )
    return {
        "mayoritaria": (DummyClassifier(strategy="prior"), ["log_poblacion"]),
        "logistica_winsor": (logistica_winsor, list(FEATURES_PROVINCIA)),
        "poblacion_polinomica": (
            make_pipeline(SimpleImputer(strategy="median"), PolynomialFeatures(2, include_bias=False), StandardScaler(), LogisticRegression(max_iter=2000)),
            ["log_poblacion"],
        ),
        "poblacion_frecuencia_ccaa": (
            make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000)),
            ["log_poblacion", "ccaa_frecuencia"],
        ),
        "poblacion_target_ccaa": (poblacion_target, ["log_poblacion", "ccaa_codigo"]),
        "solo_poblacion": (
            make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=2000)),
            ["log_poblacion"],
        ),
        "logistica": (logistica, list(FEATURES_PROVINCIA)),
        "bosque": (
            make_pipeline(
                SimpleImputer(strategy="median"),
                RandomForestClassifier(n_estimators=300, max_depth=3, min_samples_leaf=3, random_state=SEMILLA),
            ),
            list(FEATURES_PROVINCIA),
        ),
    }


def _ajustar(modelo: Any, x: np.ndarray, y: np.ndarray, grupos: np.ndarray) -> Any:
    """Ajusta un candidato sin mezclar una comunidad autónoma entre entrenamiento y validación interna."""
    if len(np.unique(y)) == 1:
        return DummyClassifier(strategy="prior").fit(x, y)
    if isinstance(modelo, GridSearchCV):
        n_grupos = len(np.unique(grupos))
        if n_grupos >= 2:
            cv = GroupKFold(n_splits=min(4, n_grupos))
            particiones = [(t, v) for t, v in cv.split(x, y, grupos) if len(np.unique(y[t])) == 2]
            if len(particiones) >= 2:
                return clone(modelo).set_params(cv=particiones).fit(x, y)
        return clone(modelo.estimator).fit(x, y)
    return clone(modelo).fit(x, y)


def ajustar_final(tabla: pd.DataFrame, modelo: Any, columnas: list[str]) -> Any:
    """Entrena el estimador de despliegue con tuning agrupado cuando procede."""
    return _ajustar(modelo, tabla[columnas].to_numpy(dtype=float), tabla["tiene_cpd"].to_numpy(dtype=int),
                    tabla["ccaa"].fillna("sin_ccaa").to_numpy())


def _probabilidad_positiva(modelo: Any, x: np.ndarray) -> np.ndarray:
    """Columna de clase positiva, incluso en un pliegue de entrenamiento con una sola clase."""
    clases = list(modelo.classes_)
    if 1 not in clases:
        return np.zeros(len(x))
    return modelo.predict_proba(x)[:, clases.index(1)]


def _log_loss_grupo(modelo: Any, x: np.ndarray, y: np.ndarray) -> float:
    """Permite evaluar un grupo de validación con una única clase."""
    return -float(log_loss(y, _probabilidad_positiva(modelo, x), labels=[0, 1]))


def _pliegues_geograficos(tabla: pd.DataFrame):
    """Deja una CCAA completa fuera en cada pliegue; no valida una provincia con vecinas del entrenamiento."""
    grupos = tabla["ccaa"].fillna("sin_ccaa").to_numpy()
    if len(np.unique(grupos)) < 2:
        raise ValueError("La validación geográfica de prob_cpd necesita al menos dos CCAA.")
    return LeaveOneGroupOut().split(np.zeros(len(tabla)), tabla["tiene_cpd"].to_numpy(dtype=int), grupos)


def probabilidades_fuera_de_pliegue(tabla: pd.DataFrame, modelo: Any, columnas: list[str]) -> pd.Series:
    """Probabilidad fuera de pliegue por provincia, dejando fuera su CCAA completa.

    Args:
        tabla: salida de `features_estaticas_provincia` (con `tiene_cpd`).
        modelo: estimador de scikit-learn con `predict_proba`.
        columnas: features que usa el modelo.

    Returns:
        Serie indexada por `codigo_provincia` con valores entre 0 y 1.
    """
    x = tabla[columnas].to_numpy(dtype=float)
    y = tabla["tiene_cpd"].to_numpy(dtype=int)
    grupos = tabla["ccaa"].fillna("sin_ccaa").to_numpy()
    probabilidad = np.full(len(tabla), np.nan)
    for entrenar, evaluar in _pliegues_geograficos(tabla):
        ajustado = _ajustar(modelo, x[entrenar], y[entrenar], grupos[entrenar])
        probabilidad[evaluar] = _probabilidad_positiva(ajustado, x[evaluar])
    return pd.Series(probabilidad, index=tabla.index, name="prob_cpd")


def umbrales_fuera_de_pliegue(tabla: pd.DataFrame, modelo: Any, columnas: list[str]) -> pd.Series:
    """Umbral de Youden aplicado a cada CCAA sin usar sus etiquetas.

    Para cada CCAA de evaluación, el umbral se calcula con probabilidades fuera de pliegue de las demás CCAA. Así la
    matriz de confusión no optimiza el corte con las mismas etiquetas que después declara acertar.
    """
    umbrales = np.full(len(tabla), np.nan)
    for entrenar, evaluar in _pliegues_geograficos(tabla):
        internas = tabla.iloc[entrenar]
        if internas["tiene_cpd"].nunique() < 2 or internas["ccaa"].nunique() < 2:
            umbrales[evaluar] = 0.5
        else:
            prob_interna = probabilidades_fuera_de_pliegue(internas, modelo, columnas)
            umbrales[evaluar] = umbral_youden(internas["tiene_cpd"], prob_interna)
    return pd.Series(umbrales, index=tabla.index, name="umbral_cpd")


def sesgos_por_subgrupo(tabla: pd.DataFrame, probabilidad: pd.Series, umbral: float | pd.Series) -> pd.DataFrame:
    """Errores por subgrupo (C3 p.22-24): península frente a islas y Ceuta/Melilla, y tercios de población.

    Returns:
        Una fila por subgrupo con nº de provincias, % real con CPD, probabilidad media, falsos positivos y negativos.
    """
    datos = tabla.assign(prob=probabilidad, pred=(probabilidad >= umbral).astype(int))
    datos["territorio"] = np.where(datos["extrapeninsular"] == 1, "Islas, Ceuta y Melilla", "Península")
    datos["tamano"] = pd.qcut(datos["log_poblacion"], 3, labels=["población baja", "población media", "población alta"])
    filas = []
    for variable in ("territorio", "tamano"):
        for grupo, d in datos.groupby(variable, observed=True):
            filas.append(
                {
                    "variable": variable,
                    "grupo": str(grupo),
                    "provincias": len(d),
                    "con_cpd_pct": d["tiene_cpd"].mean() * 100,
                    "prob_media_pct": d["prob"].mean() * 100,
                    "falsos_positivos": int(((d["pred"] == 1) & (d["tiene_cpd"] == 0)).sum()),
                    "falsos_negativos": int(((d["pred"] == 0) & (d["tiene_cpd"] == 1)).sum()),
                }
            )
    return pd.DataFrame(filas)


def evaluar(tabla: pd.DataFrame) -> dict[str, Any]:
    """Evalúa todos los modelos con los mismos pliegues y elige el de menor log-loss fuera de pliegue.

    Returns:
        `metricas` (una fila por modelo, umbral 0,5), `probabilidades` (DataFrame provincia × modelo), `elegido`,
        `umbral` (Youden del elegido), `metricas_umbral` (elegido con ese umbral), `sesgos`, `coeficientes`
        (logística final, features estandarizadas) y `C` elegido en el ajuste final.
    """
    tabla = anadir_codificaciones(tabla)
    candidatos = modelos_candidatos()
    probabilidades = pd.DataFrame(index=tabla.index)
    filas = []
    for nombre, (modelo, columnas) in candidatos.items():
        prob = probabilidades_fuera_de_pliegue(tabla, modelo, columnas)
        probabilidades[nombre] = prob
        filas.append({"modelo": nombre, **metricas_clasificacion(tabla["tiene_cpd"], prob, umbral=0.5)})
    metricas = pd.DataFrame(filas)
    elegido = str(metricas.set_index("modelo")["log_loss"].idxmin())
    prob_elegido = probabilidades[elegido]
    umbrales = umbrales_fuera_de_pliegue(tabla, candidatos[elegido][0], candidatos[elegido][1])
    pred_umbral = (prob_elegido >= umbrales).astype(int)
    # Para nuevas provincias se conserva un corte único, calculado sin reusar un test temporal inexistente. La matriz
    # de confusión usa en cambio el corte geográficamente externo de cada CCAA.
    umbral = umbral_youden(tabla["tiene_cpd"], prob_elegido)

    # Ajuste final de la logística con todas las provincias, solo para interpretar los coeficientes.
    logistica, columnas = candidatos["logistica"]
    final = ajustar_final(tabla, logistica, columnas)
    regresion = getattr(final, "best_estimator_", final).named_steps["logisticregression"]
    coeficientes = pd.DataFrame({"feature": columnas, "coeficiente_estandarizado": regresion.coef_[0]})
    coeficientes = coeficientes.reindex(coeficientes["coeficiente_estandarizado"].abs().sort_values(ascending=False).index)

    metricas_umbral = metricas_clasificacion(tabla["tiene_cpd"], prob_elegido, umbral=umbral)
    matriz = matriz_confusion(tabla["tiene_cpd"], pred_umbral)
    vp, fp, fn, vn = (matriz[k] for k in ("vp", "fp", "fn", "vn"))
    precision = vp / (vp + fp) if vp + fp else 0.0
    recall = vp / (vp + fn) if vp + fn else 0.0
    metricas_umbral.update(
        {
            "umbral": float(umbrales.mean()),
            "accuracy": (vp + vn) / len(tabla),
            "precision": precision,
            "recall": recall,
            "fpr": fp / (fp + vn) if fp + vn else 0.0,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            **matriz,
        }
    )
    return {
        "metricas": metricas,
        "probabilidades": probabilidades,
        "elegido": elegido,
        "umbral": umbral,
        "metricas_umbral": metricas_umbral,
        "umbrales_fuera_de_pliegue": umbrales,
        "umbral_despliegue": umbral,
        "sesgos": sesgos_por_subgrupo(tabla, prob_elegido, umbrales),
        "coeficientes": coeficientes.reset_index(drop=True),
        "C_final": float(regresion.C),
        "prevalencia": float(tabla["tiene_cpd"].mean()),
    }


def tabla_salida(tabla: pd.DataFrame, resultado: dict[str, Any]) -> pd.DataFrame:
    """Probabilidad final por provincia (la del modelo elegido, fuera de pliegue) para el mapa y el simulador."""
    prob = resultado["probabilidades"][resultado["elegido"]]
    salida = tabla[["provincia", "ccaa", "n_centros_datos", "tiene_cpd"]].copy()
    salida["prob_cpd"] = prob.round(4)
    salida["modelo"] = resultado["elegido"]
    salida["por_encima_del_umbral"] = (prob >= resultado["umbral"]).astype(int)
    return salida.reset_index()
