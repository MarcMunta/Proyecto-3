"""Ejecuta el EDA, entrena y evalúa los modelos y escribe salidas e informes.

Uso (desde la raíz del repositorio):

    .\\.venv\\Scripts\\python.exe -m cpd.modelos            # todo
    .\\.venv\\Scripts\\python.exe -m cpd.modelos --sin-eda  # solo modelos

Salidas:
- `data/curated/modelos/`: previsiones, probabilidades, métricas, atípicos y diccionario de features (fuera de git).
- `models/`: modelos ajustados con joblib (fuera de git).
- `docs/analisis/` y `docs/modelos/`: informes y fichas de modelo; `docs/figuras/`: figuras (en git).
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import functools
import sys
import textwrap
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402

from cpd.config import RUTA_RAIZ  # noqa: E402
from cpd.features.demanda import diccionario_features_demanda, preparar_serie_modelo, serie_demanda_ccaa  # noqa: E402
from cpd.features.provincia import diccionario_features_provincia, features_estaticas_provincia  # noqa: E402
from cpd.modelos import demanda as md  # noqa: E402
from cpd.modelos import eda as meda  # noqa: E402
from cpd.modelos import informe  # noqa: E402
from cpd.modelos import prob_cpd as mp  # noqa: E402
from cpd.features import precio as fprecio  # noqa: E402
from cpd.modelos import precio as mprecio  # noqa: E402
from cpd.modelos.metricas import mape  # noqa: E402

RUTA_PANEL = RUTA_RAIZ / "data" / "curated" / "panel_provincia_mes.parquet"
RUTA_SALIDAS = RUTA_RAIZ / "data" / "curated" / "modelos"
RUTA_MODELOS = RUTA_RAIZ / "models"
RUTA_DOCS = RUTA_RAIZ / "docs"
RUTA_FIG_MODELOS = RUTA_DOCS / "figuras" / "modelos"


def _escribir(texto: str, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    print(f"  · {ruta.relative_to(RUTA_RAIZ).as_posix()}")


def _figura_prevision(predicciones: pd.DataFrame, modelo: str) -> str:
    """Real frente a previsión a 1 mes en test para seis comunidades."""
    datos = predicciones[(predicciones["modelo"] == modelo) & (predicciones["particion"] == "test")]
    principales = datos.groupby("ccaa")["demanda_mwh"].mean().nlargest(6).index
    figura, ejes = plt.subplots(2, 3, figsize=(12, 6), sharex=True)
    for eje, ccaa in zip(ejes.flat, principales):
        d = datos[datos["ccaa"] == ccaa].sort_values("mes")
        eje.plot(d["mes"], d["demanda_mwh"] / 1e3, color="#2c714e", label="real")
        eje.plot(d["mes"], d["prevision_mwh"] / 1e3, color="#e47b2f", ls="--", label="previsión")
        eje.set_title(ccaa, fontsize=9)
        eje.set_ylabel("GWh")
        eje.tick_params(axis="x", labelrotation=45, labelsize=7)
    ejes.flat[0].legend(fontsize=8)
    figura.suptitle(f"Demanda real y prevista a 1 mes en el periodo de test ({informe.NOMBRES_MODELO.get(modelo, modelo)})")
    figura.tight_layout()
    RUTA_FIG_MODELOS.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_FIG_MODELOS / "prevision_demanda_test.png"
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


def _figura_roc(tabla: pd.DataFrame, probabilidades: pd.DataFrame) -> str:
    """Curvas ROC fuera de pliegue de los modelos de `prob_cpd`."""
    figura, eje = plt.subplots(figsize=(5.5, 5))
    for nombre in probabilidades.columns:
        if nombre == "mayoritaria":
            continue
        fpr, tpr, _ = roc_curve(tabla["tiene_cpd"], probabilidades[nombre])
        eje.plot(fpr, tpr, label=informe.NOMBRES_MODELO.get(nombre, nombre))
    eje.plot([0, 1], [0, 1], color="#999999", ls=":", label="azar")
    eje.set_xlabel("Tasa de falsos positivos (FPR)")
    eje.set_ylabel("Tasa de verdaderos positivos (TPR, recall)")
    eje.set_title("Curva ROC fuera de pliegue (52 provincias)")
    eje.legend(fontsize=7)
    RUTA_FIG_MODELOS.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_FIG_MODELOS / "roc_prob_cpd.png"
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


def ejecutar_demanda(panel: pd.DataFrame) -> dict:
    """Evalúa los dos horizontes, hace backtesting y la previsión final a 12 meses."""
    serie = preparar_serie_modelo(serie_demanda_ccaa(panel))
    periodos = md.definir_periodos(serie)
    resultados = {h: md.evaluar_horizonte(serie, h, periodos) for h in md.HORIZONTES}
    for h, r in resultados.items():
        print(f"  h={h:>2}: elegido {r['elegido']['modelo']} ({r['elegido']['configuracion']})")
    ml_12 = {f: resultados[12]["metricas"].query("modelo == @f").iloc[0]["configuracion"] for f in ("ridge", "gradient_boosting")}
    # Cortes anteriores al test (el test se usa una sola vez, en evaluar_horizonte).
    cortes = [periodos.inicio_validacion - pd.DateOffset(months=12 * k) for k in (2, 1)] + [periodos.inicio_validacion]
    bt = md.backtesting(serie, 12, ml_12, cortes)
    prevision, ajustado_12 = md.prevision_final(serie, resultados[12])
    resumen = md.resumen_por_ccaa(serie, prevision)

    # Modelo a 1 mes reentrenado con todo (para guardarlo) y error por comunidad en test.
    r1 = resultados[1]
    e1 = r1["elegido"]
    pred1 = r1["predicciones"][(r1["predicciones"]["modelo"] == e1["modelo"]) & (r1["predicciones"]["particion"] == "test")]
    por_ccaa = pred1.groupby("ccaa").apply(lambda d: mape(d["demanda_mwh"], d["prevision_mwh"]), include_groups=False).sort_values()
    formato = lambda s: ", ".join(f"{c} ({informe._n(v, 1)} %)" for c, v in s.items())  # noqa: E731
    if e1["familia"] == "ml":
        from cpd.features.demanda import construir_features_demanda

        tabla1 = construir_features_demanda(serie, 1).dropna(subset=["objetivo_log_ratio"])
        modelo1 = md._ajustar(dict(md.candidatos_ml()[e1["modelo"]])[e1["configuracion"]], tabla1, r1["columnas"])
        RUTA_MODELOS.mkdir(exist_ok=True)
        joblib.dump({"modelo": modelo1, "columnas": r1["columnas"], "horizonte": 1, "entrenado": dt.date.today().isoformat()}, RUTA_MODELOS / "demanda_ccaa_h1.joblib")
    if ajustado_12 is not None:
        joblib.dump({"modelo": ajustado_12, "columnas": resultados[12]["columnas"], "horizonte": 12}, RUTA_MODELOS / "demanda_ccaa_h12.joblib")

    RUTA_SALIDAS.mkdir(parents=True, exist_ok=True)
    pd.concat([r["metricas"] for r in resultados.values()]).to_csv(RUTA_SALIDAS / "metricas_demanda.csv", index=False)
    pd.concat([r["seleccion"] for r in resultados.values()]).to_csv(RUTA_SALIDAS / "seleccion_demanda.csv", index=False)
    pd.concat([r["predicciones"] for r in resultados.values()]).to_csv(RUTA_SALIDAS / "predicciones_demanda.csv", index=False)
    bt.to_csv(RUTA_SALIDAS / "backtesting_demanda.csv", index=False)
    prevision.to_csv(RUTA_SALIDAS / "prevision_demanda_ccaa.csv", index=False)
    resumen.to_csv(RUTA_SALIDAS / "resumen_demanda_ccaa.csv", index=False)
    serie.to_csv(RUTA_SALIDAS / "serie_demanda_preparada.csv", index=False)
    return {
        "serie": serie,
        "periodos": periodos.como_texto(),
        "resultados": resultados,
        "backtesting": bt,
        "prevision": prevision,
        "resumen": resumen,
        "cuantiles_log": tuple(pd.Series(resultados[12]["residuos_validacion_log"]).quantile([0.05, 0.95])),
        "figura": _figura_prevision(r1["predicciones"], e1["modelo"]),
        "peores_ccaa": formato(por_ccaa.tail(3).iloc[::-1]),
        "mejores_ccaa": formato(por_ccaa.head(3)),
        "semilla": md.SEMILLA,
    }


def ejecutar_prob_cpd(panel: pd.DataFrame) -> tuple[dict, pd.DataFrame, str]:
    """Evalúa los modelos de `prob_cpd` y guarda la probabilidad por provincia."""
    tabla = features_estaticas_provincia(panel)
    resultado = mp.evaluar(tabla)
    print(f"  elegido {resultado['elegido']} · umbral {resultado['umbral']:.2f}")
    salida = mp.tabla_salida(tabla, resultado)
    salida["generado_en"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    RUTA_SALIDAS.mkdir(parents=True, exist_ok=True)
    salida.to_csv(RUTA_SALIDAS / "prob_cpd_provincia.csv", index=False)
    resultado["metricas"].to_csv(RUTA_SALIDAS / "metricas_prob_cpd.csv", index=False)
    resultado["sesgos"].to_csv(RUTA_SALIDAS / "sesgos_prob_cpd.csv", index=False)
    modelo, columnas = mp.modelos_candidatos()[resultado["elegido"]]
    from sklearn.base import clone

    final = clone(modelo).fit(tabla[columnas].to_numpy(dtype=float), tabla["tiene_cpd"].to_numpy(dtype=int))
    RUTA_MODELOS.mkdir(exist_ok=True)
    joblib.dump({"modelo": final, "columnas": columnas, "umbral": resultado["umbral"], "entrenado": dt.date.today().isoformat()}, RUTA_MODELOS / "prob_cpd.joblib")
    resultado["figura_provincias"] = _figura_prob_cpd_provincias(tabla, resultado)
    return resultado, tabla, _figura_roc(tabla, resultado["probabilidades"])


def _figura_prob_cpd_provincias(tabla: pd.DataFrame, resultado: dict) -> str:
    """Matriz de confusión al umbral elegido (izquierda) y probabilidad fuera de pliegue de cada provincia (derecha),
    con el estilo de las figuras de previsiones (`ESTILO_FIGURAS`, definido más abajo)."""
    with plt.rc_context(ESTILO_FIGURAS):
        return _dibujar_prob_cpd_provincias(tabla, resultado)


def _dibujar_prob_cpd_provincias(tabla: pd.DataFrame, resultado: dict) -> str:
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.gridspec import GridSpec

    mu = resultado["metricas_umbral"]
    prob = resultado["probabilidades"][resultado["elegido"]]
    datos = tabla.assign(prob=prob).sort_values("prob")
    figura = plt.figure(figsize=(13, 11))
    rejilla = GridSpec(2, 2, figure=figura, width_ratios=(1, 1.6), height_ratios=(1, 2.2), wspace=0.45)

    # Matriz de confusión: una sola tonalidad (más oscuro = más provincias), cifras en tinta.
    eje = figura.add_subplot(rejilla[0, 0])
    matriz = np.array([[mu["vn"], mu["fp"]], [mu["fn"], mu["vp"]]])
    eje.imshow(matriz, cmap=LinearSegmentedColormap.from_list("azules", ["#e8f1fc", COLOR_REAL]), vmin=0, vmax=matriz.max())
    for (i, j), valor in np.ndenumerate(matriz):
        eje.text(j, i, f"{valor}", ha="center", va="center", fontsize=13, fontweight="bold", color="#ffffff" if valor > matriz.max() * 0.6 else TINTA)
    eje.set_xticks([0, 1], ["previsto: sin CPD", "previsto: con CPD"])
    eje.set_yticks([0, 1], ["real: sin CPD", "real: con CPD"])
    eje.grid(False)
    eje.set_title(f"Matriz de confusión (umbral {resultado['umbral']:.2f})".replace(".", ","))

    # Probabilidad por provincia, ordenada; azul = tiene CPD, gris = no tiene; línea = umbral.
    eje = figura.add_subplot(rejilla[:, 1])
    y = np.arange(len(datos))
    colores = np.where(datos["tiene_cpd"] == 1, COLOR_REAL, COLOR_GRIS)
    eje.barh(y, datos["prob"], 0.72, color=colores, edgecolor=FONDO, lw=0.6)
    eje.axvline(resultado["umbral"], color=TINTA_2, lw=1, ls=(0, (4, 3)))
    # Rótulo abajo, donde las barras son cortas (arriba lo taparía el título).
    eje.annotate(f"umbral {resultado['umbral']:.2f}".replace(".", ","), (resultado["umbral"], 0.03), xycoords=("data", "axes fraction"), xytext=(4, 0), textcoords="offset points", fontsize=7.5, color=TINTA_2)
    eje.set_yticks(y, datos["provincia"], fontsize=6.8)
    eje.set_ylim(-0.7, len(datos) - 0.3)
    eje.set_xlim(0, 1)
    eje.grid(False)
    eje.grid(axis="x")
    eje.set_xlabel("Probabilidad fuera de pliegue")
    eje.set_title(f"prob_cpd por provincia · {informe.NOMBRES_MODELO.get(resultado['elegido'], resultado['elegido'])}")
    eje.legend(handles=[Patch(color=COLOR_REAL, label="tiene CPD"), Patch(color=COLOR_GRIS, label="no tiene")], loc="lower right")

    # Texto con las métricas al umbral, bajo la matriz.
    eje = figura.add_subplot(rejilla[1, 0])
    eje.axis("off")
    lineas = [
        f"Accuracy: {100 * mu['accuracy']:.1f} %",
        f"Precisión: {100 * mu['precision']:.1f} %",
        f"Recall (TPR): {100 * mu['recall']:.1f} %",
        f"FPR: {100 * mu['fpr']:.1f} %",
        f"ROC-AUC: {mu['roc_auc']:.2f}",
        f"Provincias con CPD: {int(tabla['tiene_cpd'].sum())} de {len(tabla)}",
    ]
    eje.text(0, 1, "\n".join(lineas).replace(".", ","), va="top", fontsize=10, color=TINTA_2, linespacing=1.8)
    RUTA_FIG_MODELOS.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_FIG_MODELOS / "prob_cpd_provincias.png"
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


def _figura_precio(mensual: pd.DataFrame, prevision: pd.DataFrame, resumen: dict) -> str:
    """Precio mensual real desde 2019, previsión de los 12 meses siguientes con su intervalo y escenario «último mes»."""
    historia = mensual["precio_eur_mwh"].dropna().loc["2019-01-01":]
    figura, eje = plt.subplots(figsize=(11, 4.4))
    eje.plot(historia.index, historia.values, color="#2c714e", label="precio spot medio real")
    eje.plot(prevision["mes"], prevision["prevision_eur_mwh"], color="#e47b2f", ls="--", label=f"previsión ({informe.NOMBRES_MODELO.get(resumen['modelo'], resumen['modelo'])})")
    eje.fill_between(prevision["mes"], prevision["inferior_eur_mwh"], prevision["superior_eur_mwh"], color="#e47b2f", alpha=0.15, label="intervalo mensual (5-95 %)")
    eje.axhline(resumen["ultimo_mes_eur_mwh"], color="#b8383f", lw=0.9, ls=":", label=f"escenario: se mantiene el último mes ({resumen['ultimo_mes_eur_mwh']:.0f} €/MWh)")
    eje.set_title("Precio de la electricidad (spot, media mensual) y previsión de los próximos 12 meses")
    eje.set_xlabel("Mes")
    eje.set_ylabel("€/MWh")
    eje.legend(fontsize=8)
    RUTA_FIG_MODELOS.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_FIG_MODELOS / "prevision_precio_luz.png"
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


def ejecutar_precio() -> dict:
    """Evalúa los modelos del precio de la luz, hace el backtesting anual y la previsión de los 12 meses siguientes."""
    import json

    from cpd.fuentes.curado import CARPETA_TABLAS

    mensual = fprecio.tabla_mensual(
        fprecio.serie_precio_mensual(pd.read_csv(CARPETA_TABLAS / "precios_diarios.csv")),
        fprecio.serie_reserva_nacional(pd.read_csv(CARPETA_TABLAS / "reservas_ambito_mensual.csv")),
        fprecio.serie_co2(pd.read_csv(CARPETA_TABLAS / "co2.csv")),
    )
    periodos = mprecio.definir_periodos(mensual)
    resultado = mprecio.evaluar(mensual, periodos)
    print(f"  elegido {resultado['elegido']['modelo']} ({resultado['elegido']['configuracion']})")
    configuraciones = {f: resultado["metricas"].query("modelo == @f").iloc[0]["configuracion"] for f in ("ridge", "gradient_boosting")}
    # Backtesting de la media anual: orígenes trimestrales cuyos 12 meses terminan antes de la validación.
    origenes = list(pd.date_range("2020-01-01", periodos.inicio_validacion - pd.DateOffset(months=12), freq="3MS"))
    backtest = mprecio.media_anual_por_origen(mensual, configuraciones, origenes)
    test_anual = mprecio.media_anual_por_origen(mensual, configuraciones, [periodos.inicio_test - pd.DateOffset(months=1)])
    prevision, ajustado = mprecio.prevision_final(mensual, resultado)
    resumen = mprecio.resumen_anual(prevision, backtest, mensual)
    fila_test = resultado["metricas"].query("modelo == @resumen['modelo'] and particion == 'test' and horizonte == 'todos'")
    resumen["mae_test_eur_mwh"] = float(fila_test["mae"].iloc[0])
    resumen["generado_en"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    RUTA_SALIDAS.mkdir(parents=True, exist_ok=True)
    resultado["metricas"].to_csv(RUTA_SALIDAS / "metricas_precio.csv", index=False)
    resultado["seleccion"].to_csv(RUTA_SALIDAS / "seleccion_precio.csv", index=False)
    resultado["predicciones"].to_csv(RUTA_SALIDAS / "predicciones_precio.csv", index=False)
    pd.concat([backtest.assign(tipo="backtesting"), test_anual.assign(tipo="test")]).to_csv(RUTA_SALIDAS / "media_anual_precio.csv", index=False)
    prevision.to_csv(RUTA_SALIDAS / "prevision_precio_luz.csv", index=False)
    (RUTA_SALIDAS / "resumen_precio_luz.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    if ajustado is not None:
        RUTA_MODELOS.mkdir(exist_ok=True)
        joblib.dump({"modelo": ajustado, "columnas": resultado["columnas"], "entrenado": dt.date.today().isoformat()}, RUTA_MODELOS / "precio_luz.joblib")
    return {
        "periodos": periodos.como_texto(),
        "resultado": resultado,
        "backtest": backtest,
        "test_anual": test_anual,
        "prevision": prevision,
        "resumen": resumen,
        "figura": _figura_precio(mensual, prevision, resumen),
        "semilla": mprecio.SEMILLA,
    }


RUTA_FIG_PREVISIONES = RUTA_DOCS / "figuras" / "previsiones"

# Estilo de las figuras de previsiones: un solo eje Y por gráfico (nunca doble eje), rejilla fina, rótulos directos del
# último valor y colores comprobados con un validador de paletas sobre fondo claro (también para daltonismo).
# Real = azul y previsión = naranja en todas las figuras; los modelos que no se eligen, en gris.
COLOR_REAL = "#2a78d6"
COLOR_PREVISTO = "#eb6834"
COLOR_GRIS = "#b9b7b0"
TINTA, TINTA_2, TINTA_3 = "#0b0b0b", "#52514e", "#898781"
FONDO = "#fcfcfb"
ESTILO_FIGURAS = {
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e1e0d9", "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.axisbelow": True,
    "axes.titlesize": 10.5, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlecolor": TINTA, "axes.titlepad": 8,
    "axes.labelcolor": TINTA_2, "axes.labelsize": 9, "xtick.color": "#c3c2b7", "ytick.color": "#c3c2b7",
    "xtick.labelcolor": TINTA_2, "ytick.labelcolor": TINTA_2, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.frameon": False, "legend.fontsize": 8, "legend.labelcolor": TINTA_2, "lines.linewidth": 2, "lines.solid_capstyle": "round",
    "font.size": 9, "text.color": TINTA, "figure.titlesize": 12, "figure.titleweight": "bold",
}


def _con_estilo(funcion):
    """Dibuja las figuras de `funcion` con `ESTILO_FIGURAS` sin tocar el estilo del resto de figuras del proyecto."""

    @functools.wraps(funcion)
    def envuelta(*args, **kwargs):
        with plt.rc_context(ESTILO_FIGURAS):
            return funcion(*args, **kwargs)

    return envuelta


def _punto_final(eje: plt.Axes, x, y: float, texto: str, color: str, arriba: bool = False) -> None:
    """Punto al final de una serie (con anillo del color del fondo) y su valor rotulado a la derecha o encima."""
    eje.plot([x], [y], "o", ms=6.5, color=color, mec=FONDO, mew=1.8, zorder=6)
    desplazamiento, alineacion = ((-4, 9), "right") if arriba else ((8, 0), "left")
    eje.annotate(texto, (x, y), xytext=desplazamiento, textcoords="offset points", ha=alineacion, va="center", fontsize=8.5, fontweight="bold", color=TINTA, zorder=6)


def _rotulos_sin_choque(valores: list[float], hueco: float) -> list[float]:
    """Alturas para rotular varias líneas a la derecha sin que los textos se pisen (separación mínima `hueco`, en unidades del eje)."""
    posiciones = np.asarray(valores, dtype=float).copy()
    anterior = -np.inf
    for k in np.argsort(valores):
        posiciones[k] = max(posiciones[k], anterior + hueco)
        anterior = posiciones[k]
    return posiciones.tolist()


def _leyenda_previsiones(etiqueta_prevision: str) -> list:
    """Leyenda común de los gráficos pequeños: real, previsión e intervalo."""
    return [
        Line2D([], [], color=COLOR_REAL, lw=2, label="real"),
        Line2D([], [], color=COLOR_PREVISTO, lw=2, label=etiqueta_prevision),
        Patch(color=COLOR_PREVISTO, alpha=0.16, lw=0, label="intervalo 10-90 %"),
    ]


def _eje_anios(eje: plt.Axes) -> None:
    eje.xaxis.set_major_locator(mdates.YearLocator())
    eje.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def _guardar_figura(figura: plt.Figure, nombre: str) -> str:
    RUTA_FIG_PREVISIONES.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_FIG_PREVISIONES / nombre
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


@_con_estilo
def _figuras_anual(precio: dict, demanda: dict, mensual: pd.DataFrame, serie: pd.DataFrame) -> dict[str, str]:
    """Gráficos de la previsión a 1 año: precio, demanda por comunidad, errores por horizonte, modelos y backtesting."""
    figuras: dict[str, str] = {}
    nombre = lambda m: informe.NOMBRES_MODELO.get(m, m)  # noqa: E731

    # 1. Precio de la luz (arriba) y precio del gas (abajo): dos gráficos con su propio eje, nunca un doble eje.
    r, f = precio["resultado"], precio["prevision"]
    historia = mensual["precio_eur_mwh"].dropna().loc["2021-01-01":]
    test = r["predicciones"].query("particion == 'test' and modelo == @r['elegido']").sort_values("mes")
    gas = {c: mensual[c].dropna().loc["2021-01-01":] for c in ("gas_spot_eur_mwh", "gas_y1_eur_mwh") if c in mensual and mensual[c].notna().any()}
    if gas:
        figura, (eje, eje_gas) = plt.subplots(2, 1, figsize=(12, 6.8), sharex=True, gridspec_kw={"height_ratios": [3, 1.25], "hspace": 0.3})
    else:
        figura, eje = plt.subplots(figsize=(12, 4.8))
        eje_gas = None
    media_12 = float(historia.iloc[-12:].mean())
    tope = 1.4 * max(float(historia.max()), float(f["prevision"].max()))
    recortado = float(f["superior"].max()) > tope
    nota_banda = f" (recortado: llega a {f['superior'].max():.0f} €/MWh)" if recortado else ""
    eje.fill_between(f["mes"], f["inferior"], f["superior"], color=COLOR_PREVISTO, alpha=0.14, lw=0, label=f"intervalo mensual 10-90 %{nota_banda}")
    eje.axhline(media_12, color=TINTA_3, lw=0.9, ls=(0, (4, 3)), zorder=1, label=f"media de los últimos 12 meses ({media_12:.0f} €/MWh)")
    eje.plot(historia.index, historia.values, color=COLOR_REAL, label="precio real (media mensual)", zorder=4)
    eje.plot(test["mes"], test["prevision"], color=COLOR_PREVISTO, ls=(0, (1, 2)), lw=1.6, label=f"lo que habría previsto hace un año (test, MAE {precio['error_test']:.0f} €/MWh)", zorder=3)
    eje.plot([historia.index[-1], *f["mes"]], [historia.iloc[-1], *f["prevision"]], color=COLOR_PREVISTO, label=f"previsión a 1 año ({nombre(r['elegido'])})", zorder=4)
    _punto_final(eje, historia.index[-1], float(historia.iloc[-1]), f"{historia.iloc[-1]:.0f}", COLOR_REAL, arriba=True)
    _punto_final(eje, f["mes"].iloc[-1], float(f["prevision"].iloc[-1]), f"{f['prevision'].iloc[-1]:.0f}", COLOR_PREVISTO)
    if recortado:
        eje.set_ylim(0, tope)
    else:
        eje.set_ylim(bottom=0)
    eje.set_title("Precio de la luz (spot, media mensual): real, test y previsión a 1 año")
    eje.set_ylabel("Electricidad, €/MWh")
    eje.legend(loc="upper left", ncols=2)
    if eje_gas is not None:
        estilos = {"gas_spot_eur_mwh": ("mercado diario", TINTA_3, "-"), "gas_y1_eur_mwh": ("futuro a 1 año", TINTA_2, (0, (4, 2)))}
        for columna, s in gas.items():
            etiqueta, color, linea = estilos[columna]
            eje_gas.plot(s.index, s.values, color=color, lw=1.4, ls=linea, label=etiqueta)
        eje_gas.set_title("Precio del gas natural en MIBGAS (dato de entrada de los modelos con gas)", fontsize=9.5)
        eje_gas.set_ylabel("Gas, €/MWh")
        eje_gas.set_ylim(bottom=0)
        eje_gas.legend(loc="upper right", ncols=2)
    _eje_anios(eje_gas if eje_gas is not None else eje)
    figuras["precio"] = _guardar_figura(figura, "01_precio_luz_1_anio.png")

    # 2. Demanda: una gráfica por comunidad (últimos 3 años + 12 meses previstos con su intervalo).
    fd_ = demanda["prevision"]
    codigos = sorted(fd_["serie"].unique())
    nombres_ccaa = serie.drop_duplicates("codigo_ccaa").set_index("codigo_ccaa")["ccaa"]
    figura, ejes = plt.subplots(4, 5, figsize=(17, 12))
    for eje, codigo in zip(ejes.flat, codigos):
        s = serie[serie["codigo_ccaa"] == codigo].set_index("mes")["demanda_mwh"].iloc[-36:] / 1e3
        p = fd_[fd_["serie"] == codigo]
        eje.fill_between(p["mes"], p["inferior"] / 1e3, p["superior"] / 1e3, color=COLOR_PREVISTO, alpha=0.16, lw=0)
        eje.plot(s.index, s.values, color=COLOR_REAL, lw=1.4)
        eje.plot([s.index[-1], *p["mes"]], [s.iloc[-1], *(p["prevision"] / 1e3)], color=COLOR_PREVISTO, lw=1.6)
        eje.set_title(nombres_ccaa.get(codigo, codigo), fontsize=9)
        _eje_anios(eje)
        eje.tick_params(labelsize=7)
    for eje in list(ejes.flat)[len(codigos):]:
        eje.axis("off")
    figura.suptitle("Demanda eléctrica por comunidad (GWh al mes): últimos 3 años y previsión a 1 año", x=0.01, ha="left")
    figura.legend(handles=_leyenda_previsiones(f"previsión ({nombre(demanda['resultado']['elegido'])})"), loc="upper right", ncols=3)
    figura.tight_layout(rect=(0, 0, 1, 0.97))
    figuras["demanda"] = _guardar_figura(figura, "02_demanda_ccaa_1_anio.png")

    # Las figuras 3 (error por horizonte) y 4 (comparación de modelos) las dibuja `_figuras_errores` con todas las series.

    # 5. Backtesting del precio: las previsiones a 1 año desde cada origen de validación frente al precio real.
    figuras.update(_figura_backtesting_precio(precio, mensual))
    return figuras


@_con_estilo
def _figuras_errores(paneles: list[tuple[str, dict, str, str]]) -> dict[str, str]:
    """Errores a 1 año de todos los candidatos, un panel por serie: por horizonte (figura 3, validación) y validación
    frente a test (figura 4). El modelo elegido va en naranja (fig. 3) o en negrita (fig. 4); el resto, en gris.

    Args:
        paneles: (nombre de la serie, resultado de `anual.evaluar`, columna de la métrica, etiqueta del eje).
    """
    figuras: dict[str, str] = {}
    nombre = lambda m: informe.NOMBRES_MODELO.get(m, m)  # noqa: E731
    filas = (len(paneles) + 1) // 2

    # 3. Error por horizonte (validación): el modelo elegido en naranja, el resto en gris y rotulados a la derecha.
    figura, ejes = plt.subplots(filas, 2, figsize=(13.5, 4.6 * filas), squeeze=False)
    for eje, (titulo, res, col, etiqueta) in zip(ejes.flat, paneles):
        ph = res["por_horizonte"].query("particion == 'validacion'")
        finales: dict[str, float] = {}
        for modelo, d in ph.groupby("modelo"):
            d = d.sort_values("horizonte_meses")
            elegido = modelo == res["elegido"]
            eje.plot(d["horizonte_meses"], d[col], lw=2.4 if elegido else 1.1, color=COLOR_PREVISTO if elegido else COLOR_GRIS, zorder=4 if elegido else 2)
            finales[str(modelo)] = float(d[col].iloc[-1])
        eje.set_ylim(bottom=0)
        bajo, alto = eje.get_ylim()
        for (modelo, valor), altura in zip(finales.items(), _rotulos_sin_choque(list(finales.values()), (alto - bajo) * 0.05)):
            elegido = modelo == res["elegido"]
            eje.annotate(nombre(modelo) + (" (elegido)" if elegido else ""), (12, valor), xytext=(12.35, altura), textcoords="data", va="center", fontsize=7.5, color=TINTA if elegido else TINTA_2, fontweight="bold" if elegido else "normal", annotation_clip=False, arrowprops={"arrowstyle": "-", "color": COLOR_GRIS, "lw": 0.6, "shrinkA": 0, "shrinkB": 2})
        eje.set_xlim(0.8, 12.2)
        eje.set_xlabel("Meses vista")
        eje.set_ylabel(etiqueta)
        eje.set_xticks(range(1, 13))
        eje.set_title(f"{titulo}: error por horizonte (validación)")
    for eje in list(ejes.flat)[len(paneles):]:
        eje.axis("off")
    figura.tight_layout(w_pad=6, h_pad=2.5)
    figuras["horizonte"] = _guardar_figura(figura, "03_error_por_horizonte.png")

    # 4. Comparación de modelos: validación frente a test (el elegido, en negrita).
    figura, ejes = plt.subplots(filas, 2, figsize=(13, 4.8 * filas), squeeze=False)
    for eje, (titulo, res, col, etiqueta) in zip(ejes.flat, paneles):
        tabla = res["metricas"].pivot(index="modelo", columns="particion", values=col).sort_values("validacion")
        x = np.arange(len(tabla))
        eje.bar(x - 0.2, tabla["validacion"], 0.4, color=COLOR_REAL, edgecolor=FONDO, lw=1, label="validación (24 orígenes)")
        eje.bar(x + 0.2, tabla["test"], 0.4, color=COLOR_PREVISTO, edgecolor=FONDO, lw=1, label="test (1 origen)")
        eje.set_xticks(x, [nombre(m) + (" (elegido)" if m == res["elegido"] else "") for m in tabla.index], rotation=35, ha="right", fontsize=7.5)
        for texto, modelo in zip(eje.get_xticklabels(), tabla.index):
            if modelo == res["elegido"]:
                texto.set_fontweight("bold")
                texto.set_color(TINTA)
        eje.set_ylabel(etiqueta)
        eje.legend(loc="upper left")
        eje.set_title(f"{titulo}: error de cada modelo a 1 año")
    for eje in list(ejes.flat)[len(paneles):]:
        eje.axis("off")
    figura.tight_layout(h_pad=2.5)
    figuras["modelos"] = _guardar_figura(figura, "04_comparacion_modelos.png")
    return figuras


@_con_estilo
def _figura_backtesting_precio(precio: dict, mensual: pd.DataFrame) -> dict[str, str]:
    """Figura 5: cada origen de validación del precio y su previsión a 12 meses frente al precio real."""
    r = precio["resultado"]
    nombre = lambda m: informe.NOMBRES_MODELO.get(m, m)  # noqa: E731
    figura, eje = plt.subplots(figsize=(12, 4.5))
    val = r["predicciones"].query("particion == 'validacion' and modelo == @r['elegido']")
    for _, d in val.groupby("origen"):
        eje.plot(d["mes"], d["prevision"], color=COLOR_PREVISTO, alpha=0.35, lw=1)
    real = mensual["precio_eur_mwh"].dropna().loc[val["mes"].min() - pd.DateOffset(months=12) : val["mes"].max()]
    eje.plot(real.index, real.values, color=COLOR_REAL, lw=2.2, label="precio real", zorder=5)
    eje.plot([], [], color=COLOR_PREVISTO, alpha=0.6, lw=1, label=f"previsiones a 1 año desde cada origen de validación ({nombre(r['elegido'])})")
    eje.set_ylim(bottom=0)
    eje.set_title("Backtesting del precio de la luz: 24 previsiones a 1 año frente a lo que pasó")
    eje.set_ylabel("€/MWh")
    _eje_anios(eje)
    eje.legend(loc="upper left")
    return {"backtesting_precio": _guardar_figura(figura, "05_backtesting_precio.png")}


def ejecutar_anual(panel: pd.DataFrame) -> dict:
    """Previsión a 1 año de la demanda por comunidad y del precio de la luz (`cpd.modelos.anual`)."""
    import json

    from cpd.features.demanda import preparar_serie_modelo, serie_demanda_ccaa
    from cpd.fuentes.curado import CARPETA_TABLAS
    from cpd.modelos import anual

    # Precio (con gas MIBGAS si está descargado).
    gas = None
    if (CARPETA_TABLAS / "gas_diario.csv").exists() and (CARPETA_TABLAS / "gas_futuros.csv").exists():
        gas = fprecio.series_gas(pd.read_csv(CARPETA_TABLAS / "gas_diario.csv"), pd.read_csv(CARPETA_TABLAS / "gas_futuros.csv"))
    mensual = fprecio.tabla_mensual(
        fprecio.serie_precio_mensual(pd.read_csv(CARPETA_TABLAS / "precios_diarios.csv")),
        fprecio.serie_reserva_nacional(pd.read_csv(CARPETA_TABLAS / "reservas_ambito_mensual.csv")),
        fprecio.serie_co2(pd.read_csv(CARPETA_TABLAS / "co2.csv")),
        gas,
    )
    candidatos_p = anual.candidatos_precio(mensual)
    # Precio estructural con los modelos del gas y del tiempo (18/11/2026; ver cpd.modelos.gas_tiempo).
    from cpd.modelos import gas_tiempo

    detalle = None
    if gas is not None and (CARPETA_TABLAS / "generacion_nacional_detalle.csv").exists():
        generacion_ccaa = pd.read_csv(CARPETA_TABLAS / "ccaa_generacion.csv", dtype={"codigo_ccaa": str}, parse_dates=["fecha"])
        ultimo_completo = generacion_ccaa.groupby("codigo_ccaa")["fecha"].max().min()  # todas las comunidades
        detalle = pd.read_csv(CARPETA_TABLAS / "generacion_nacional_detalle.csv", parse_dates=["fecha"])
        detalle = detalle[detalle["fecha"] <= ultimo_completo]
        candidatos_p["estructural_gas_tiempo"] = gas_tiempo.candidato_precio_estructural(gas, detalle, mensual["precio_eur_mwh"].dropna())
    origenes_p = anual.definir_origenes(mensual["precio_eur_mwh"].dropna().index.max())
    res_p = anual.evaluar(candidatos_p, anual.reales_precio(mensual), origenes_p, "mae")
    prev_p = anual.prevision_final(candidatos_p, res_p, {"ES": origenes_p.fin})
    factor_p = anual.intervalo_media_anual(res_p).iloc[0]
    print(f"  precio: {res_p['elegido']} ({', '.join(res_p['miembros'])})")

    # Demanda por comunidad.
    serie = preparar_serie_modelo(serie_demanda_ccaa(panel))
    candidatos_d = anual.candidatos_demanda(serie)
    origenes_d = anual.definir_origenes(serie[~serie["imputado"]].groupby("codigo_ccaa")["mes"].max().min())
    res_d = anual.evaluar(candidatos_d, anual.reales_demanda(serie), origenes_d, "mape_pct")
    prev_d = anual.prevision_final(candidatos_d, res_d, serie.groupby("codigo_ccaa")["mes"].max().to_dict())
    factores_d = anual.intervalo_media_anual(res_d).set_index("serie")
    print(f"  demanda: {res_d['elegido']} ({', '.join(res_d['miembros'])})")

    def error(res: dict, particion: str) -> float:
        m = res["metricas"]
        return float(m[(m["modelo"] == res["elegido"]) & (m["particion"] == particion)][res["metrica"]].iloc[0])

    mes = lambda t: pd.Timestamp(t).strftime("%Y-%m")  # noqa: E731
    historia_p = mensual["precio_eur_mwh"].dropna()
    media_p = float(prev_p["prevision"].mean())
    salida = {
        "generado": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "precio": {
            "modelo": res_p["elegido"], "miembros": res_p["miembros"], "metrica": "mae", "unidad": "€/MWh",
            "error_validacion": error(res_p, "validacion"), "error_test": error(res_p, "test"),
            "historia": [{"mes": mes(i), "valor": round(float(v), 2)} for i, v in historia_p.iloc[-36:].items()],
            "prevision": [{"mes": mes(f.mes), "valor": round(f.prevision, 2), "inferior": round(f.inferior, 2), "superior": round(f.superior, 2)} for f in prev_p.itertuples()],
            "media_prevista": round(media_p, 2),
            "media_inferior": round(media_p * factor_p["factor_inferior"], 2),
            "media_superior": round(media_p * factor_p["factor_superior"], 2),
            "media_12m_actual": round(float(historia_p.iloc[-12:].mean()), 2),
            "ultimo_mes": mes(historia_p.index.max()), "ultimo_mes_valor": round(float(historia_p.iloc[-1]), 2),
            "futuro_gas_anio": round(float(mensual["gas_y1_eur_mwh"].dropna().iloc[-1]), 2) if gas is not None else None,
        },
        "demanda": {
            "modelo": res_d["elegido"], "miembros": res_d["miembros"], "metrica": "mape_pct", "unidad": "MWh",
            "error_validacion": error(res_d, "validacion"), "error_test": error(res_d, "test"),
            "ccaa": {},
        },
    }
    for codigo, grupo in serie.groupby("codigo_ccaa"):
        s = grupo.set_index("mes")["demanda_mwh"].sort_index()
        p = prev_d[prev_d["serie"] == codigo].sort_values("mes")
        total = float(p["prevision"].sum())
        salida["demanda"]["ccaa"][codigo] = {
            "nombre": grupo["ccaa"].iloc[0],
            "historia": [{"mes": mes(i), "valor": round(float(v), 0)} for i, v in s.iloc[-36:].items()],
            "prevision": [{"mes": mes(f.mes), "valor": round(f.prevision, 0), "inferior": round(f.inferior, 0), "superior": round(f.superior, 0)} for f in p.itertuples()],
            "hasta": mes(s.index.max()),
            "ultimos_12m": round(float(s.iloc[-12:].sum()), 0),
            "prevision_12m": round(total, 0),
            "prevision_12m_inferior": round(total * factores_d.loc[codigo, "factor_inferior"], 0),
            "prevision_12m_superior": round(total * factores_d.loc[codigo, "factor_superior"], 0),
        }

    # Reservas de agua por ámbito hidrográfico (1 año).
    reales_r = anual.series_reservas(pd.read_csv(CARPETA_TABLAS / "reservas_ambito_mensual.csv"))
    candidatos_r = anual.candidatos_reservas(reales_r)
    origenes_r = anual.definir_origenes(reales_r.groupby("serie")["mes"].max().min())
    res_r = anual.evaluar(candidatos_r, reales_r, origenes_r, "mae")
    prev_r = anual.prevision_final(candidatos_r, res_r, reales_r.groupby("serie")["mes"].max().to_dict())
    print(f"  reservas: {res_r['elegido']} ({', '.join(res_r['miembros'])})")
    salida["reservas"] = {
        "modelo": res_r["elegido"], "miembros": res_r["miembros"], "metrica": "mae", "unidad": "%",
        "error_validacion": error(res_r, "validacion"), "error_test": error(res_r, "test"), "ambitos": {},
    }
    for ambito, grupo in reales_r.groupby("serie"):
        s = grupo.set_index("mes")["real"].sort_index()
        p = prev_r[prev_r["serie"] == ambito].sort_values("mes")
        salida["reservas"]["ambitos"][ambito] = {
            "historia": [{"mes": mes(i), "valor": round(float(v), 1)} for i, v in s.iloc[-36:].items()],
            "prevision": [{"mes": mes(f.mes), "valor": round(f.prevision, 1), "inferior": round(max(f.inferior, 0), 1), "superior": round(min(f.superior, 100), 1)} for f in p.itertuples()],
        }

    # Temperatura media por provincia (1 año): es la que usa el PUE estimado (simulator.pue_estimado).
    clima = pd.read_csv(CARPETA_TABLAS / "clima_diario.csv", dtype={"codigo_provincia": str})
    reales_t = anual.series_temperatura(clima)
    candidatos_t = anual.candidatos_temperatura(reales_t)
    origenes_t = anual.definir_origenes(reales_t.groupby("serie")["mes"].max().min())
    res_t = anual.evaluar(candidatos_t, reales_t, origenes_t, "mae")
    # Intervalo aditivo (°C): la temperatura no tiene un cero natural, así que un error «relativo» no tiene sentido.
    prev_t = anual.prevision_final(candidatos_t, res_t, reales_t.groupby("serie")["mes"].max().to_dict(), aditivo=True)
    deltas_t = anual.intervalo_media_anual(res_t, aditivo=True).set_index("serie")
    nombres_prov = pd.read_csv(CARPETA_TABLAS / "provincias.csv", dtype={"codigo_provincia": str}).set_index("codigo_provincia")["provincia"]
    print(f"  temperatura: {res_t['elegido']} ({', '.join(res_t['miembros'])})")
    salida["temperatura"] = {
        "modelo": res_t["elegido"], "miembros": res_t["miembros"], "metrica": "mae", "unidad": "°C",
        "error_validacion": error(res_t, "validacion"), "error_test": error(res_t, "test"), "provincias": {},
    }
    for codigo, grupo in reales_t.groupby("serie"):
        s = grupo.set_index("mes")["real"].sort_index()
        p = prev_t[prev_t["serie"] == codigo].sort_values("mes")
        media = float(p["prevision"].mean())
        salida["temperatura"]["provincias"][codigo] = {
            "nombre": str(nombres_prov.get(codigo, codigo)),
            "historia": [{"mes": mes(i), "valor": round(float(v), 1)} for i, v in s.iloc[-36:].items()],
            "prevision": [{"mes": mes(f.mes), "valor": round(f.prevision, 1), "inferior": round(f.inferior, 1), "superior": round(f.superior, 1)} for f in p.itertuples()],
            "hasta": mes(s.index.max()),
            "media_12m_actual": round(float(s.iloc[-12:].mean()), 2),
            "media_prevista": round(media, 2),
            "media_inferior": round(media + float(deltas_t.loc[codigo, "factor_inferior"]), 2),
            "media_superior": round(media + float(deltas_t.loc[codigo, "factor_superior"]), 2),
        }

    # Porcentaje de generación renovable por comunidad (1 año).
    generacion = pd.read_csv(CARPETA_TABLAS / "ccaa_generacion.csv", dtype={"codigo_ccaa": str})
    reales_v = anual.series_renovables(generacion)
    candidatos_v = anual.candidatos_renovables(reales_v)
    # Mejora (18/11/2026): Ridge sobre anomalías con la reserva de los embalses (validación 84,3 % → 84,8 %).
    reserva_nacional = fprecio.serie_reserva_nacional(pd.read_csv(CARPETA_TABLAS / "reservas_ambito_mensual.csv"))
    candidatos_v["ridge_anomalias"] = anual.candidato_ridge_anomalias(reales_v, reserva_nacional)
    origenes_v = anual.definir_origenes(reales_v.groupby("serie")["mes"].max().min())
    res_v = anual.evaluar(candidatos_v, reales_v, origenes_v, "mae")
    prev_v = anual.prevision_final(candidatos_v, res_v, reales_v.groupby("serie")["mes"].max().to_dict(), aditivo=True)
    prev_v[["inferior", "superior"]] = prev_v[["inferior", "superior"]].clip(0, 100)
    deltas_v = anual.intervalo_media_anual(res_v, aditivo=True).set_index("serie")
    nombres_ccaa = (
        pd.read_csv(CARPETA_TABLAS / "provincias.csv", dtype={"codigo_ccaa": str}).drop_duplicates("codigo_ccaa").set_index("codigo_ccaa")["ccaa"]
    )
    acierto_anual_v = anual.acierto_media_anual(res_v)
    print(f"  renovables: {res_v['elegido']} ({', '.join(res_v['miembros'])})")
    salida["renovables"] = {
        "modelo": res_v["elegido"], "miembros": res_v["miembros"], "metrica": "mae", "unidad": "%",
        "error_validacion": error(res_v, "validacion"), "error_test": error(res_v, "test"),
        "acierto_anual_validacion": round(acierto_anual_v["validacion"], 1), "acierto_anual_test": round(acierto_anual_v["test"], 1),
        "ccaa": {},
    }
    for codigo, grupo in reales_v.groupby("serie"):
        s = grupo.set_index("mes")["real"].sort_index()
        p = prev_v[prev_v["serie"] == codigo].sort_values("mes")
        media = float(p["prevision"].mean())
        salida["renovables"]["ccaa"][codigo] = {
            "nombre": str(nombres_ccaa.get(codigo, codigo)),
            "historia": [{"mes": mes(i), "valor": round(float(v), 1)} for i, v in s.iloc[-36:].items()],
            "prevision": [{"mes": mes(f.mes), "valor": round(f.prevision, 1), "inferior": round(f.inferior, 1), "superior": round(f.superior, 1)} for f in p.itertuples()],
            "hasta": mes(s.index.max()),
            "media_12m_actual": round(float(s.iloc[-12:].mean()), 2),
            "media_prevista": round(media, 2),
            "media_inferior": round(min(max(media + float(deltas_v.loc[codigo, "factor_inferior"]), 0), 100), 2),
            "media_superior": round(min(max(media + float(deltas_v.loc[codigo, "factor_superior"]), 0), 100), 2),
        }

    # Generación renovable por comunidad (MWh, 1 año) y cobertura renovable = generación renovable / demanda (%).
    # Más del 100 %: la comunidad genera en renovables más de lo que consume (energía verde de sobra para un CPD).
    reales_g = anual.series_generacion_renovable(generacion)
    candidatos_g = anual.candidatos_renovables(reales_g, maximo=np.inf, con_log=True)
    # Mejora (18/11/2026): cada tecnología por separado (solar, eólica, hidráulica…) y sumadas (85,6 % en validación).
    if (CARPETA_TABLAS / "ccaa_generacion_tecnologia.csv").exists():
        tecnologias = pd.read_csv(CARPETA_TABLAS / "ccaa_generacion_tecnologia.csv", dtype={"codigo_ccaa": str})
        candidatos_g["suma_tecnologias"] = anual.candidato_suma_tecnologias(tecnologias, "mwh")
        # Hidráulica prevista desde los embalses (18/11/2026): 85,6 % → 86,2 % en validación.
        candidatos_g["tecnologias_hidro_embalses"] = anual.candidato_tecnologias_hidro_embalses(tecnologias, reserva_nacional)
    origenes_g = anual.definir_origenes(reales_g.groupby("serie")["mes"].max().min())
    res_g = anual.evaluar(candidatos_g, reales_g, origenes_g, "mae")
    prev_g = anual.prevision_final(candidatos_g, res_g, reales_g.groupby("serie")["mes"].max().to_dict())
    acierto_anual_g = anual.acierto_media_anual(res_g)
    print(f"  generación renovable: {res_g['elegido']} ({', '.join(res_g['miembros'])})")
    salida["cobertura_renovable"] = {
        "modelo": res_g["elegido"], "miembros": res_g["miembros"], "metrica": "mae", "unidad": "MWh",
        "error_validacion": error(res_g, "validacion"), "error_test": error(res_g, "test"),
        "acierto_anual_validacion": round(acierto_anual_g["validacion"], 1), "acierto_anual_test": round(acierto_anual_g["test"], 1),
        "ccaa": {},
    }
    renovable_real = generacion.assign(mes=pd.to_datetime(generacion["fecha"]).dt.to_period("M").dt.to_timestamp())
    for codigo, d in salida["demanda"]["ccaa"].items():
        historia = renovable_real[(renovable_real["codigo_ccaa"] == codigo) & (renovable_real["mes"] <= reales_v["mes"].max())]
        renovable_12m = float(historia.sort_values("mes")["generacion_renovable_mwh"].iloc[-12:].sum()) if len(historia) >= 12 else None
        prevista = prev_g.loc[prev_g["serie"] == codigo, "prevision"]
        # Sin serie (Ceuta, siempre 0 MWh renovables): la previsión es 0, no un dato ausente.
        renovable_prevista = float(prevista.sum()) if len(prevista) else (0.0 if renovable_12m == 0 else None)
        cobertura = lambda r, dem: round(100 * r / dem, 1) if r is not None and dem else None  # noqa: E731
        salida["cobertura_renovable"]["ccaa"][codigo] = {
            "nombre": d["nombre"],
            "renovable_12m_mwh": None if renovable_12m is None else round(renovable_12m, 0),
            "renovable_prevista_mwh": None if renovable_prevista is None else round(renovable_prevista, 0),
            "demanda_12m_mwh": d["ultimos_12m"], "demanda_prevista_mwh": d["prevision_12m"],
            "cobertura_actual_pct": cobertura(renovable_12m, d["ultimos_12m"]),
            "cobertura_prevista_pct": cobertura(renovable_prevista, d["prevision_12m"]),
        }

    # Gas y tiempo (entradas del precio de la luz, inestables): backtesting a 1 año y previsión de los 12 meses.
    gas_tiempo_res = None
    if detalle is not None:
        gas_tiempo_res = gas_tiempo.evaluar_todo(gas, detalle, reserva_nacional)
        diagnostico = gas_tiempo.diagnostico_precio(gas, detalle, mensual["precio_eur_mwh"].dropna(), "2022-12", str(origenes_p.validacion[-1] + pd.DateOffset(months=12))[:7])
        salida["gas_tiempo"] = {"diagnostico_precio_con_reales": round(diagnostico, 1), "modelos": {}}
        series_gt = {"gas": (gas_tiempo_res["gas"], gas_tiempo.reales_gas(gas), gas_tiempo.candidatos_gas(gas))}
        for tec in gas_tiempo.TECNOLOGIAS_TIEMPO:
            reales_tec = gas_tiempo.reales_tecnologia(detalle, tec)
            series_gt[tec] = (gas_tiempo_res["tiempo"][tec], reales_tec, gas_tiempo.candidatos_tecnologia(reales_tec, reserva_nacional))
        gas_tiempo_res["previsiones"], gas_tiempo_res["reales"] = {}, {}
        for nombre, (res_x, reales_x, cand_x) in series_gt.items():
            prev_x = anual.prevision_final(cand_x, res_x, {reales_x["serie"].iloc[0]: reales_x["mes"].max()})
            gas_tiempo_res["previsiones"][nombre], gas_tiempo_res["reales"][nombre] = prev_x, reales_x
            m_x = res_x["metricas"].query("modelo == @res_x['elegido']").set_index("particion")["acierto_pct"]
            salida["gas_tiempo"]["modelos"][nombre] = {
                "modelo": res_x["elegido"], "miembros": res_x["miembros"],
                "acierto_validacion": round(float(m_x["validacion"]), 1), "acierto_test": round(float(m_x["test"]), 1),
            }
            res_x["metricas"].to_csv(RUTA_SALIDAS / f"anual_metricas_{nombre}.csv", index=False)
            prev_x.to_csv(RUTA_SALIDAS / f"anual_prevision_{nombre}.csv", index=False)
        print(f"  gas y tiempo: diagnóstico del precio con los reales {diagnostico:.1f} %; " + ", ".join(f"{k} {v['acierto_validacion']} %" for k, v in salida["gas_tiempo"]["modelos"].items()))

    # Operación del CPD de referencia a 1 año (objetivo A3): temperatura → PUE → consumo; % renovable → emisiones.
    from cpd import simulator as simulador
    from cpd.config import cargar_settings
    from cpd.fuentes.embalses import AMBITO_POR_PROVINCIA
    from cpd.modelos import operacion

    ajustes = cargar_settings()
    validos = {f.name for f in dataclasses.fields(simulador.CPDParams)}
    params = simulador.CPDParams(**{k: v for k, v in ajustes.get("cpd_por_defecto", {}).items() if k in validos})
    factor_emision = float(ajustes["precios"]["factor_emision_t_mwh"])
    ccaa_de = pd.read_csv(CARPETA_TABLAS / "provincias.csv", dtype={"codigo_provincia": str, "codigo_ccaa": str}).set_index("codigo_provincia")["codigo_ccaa"].to_dict()
    bt_op = operacion.backtesting(res_t, res_v, ccaa_de, params, factor_emision)
    tabla_op = operacion.prevision(salida["temperatura"]["provincias"], salida["renovables"]["ccaa"], ccaa_de, params, factor_emision)
    print(f"  operación del CPD: consumo {bt_op['acierto_consumo']:.1f} %, emisiones {bt_op['acierto_emisiones']:.1f} % ({bt_op['origenes']} orígenes comunes)")
    salida["operacion"] = {
        "cpd": {"potencia_ti_mw": params.potencia_ti_mw, "factor_carga": params.factor_carga, "tipo_refrigeracion": params.tipo_refrigeracion},
        "factor_emision_t_mwh": factor_emision,
        "acierto_consumo": round(bt_op["acierto_consumo"], 1), "acierto_emisiones": round(bt_op["acierto_emisiones"], 1),
        "origenes": bt_op["origenes"], "provincias": {},
    }
    for f in tabla_op.itertuples():
        ambito = AMBITO_POR_PROVINCIA.get(f.codigo_provincia)
        p_res = prev_r[prev_r["serie"] == ambito].sort_values("prevision") if ambito else prev_r.iloc[0:0]
        salida["operacion"]["provincias"][f.codigo_provincia] = {
            "pue_actual": round(f.pue_actual, 3), "pue_previsto": round(f.pue_previsto, 3),
            "consumo_actual_mwh": round(f.consumo_mwh_actual, 0), "consumo_previsto_mwh": round(f.consumo_mwh_previsto, 0),
            "emisiones_actual_t": round(f.emisiones_t_actual, 0), "emisiones_previsto_t": round(f.emisiones_t_previsto, 0),
            "agua_m3": round(f.agua_m3_previsto, 0),
            "reserva_minima_prevista_pct": round(float(p_res["prevision"].iloc[0]), 1) if len(p_res) else None,
            "mes_reserva_minima": mes(p_res["mes"].iloc[0]) if len(p_res) else None,
        }
    bt_op["detalle"].to_csv(RUTA_SALIDAS / "operacion_backtesting.csv", index=False)
    tabla_op.to_csv(RUTA_SALIDAS / "operacion_cpd_provincia.csv", index=False)

    # Impacto previsto del CPD sobre los recursos locales (P2): electricidad, red y agua de su comunidad.
    from cpd.modelos import impacto_local

    pob = pd.read_csv(CARPETA_TABLAS / "poblacion.csv", dtype={"codigo_provincia": str})
    pob = pob[pob["anio"] == pob["anio"].max()].assign(ccaa=lambda d: d["codigo_provincia"].map(ccaa_de)).groupby("ccaa")["poblacion"].sum()
    pob.loc[impacto_local.CODIGO_CEUTA_MELILLA] = pob.get("18", 0.0) + pob.get("19", 0.0)
    tabla_imp = impacto_local.impacto_provincias(
        salida["operacion"]["provincias"], salida["demanda"]["ccaa"],
        pd.read_csv(CARPETA_TABLAS / "capacidad_ccaa.csv", dtype={"codigo_ccaa": str}),
        pd.read_csv(CARPETA_TABLAS / "agua_ccaa.csv", dtype={"codigo_ccaa": str}), pob, ccaa_de, params,
    )
    val_imp = impacto_local.validar_impacto_electrico(res_t, res_d, ccaa_de, params, "validacion")
    test_imp = impacto_local.validar_impacto_electrico(res_t, res_d, ccaa_de, params, "test")
    print(f"  impacto local (P2): acierto del % eléctrico {val_imp['acierto']:.1f} % validación ({val_imp['origenes']} orígenes)"
          + (f", {test_imp['acierto']:.1f} % test" if test_imp["acierto"] is not None else ", sin test común"))
    salida["impacto_local"] = {
        "acierto_validacion": round(val_imp["acierto"], 1), "acierto_test": round(test_imp["acierto"], 1) if test_imp["acierto"] is not None else None,
        "origenes": val_imp["origenes"], "anio_agua": int(tabla_imp["anio_agua"].max()),
        "provincias": {
            f.codigo_provincia: {
                "pct_demanda_ccaa": round(f.pct_demanda_ccaa, 2), "habitantes_eq_electricidad": round(f.habitantes_eq_electricidad, -2),
                "potencia_pico_mw": round(f.potencia_pico_mw, 1),
                "pct_capacidad_disponible": None if pd.isna(f.pct_capacidad_disponible) else round(f.pct_capacidad_disponible, 0),
                "sin_capacidad_libre": bool(f.sin_capacidad_libre),
                "capacidad_disponible_mw": None if pd.isna(f.capacidad_disponible_mw) else round(f.capacidad_disponible_mw, 0),
                "pct_agua_ccaa": round(f.pct_agua_ccaa, 3), "habitantes_eq_agua": round(f.habitantes_eq_agua, -1),
            }
            for f in tabla_imp.itertuples()
        },
    }
    tabla_imp.to_csv(RUTA_SALIDAS / "impacto_local_provincia.csv", index=False)

    # Control de acierto de los modelos de la previsión a 1 año (100 − WAPE, ver cpd.modelos.metricas).
    for clave, res in (("precio", res_p), ("demanda", res_d), ("reservas", res_r), ("temperatura", res_t), ("renovables", res_v), ("cobertura_renovable", res_g)):
        m = res["metricas"].query("modelo == @res['elegido']").set_index("particion")
        salida[clave]["acierto_validacion"] = round(float(m.loc["validacion", "acierto_pct"]), 1)
        salida[clave]["acierto_test"] = round(float(m.loc["test", "acierto_pct"]), 1)

    RUTA_SALIDAS.mkdir(parents=True, exist_ok=True)
    (RUTA_SALIDAS / "previsiones_1_anio.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    for nombre_res, res in (
        ("precio", res_p), ("demanda", res_d), ("reservas", res_r), ("temperatura", res_t), ("renovables", res_v), ("generacion_renovable", res_g),
    ):
        res["metricas"].to_csv(RUTA_SALIDAS / f"anual_metricas_{nombre_res}.csv", index=False)
        res["por_horizonte"].to_csv(RUTA_SALIDAS / f"anual_por_horizonte_{nombre_res}.csv", index=False)
    prev_v.to_csv(RUTA_SALIDAS / "anual_prevision_renovables.csv", index=False)
    prev_g.to_csv(RUTA_SALIDAS / "anual_prevision_generacion_renovable.csv", index=False)
    pd.DataFrame.from_dict(salida["cobertura_renovable"]["ccaa"], orient="index").rename_axis("codigo_ccaa").to_csv(RUTA_SALIDAS / "cobertura_renovable_ccaa.csv")
    prev_p.to_csv(RUTA_SALIDAS / "anual_prevision_precio.csv", index=False)
    prev_d.to_csv(RUTA_SALIDAS / "anual_prevision_demanda.csv", index=False)
    prev_r.to_csv(RUTA_SALIDAS / "anual_prevision_reservas.csv", index=False)
    prev_t.to_csv(RUTA_SALIDAS / "anual_prevision_temperatura.csv", index=False)

    precio = {"resultado": res_p, "prevision": prev_p, "error_test": error(res_p, "test"), "resumen": salida["precio"]}
    demanda = {"resultado": res_d, "prevision": prev_d, "resumen": salida["demanda"]}
    reservas = {"resultado": res_r, "prevision": prev_r, "reales": reales_r, "resumen": salida["reservas"]}
    temperatura = {"resultado": res_t, "prevision": prev_t, "reales": reales_t, "resumen": salida["temperatura"]}
    renovables = {"resultado": res_v, "prevision": prev_v, "reales": reales_v, "resumen": salida["renovables"]}
    cobertura = {"resultado": res_g, "prevision": prev_g, "resumen": salida["cobertura_renovable"]}
    operacion_res = {"backtesting": bt_op, "tabla": tabla_op, "resumen": salida["operacion"], "nombres": salida["temperatura"]["provincias"]}
    nombres_ccaa = pd.read_csv(CARPETA_TABLAS / "provincias.csv", dtype={"codigo_ccaa": str}).drop_duplicates("codigo_ccaa").set_index("codigo_ccaa")["ccaa"].to_dict()
    impacto_res = {"tabla": tabla_imp, "resumen": salida["impacto_local"], "validacion": val_imp, "test": test_imp, "nombres_ccaa": nombres_ccaa, "nombres": salida["temperatura"]["provincias"]}
    gas_tiempo_res = None if gas_tiempo_res is None else {**gas_tiempo_res, "resumen": salida.get("gas_tiempo")}
    figuras = _figuras_anual(precio, demanda, mensual, serie)
    figuras.update(_figuras_reservas(reservas))
    figuras.update(_figuras_temperatura(temperatura))
    figuras.update(_figuras_renovables(renovables))
    figuras.update(_figura_cobertura(cobertura))
    figuras.update(_figura_operacion(operacion_res))
    figuras["impacto"] = _figura_impacto(impacto_res)
    if gas_tiempo_res is not None:
        figuras.update(_figura_gas_tiempo(gas_tiempo_res))
    # MAE de la generación renovable en GWh para que el eje sea legible.
    en_gwh = {k: (v.assign(mae=v["mae"] / 1e3) if k in ("metricas", "por_horizonte") else v) for k, v in res_g.items()}
    figuras.update(
        _figuras_errores(
            [
                ("Demanda por comunidad", res_d, "mape_pct", "MAPE (%)"),
                ("Precio de la luz", res_p, "mae", "MAE (€/MWh)"),
                ("Reservas de agua por ámbito", res_r, "mae", "MAE (puntos de reserva, %)"),
                ("Temperatura por provincia", res_t, "mae", "MAE (°C)"),
                ("Renovables por comunidad", res_v, "mae", "MAE (puntos de % renovable)"),
                ("Generación renovable por comunidad", en_gwh, "mae", "MAE (GWh al mes)"),
            ]
        )
    )
    return {
        "precio": precio, "demanda": demanda, "reservas": reservas, "temperatura": temperatura, "renovables": renovables,
        "cobertura": cobertura, "operacion": operacion_res, "impacto": impacto_res, "gas_tiempo": gas_tiempo_res, "figuras": figuras, "json": salida,
    }


@_con_estilo
def _figura_impacto(impacto_res: dict) -> str:
    """Figura 17: impacto previsto del CPD de referencia por comunidad (media de sus provincias): % de la demanda
    eléctrica, % de la capacidad de acceso libre de la red y % del agua distribuida."""
    tabla = impacto_res["tabla"].copy()
    por_ccaa = tabla.groupby("codigo_ccaa").agg(
        demanda=("pct_demanda_ccaa", "mean"), red=("pct_capacidad_disponible", "mean"), agua=("pct_agua_ccaa", "mean"),
        sin_red=("sin_capacidad_libre", "any"), disponible=("capacidad_disponible_mw", "first"),
    )
    por_ccaa["nombre"] = por_ccaa.index.map(lambda c: impacto_res["nombres_ccaa"].get(c, c))
    por_ccaa = por_ccaa.sort_values("demanda")
    y = np.arange(len(por_ccaa))
    coma = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")  # noqa: E731
    figura, ejes = plt.subplots(1, 3, figsize=(16, 0.42 * len(por_ccaa) + 2.4), sharey=True)
    paneles = (
        ("demanda", "(a) % de la demanda eléctrica prevista de su comunidad", 20, 1),
        ("red", "(b) % de la capacidad de acceso libre de la red (REE)", 100, 0),
        ("agua", "(c) % del agua distribuida en su comunidad (INE)", 2, 2),
    )
    for eje, (col, titulo, tope, dec) in zip(ejes, paneles):
        valores = por_ccaa[col]
        eje.barh(y, valores.clip(upper=tope).fillna(0), 0.62, color=COLOR_PREVISTO, edgecolor=FONDO, lw=1)
        for yi, (v, sin_red, disp) in enumerate(zip(valores, por_ccaa["sin_red"], por_ccaa["disponible"])):
            if col == "red" and sin_red:
                texto = "0 MW libres: no cabe"
            elif col == "red" and pd.isna(disp):
                texto = "sin dato"
            elif pd.isna(v):
                texto = "sin dato"
            else:
                texto = coma(v, dec) + " %" + (" ▸" if v > tope else "")
            eje.annotate(texto, (min(v, tope) if pd.notna(v) else 0, yi), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=TINTA_2)
        eje.set_xlim(0, tope * 1.32)
        eje.xaxis.set_major_formatter(lambda x, _: f"{x:g}".replace(".", ","))
        eje.set_title(titulo, fontsize=9.5, loc="left")
        eje.grid(False)
        eje.grid(axis="x")
    ejes[0].set_yticks(y, por_ccaa["nombre"], fontsize=8.5)
    ejes[0].annotate("▸ se sale de la escala", (0, -0.06), xycoords="axes fraction", fontsize=7.5, color=TINTA_3)
    cpd = impacto_res["resumen"]
    figura.suptitle(
        f"Impacto previsto del CPD de referencia sobre los recursos de su comunidad (próximos 12 meses; agua: INE {cpd['anio_agua']})",
        x=0.01, ha="left",
    )
    figura.tight_layout(rect=(0, 0, 1, 0.95))
    return _guardar_figura(figura, "17_impacto_local.png")


@_con_estilo
def _figuras_reservas(reservas: dict) -> dict[str, str]:
    """Reserva de cada ámbito: últimos 3 años y previsión a 1 año con su intervalo."""
    reales, prev = reservas["reales"], reservas["prevision"]
    ambitos = sorted(prev["serie"].unique())
    figura, ejes = plt.subplots(4, 4, figsize=(16, 12), sharey=True)
    for eje, ambito in zip(ejes.flat, ambitos):
        s = reales[reales["serie"] == ambito].set_index("mes")["real"].iloc[-36:]
        p = prev[prev["serie"] == ambito]
        eje.fill_between(p["mes"], p["inferior"].clip(0, 100), p["superior"].clip(0, 100), color=COLOR_PREVISTO, alpha=0.16, lw=0)
        eje.plot(s.index, s.values, color=COLOR_REAL, lw=1.4)
        eje.plot([s.index[-1], *p["mes"]], [s.iloc[-1], *p["prevision"]], color=COLOR_PREVISTO, lw=1.6)
        eje.set_title(ambito, fontsize=9)
        eje.set_ylim(0, 100)
        _eje_anios(eje)
        eje.tick_params(labelsize=7)
    for eje in list(ejes.flat)[len(ambitos):]:
        eje.axis("off")
    elegido = informe.NOMBRES_MODELO.get(reservas["resultado"]["elegido"], reservas["resultado"]["elegido"])
    figura.suptitle("Reserva de los embalses por ámbito (% de la capacidad): últimos 3 años y previsión a 1 año", x=0.01, ha="left")
    figura.legend(handles=_leyenda_previsiones(f"previsión ({elegido})"), loc="upper right", ncols=3)
    figura.tight_layout(rect=(0, 0, 1, 0.97))
    return {"reservas": _guardar_figura(figura, "06_reservas_ambitos_1_anio.png")}


@_con_estilo
def _figuras_temperatura(temperatura: dict) -> dict[str, str]:
    """Temperatura por provincia: media de los próximos 12 meses frente a la del último año (figura 9, las 52) y serie
    mensual de las 4 provincias más frías y las 4 más cálidas según la previsión (figura 10)."""
    resumen = temperatura["resumen"]
    provincias = pd.DataFrame.from_dict(resumen["provincias"], orient="index").sort_values("media_prevista")
    elegido = informe.NOMBRES_MODELO.get(resumen["modelo"], resumen["modelo"])
    figuras: dict[str, str] = {}

    # 9. Las 52 provincias: punto azul = último año real, punto naranja = previsión, línea = intervalo 10-90 %.
    figura, eje = plt.subplots(figsize=(8.5, 11.5))
    y = np.arange(len(provincias))
    eje.hlines(y, provincias["media_inferior"], provincias["media_superior"], color=COLOR_PREVISTO, alpha=0.35, lw=3.2, label="intervalo 10-90 % de la previsión")
    eje.plot(provincias["media_12m_actual"], y, "o", ms=5, color=COLOR_REAL, mec=FONDO, mew=1.2, label="últimos 12 meses (real)", zorder=4)
    eje.plot(provincias["media_prevista"], y, "o", ms=5.5, color=COLOR_PREVISTO, mec=FONDO, mew=1.2, label=f"próximos 12 meses ({elegido})", zorder=5)
    eje.set_yticks(y, provincias["nombre"], fontsize=7.2)
    eje.set_ylim(-0.8, len(provincias) - 0.2)
    eje.grid(False)
    eje.grid(axis="x")
    eje.set_xlabel("Temperatura media anual (°C)")
    eje.set_title("Temperatura media por provincia: último año y previsión de los próximos 12 meses", pad=28)
    eje.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncols=3, fontsize=7.5)
    figuras["temperatura"] = _guardar_figura(figura, "09_temperatura_provincias_1_anio.png")

    # 10. Serie mensual de las 4 más frías y las 4 más cálidas (criterio: media prevista).
    reales, prev = temperatura["reales"], temperatura["prevision"]
    elegidas = [*provincias.index[:4], *provincias.index[-4:]]
    figura, ejes = plt.subplots(2, 4, figsize=(16, 6.4), sharey=True)
    for eje, codigo in zip(ejes.flat, elegidas):
        s = reales[reales["serie"] == codigo].set_index("mes")["real"].iloc[-36:]
        p = prev[prev["serie"] == codigo]
        eje.fill_between(p["mes"], p["inferior"], p["superior"], color=COLOR_PREVISTO, alpha=0.16, lw=0)
        eje.plot(s.index, s.values, color=COLOR_REAL, lw=1.4)
        eje.plot([s.index[-1], *p["mes"]], [s.iloc[-1], *p["prevision"]], color=COLOR_PREVISTO, lw=1.6)
        eje.set_title(f"{provincias.loc[codigo, 'nombre']} · {provincias.loc[codigo, 'media_prevista']:.1f} °C".replace(".", ","), fontsize=9)
        _eje_anios(eje)
        eje.tick_params(labelsize=7)
    ejes[0, 0].set_ylabel("°C (media del mes)")
    ejes[1, 0].set_ylabel("°C (media del mes)")
    figura.suptitle("Temperatura media mensual: las 4 provincias más frías (arriba) y las 4 más cálidas (abajo) según la previsión", x=0.01, ha="left")
    figura.legend(handles=_leyenda_previsiones(f"previsión ({elegido})"), loc="upper right", ncols=3)
    figura.tight_layout(rect=(0, 0, 1, 0.95))
    figuras["temperatura_mensual"] = _guardar_figura(figura, "10_temperatura_mensual.png")
    return figuras


@_con_estilo
def _figura_operacion(operacion_res: dict) -> dict[str, str]:
    """Figura 14: emisiones del CPD de referencia por provincia, último año y próximos 12 meses (t CO2/año)."""
    tabla = operacion_res["tabla"].copy()
    tabla["nombre"] = tabla["codigo_provincia"].map(lambda c: operacion_res["nombres"].get(c, {}).get("nombre", c))
    tabla = tabla.sort_values("emisiones_t_previsto")
    figura, eje = plt.subplots(figsize=(9, 11.5))
    y = np.arange(len(tabla))
    eje.hlines(y, 0, tabla["emisiones_t_previsto"] / 1e3, color=COLOR_PREVISTO, alpha=0.35, lw=3)
    eje.plot(tabla["emisiones_t_actual"] / 1e3, y, "o", ms=5, color=COLOR_REAL, mec=FONDO, mew=1.2, label="último año (real)", zorder=4)
    eje.plot(tabla["emisiones_t_previsto"] / 1e3, y, "o", ms=5.5, color=COLOR_PREVISTO, mec=FONDO, mew=1.2, label="próximos 12 meses (previsto)", zorder=5)
    eje.set_yticks(y, tabla["nombre"], fontsize=7.2)
    eje.set_ylim(-0.8, len(tabla) - 0.2)
    eje.set_xlim(left=0)
    eje.grid(False)
    eje.grid(axis="x")
    cpd = operacion_res["resumen"]["cpd"]
    eje.set_xlabel(f"Miles de t CO2 al año (CPD de {cpd['potencia_ti_mw']:.0f} MW de TI con el mix de generación de su comunidad)")
    eje.set_title("Emisiones del CPD de referencia por provincia: último año y previsión", pad=28)
    eje.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncols=2, fontsize=7.5)
    return {"operacion": _guardar_figura(figura, "14_operacion_cpd_emisiones.png")}


@_con_estilo
def _figura_gas_tiempo(gas_tiempo_res: dict) -> dict[str, str]:
    """Figura 15: gas y tiempo (eólica, solar e hidráulica de España), últimos 3 años y previsión a 1 año, con su
    acierto. Son entradas del precio de la luz y son inestables."""
    titulos = {
        "gas": ("Gas natural MIBGAS (€/MWh)", 1.0), "eolica": ("Eólica de España (TWh al mes)", 1e6),
        "solar": ("Solar de España (TWh al mes)", 1e6), "hidraulica": ("Hidráulica de España (TWh al mes)", 1e6),
    }
    modelos = gas_tiempo_res["resumen"]["modelos"]
    figura, ejes = plt.subplots(2, 2, figsize=(14, 7.6))
    for eje, (clave, (titulo, escala)) in zip(ejes.flat, titulos.items()):
        reales, prev = gas_tiempo_res["reales"][clave], gas_tiempo_res["previsiones"][clave]
        s = reales.set_index("mes")["real"].sort_index().iloc[-36:] / escala
        p = prev.sort_values("mes")
        eje.fill_between(p["mes"], p["inferior"] / escala, p["superior"] / escala, color=COLOR_PREVISTO, alpha=0.16, lw=0)
        eje.plot(s.index, s.values, color=COLOR_REAL, lw=1.6)
        eje.plot([s.index[-1], *p["mes"]], [s.iloc[-1], *(p["prevision"] / escala)], color=COLOR_PREVISTO, lw=1.8)
        m = modelos[clave]
        eje.set_title(f"{titulo} · acierto {m['acierto_validacion']:.1f} % / {m['acierto_test']:.1f} %".replace(".", ","), fontsize=9.5)
        eje.set_ylim(bottom=0)
        _eje_anios(eje)
    figura.suptitle("Gas y tiempo: entradas del precio de la luz (inestables) · últimos 3 años y previsión a 1 año", x=0.01, ha="left")
    figura.legend(handles=_leyenda_previsiones("previsión"), loc="upper right", ncols=3)
    figura.tight_layout(rect=(0, 0, 1, 0.95))
    return {"gas_tiempo": _guardar_figura(figura, "15_gas_y_tiempo.png")}


@_con_estilo
def _figura_cobertura(cobertura: dict) -> dict[str, str]:
    """Figura 13: cobertura renovable de cada comunidad (generación renovable / demanda, %), último año y previsión."""
    ccaa = pd.DataFrame.from_dict(cobertura["resumen"]["ccaa"], orient="index").dropna(subset=["cobertura_prevista_pct"])
    ccaa = ccaa.sort_values("cobertura_prevista_pct")
    elegido = informe.NOMBRES_MODELO.get(cobertura["resumen"]["modelo"], cobertura["resumen"]["modelo"])
    figura, eje = plt.subplots(figsize=(9.5, 6.4))
    y = np.arange(len(ccaa))
    eje.barh(y - 0.19, ccaa["cobertura_actual_pct"], 0.38, color=COLOR_REAL, edgecolor=FONDO, lw=1, label="últimos 12 meses (real)")
    eje.barh(y + 0.19, ccaa["cobertura_prevista_pct"], 0.38, color=COLOR_PREVISTO, edgecolor=FONDO, lw=1, label=f"próximos 12 meses ({elegido})")
    for yi, valor in zip(y + 0.19, ccaa["cobertura_prevista_pct"]):
        eje.annotate(f"{valor:.0f} %", (valor, yi), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7, color=TINTA_2)
    eje.axvline(100, color=TINTA_2, lw=1, ls=(0, (4, 3)))
    eje.annotate("100 %: genera en renovables lo mismo que consume", (100, 1), xycoords=("data", "axes fraction"), xytext=(4, -10), textcoords="offset points", fontsize=7.5, color=TINTA_2)
    eje.set_yticks(y, ccaa["nombre"], fontsize=8)
    eje.grid(False)
    eje.grid(axis="x")
    eje.set_xlabel("Generación renovable / demanda de la comunidad (%)")
    eje.set_title("Cobertura renovable por comunidad: cuánta energía renovable genera frente a la que consume", pad=24)
    eje.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncols=2, fontsize=7.5)
    return {"cobertura": _guardar_figura(figura, "13_cobertura_renovable_ccaa.png")}


@_con_estilo
def _figuras_renovables(renovables: dict) -> dict[str, str]:
    """% renovable por comunidad: media de los próximos 12 meses frente a la del último año (figura 11) y serie
    mensual de cada comunidad (figura 12)."""
    resumen = renovables["resumen"]
    ccaa = pd.DataFrame.from_dict(resumen["ccaa"], orient="index").sort_values("media_prevista")
    elegido = informe.NOMBRES_MODELO.get(resumen["modelo"], resumen["modelo"])
    figuras: dict[str, str] = {}

    # 11. Media anual: punto azul = último año real, punto naranja = previsión, barra = intervalo 10-90 %.
    figura, eje = plt.subplots(figsize=(9, 6.2))
    y = np.arange(len(ccaa))
    eje.hlines(y, ccaa["media_inferior"], ccaa["media_superior"], color=COLOR_PREVISTO, alpha=0.35, lw=4, label="intervalo 10-90 % de la previsión")
    eje.plot(ccaa["media_12m_actual"], y, "o", ms=6, color=COLOR_REAL, mec=FONDO, mew=1.2, label="últimos 12 meses (real)", zorder=4)
    eje.plot(ccaa["media_prevista"], y, "o", ms=6.5, color=COLOR_PREVISTO, mec=FONDO, mew=1.2, label=f"próximos 12 meses ({elegido})", zorder=5)
    for yi, valor in zip(y, ccaa["media_prevista"]):
        eje.annotate(f"{valor:.0f} %", (valor, yi), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7, color=TINTA_2)
    eje.set_yticks(y, ccaa["nombre"], fontsize=8)
    eje.set_ylim(-0.8, len(ccaa) - 0.2)
    eje.set_xlim(0, 100)
    eje.grid(False)
    eje.grid(axis="x")
    eje.set_xlabel("Generación renovable (% de la generación de la comunidad, media de 12 meses)")
    eje.set_title("Renovables por comunidad: último año y previsión de los próximos 12 meses", pad=28)
    eje.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncols=3, fontsize=7.5)
    figuras["renovables"] = _guardar_figura(figura, "11_renovables_ccaa_1_anio.png")

    # 12. Serie mensual de cada comunidad (de más a menos renovable según la previsión).
    reales, prev = renovables["reales"], renovables["prevision"]
    orden = list(ccaa.index[::-1])
    columnas = 6
    filas = int(np.ceil(len(orden) / columnas))
    figura, ejes = plt.subplots(filas, columnas, figsize=(18, 3.1 * filas), sharey=True)
    for eje, codigo in zip(ejes.flat, orden):
        s = reales[reales["serie"] == codigo].set_index("mes")["real"].iloc[-36:]
        p = prev[prev["serie"] == codigo]
        eje.fill_between(p["mes"], p["inferior"], p["superior"], color=COLOR_PREVISTO, alpha=0.16, lw=0)
        eje.plot(s.index, s.values, color=COLOR_REAL, lw=1.3)
        eje.plot([s.index[-1], *p["mes"]], [s.iloc[-1], *p["prevision"]], color=COLOR_PREVISTO, lw=1.5)
        eje.set_title(f"{ccaa.loc[codigo, 'nombre']} · {ccaa.loc[codigo, 'media_prevista']:.0f} %", fontsize=8.5)
        eje.set_ylim(0, 100)
        _eje_anios(eje)
        eje.tick_params(labelsize=6.5)
    for eje in list(ejes.flat)[len(orden):]:
        eje.axis("off")
    figura.suptitle("Generación renovable mensual por comunidad (%): últimos 3 años y previsión a 1 año", x=0.01, ha="left")
    figura.legend(handles=_leyenda_previsiones(f"previsión ({elegido})"), loc="upper right", ncols=3)
    figura.tight_layout(rect=(0, 0, 1, 0.96))
    figuras["renovables_mensual"] = _guardar_figura(figura, "12_renovables_mensual.png")
    return figuras


def ejecutar_10_anios() -> dict:
    """Previsión de la demanda nacional a 10 años con backtesting plurianual (`cpd.modelos.largo_plazo`)."""
    import json

    from cpd.config import RUTA_DEMANDA_LIMPIA
    from cpd.modelos import largo_plazo as lp

    mensual = pd.read_csv(RUTA_DEMANDA_LIMPIA, parse_dates=["fecha"]).set_index("fecha")["demanda_mwh"]
    anual_twh = lp.demanda_anual(mensual)
    resultado = lp.evaluar(anual_twh)
    prevision = lp.prevision(anual_twh, resultado)
    acierto = float(resultado["acierto"][resultado["elegido"]])
    print(f"  10 años: {resultado['elegido']} · acierto {acierto:.1f} %")
    salida = {
        "modelo": resultado["elegido"], "miembros": resultado["miembros"], "unidad": "TWh",
        "acierto": round(acierto, 1), "mape_medio": round(float(resultado["resumen"][resultado["elegido"]]), 2),
        "historia": [{"anio": int(a), "valor": round(float(v), 1)} for a, v in anual_twh.items()],
        "prevision": [{"anio": int(f.anio), "valor": round(f.prevision_twh, 1), "inferior": round(f.inferior_twh, 1), "superior": round(f.superior_twh, 1)} for f in prevision.itertuples()],
    }
    resultado["backtesting"].to_csv(RUTA_SALIDAS / "backtesting_10_anios.csv", index=False)
    prevision.to_csv(RUTA_SALIDAS / "prevision_10_anios.csv", index=False)
    (RUTA_SALIDAS / "prevision_10_anios.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    return {"resultado": resultado, "prevision": prevision, "json": salida, "acierto": acierto, "figura": _figura_10_anios(anual_twh, resultado, prevision, acierto)}


@_con_estilo
def _figura_10_anios(anual_twh: pd.Series, resultado: dict, prevision: pd.DataFrame, acierto: float) -> str:
    """Historia, lo que habrían previsto varios orígenes del backtesting y previsión a 10 años con su intervalo."""
    elegido = resultado["elegido"]
    figura, eje = plt.subplots(figsize=(12, 4.8))
    eje.fill_between(prevision["anio"], prevision["inferior_twh"], prevision["superior_twh"], color=COLOR_PREVISTO, alpha=0.14, lw=0, label="intervalo 10-90 %")
    bt = resultado["backtesting"]
    bt = bt[bt["modelo"] == elegido]
    for origen in (2011, 2014, 2017, 2020):
        d = bt[bt["origen"] == origen]
        if not d.empty:
            eje.plot([origen, *d["anio"]], [anual_twh.loc[origen], *d["prevision_twh"]], color=COLOR_PREVISTO, alpha=0.5, lw=1, ls=(0, (4, 3)))
    eje.plot([], [], color=COLOR_PREVISTO, alpha=0.6, lw=1, ls=(0, (4, 3)), label="lo que habría previsto desde 2011, 2014, 2017 y 2020")
    eje.plot(anual_twh.index, anual_twh.values, color=COLOR_REAL, label="demanda real", zorder=4)
    ultimo = int(anual_twh.index.max())
    eje.plot([ultimo, *prevision["anio"]], [anual_twh.iloc[-1], *prevision["prevision_twh"]], color=COLOR_PREVISTO, label=f"previsión a 10 años ({informe.NOMBRES_MODELO.get(elegido, elegido)})", zorder=4)
    _punto_final(eje, ultimo, float(anual_twh.iloc[-1]), f"{anual_twh.iloc[-1]:.0f}", COLOR_REAL, arriba=True)
    _punto_final(eje, int(prevision["anio"].iloc[-1]), float(prevision["prevision_twh"].iloc[-1]), f"{prevision['prevision_twh'].iloc[-1]:.0f} TWh", COLOR_PREVISTO)
    eje.set_title(f"Demanda eléctrica nacional: 2007-{ultimo} y previsión a 10 años (acierto en backtesting {acierto:.1f} %)".replace(".", ","))
    eje.set_ylabel("TWh al año")
    eje.xaxis.set_major_locator(MaxNLocator(integer=True))
    eje.legend(loc="lower left")
    return _guardar_figura(figura, "07_demanda_nacional_10_anios.png")


def ejecutar_escenarios(diez: dict, anual_res: dict) -> dict:
    """Escenarios de demanda a 10 años con la capacidad de red otorgada y en trámite (P5, `cpd.modelos.escenarios`)."""
    import json

    from cpd.config import cargar_settings
    from cpd.fuentes.curado import CARPETA_TABLAS
    from cpd.modelos import escenarios as esc

    ajustes = cargar_settings()["escenarios_demanda"]
    factor, realizaciones = float(ajustes["factor_utilizacion"]), [float(r) for r in ajustes["realizaciones"]]
    capacidad = pd.read_csv(CARPETA_TABLAS / "capacidad_ccaa.csv", dtype={"codigo_ccaa": str})
    otorgada, pendiente = float(capacidad["capacidad_demanda_rdt_otorgada_mw"].sum()), float(capacidad["capacidad_demanda_rdt_pendiente_mw"].sum())
    nacional = esc.escenarios_nacionales(diez["prevision"], otorgada, pendiente, factor, realizaciones)
    demanda_ccaa = pd.Series({c: v["ultimos_12m"] for c, v in anual_res["json"]["demanda"]["ccaa"].items()})
    ccaa = esc.por_ccaa(capacidad, demanda_ccaa, factor)
    final = nacional[nacional["anio"] == nacional["anio"].max()].set_index("escenario")
    ultimo = diez["json"]["historia"][-1]
    print(f"  escenarios {int(final['anio'].iloc[0])}: " + ", ".join(f"{k} {v:.0f} TWh" for k, v in final["demanda_twh"].items()))
    salida = {
        "factor_utilizacion": factor, "realizaciones": realizaciones, "otorgada_mw": otorgada, "pendiente_mw": pendiente,
        "otorgada_twh_anio": round(esc.energia_twh(otorgada, factor), 1), "pendiente_twh_anio": round(esc.energia_twh(pendiente, factor), 1),
        "ultimo_real": ultimo, "anio_final": int(final["anio"].iloc[0]),
        "final": {k: {"demanda_twh": round(float(v.demanda_twh), 1), "cambio_pct": round(100 * (float(v.demanda_twh) / ultimo["valor"] - 1), 1)} for k, v in final.iterrows()},
        "ccaa": {
            f.codigo_ccaa: {"ccaa": f.ccaa, "otorgada_mw": f.otorgada_mw, "pendiente_mw": f.pendiente_mw, "demanda_twh": round(f.demanda_twh, 2), "pct_otorgada": round(f.pct_otorgada, 1), "pct_pendiente": round(f.pct_pendiente, 1)}
            for f in ccaa.itertuples() if pd.notna(f.demanda_twh)
        },
    }
    nacional.to_csv(RUTA_SALIDAS / "escenarios_demanda_10_anios.csv", index=False)
    ccaa.to_csv(RUTA_SALIDAS / "escenarios_demanda_ccaa.csv", index=False)
    (RUTA_SALIDAS / "escenarios_demanda.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    datos = {"nacional": nacional, "ccaa": ccaa, "json": salida, "diez": diez}
    return {**datos, "figura": _figura_escenarios(datos)}


@_con_estilo
def _figura_escenarios(datos: dict) -> str:
    """Figura 19: (a) demanda nacional real, previsión tendencial y escenarios con la red otorgada y en trámite;
    (b) energía de la red otorgada y en trámite de cada comunidad frente a su demanda actual (%)."""
    j, nacional, ccaa, diez = datos["json"], datos["nacional"], datos["ccaa"].dropna(subset=["demanda_twh"]), datos["diez"]
    coma = lambda v, d=0: f"{v:,.{d}f}".replace(",", " ").replace(".", ",").replace(" ", ".")  # noqa: E731
    figura, (eje_n, eje_c) = plt.subplots(1, 2, figsize=(16, 6.6), gridspec_kw={"width_ratios": [1.25, 1]})
    historia = pd.DataFrame(diez["json"]["historia"])
    prev = diez["prevision"]
    ultimo = historia.iloc[-1]
    eje_n.fill_between(prev["anio"], prev["inferior_twh"], prev["superior_twh"], color=COLOR_PREVISTO, alpha=0.14, lw=0, label="intervalo 10-90 % (tendencial)")
    eje_n.plot(historia["anio"], historia["valor"], color=COLOR_REAL, label="demanda real", zorder=4)
    estilos = {"tendencial": ((0, ()), 2.0), "techo": ((0, (1, 2)), 1.4)}
    for nombre, d in nacional.groupby("escenario", sort=False):
        ls, lw = estilos.get(nombre, ((0, (5, 3)), 1.3))
        if nombre == "tendencial":
            etiqueta = f"tendencial (validado, {coma(diez['json']['acierto'], 1)} %)"
        elif nombre == "techo":
            etiqueta = "techo: otorgada + en trámite enteras"
        else:
            etiqueta = f"+ {nombre.removeprefix('otorgada_')} % de la red otorgada"
        eje_n.plot([ultimo["anio"], *d["anio"]], [ultimo["valor"], *d["demanda_twh"]], color=COLOR_PREVISTO, ls=ls, lw=lw, label=etiqueta, zorder=3)
        _punto_final(eje_n, int(d["anio"].iloc[-1]), float(d["demanda_twh"].iloc[-1]), f"{coma(d['demanda_twh'].iloc[-1])}", COLOR_PREVISTO)
    eje_n.set_title(f"(a) Demanda de España (TWh/año): escenarios con {coma(j['otorgada_mw'])} MW otorgados y {coma(j['pendiente_mw'])} MW en trámite", fontsize=10, loc="left")
    eje_n.set_ylabel("TWh al año")
    eje_n.xaxis.set_major_locator(MaxNLocator(integer=True))
    eje_n.legend(loc="upper left", fontsize=8)

    ccaa = ccaa.sort_values("pct_otorgada")
    y = np.arange(len(ccaa))
    eje_c.barh(y - 0.2, ccaa["pct_otorgada"], 0.38, color=COLOR_PREVISTO, edgecolor=FONDO, lw=1, label="otorgada")
    eje_c.barh(y + 0.2, ccaa["pct_pendiente"], 0.38, color=COLOR_REAL, edgecolor=FONDO, lw=1, label="en trámite")
    for yi, v in zip(y, ccaa["pct_otorgada"]):
        eje_c.annotate(f"{coma(v)} %", (v, yi - 0.2), xytext=(3, 0), textcoords="offset points", va="center", fontsize=7, color=TINTA_2)
    eje_c.set_yticks(y, ccaa["ccaa"], fontsize=8)
    eje_c.grid(False)
    eje_c.grid(axis="x")
    eje_c.xaxis.set_major_formatter(lambda x, _: f"{x:,.0f}".replace(",", "."))
    eje_c.set_xlabel(f"% de la demanda actual de la comunidad (energía = MW × 8.760 h × {coma(j['factor_utilizacion'], 1)})")
    eje_c.set_title("(b) Red otorgada y en trámite frente a la demanda de cada comunidad", fontsize=10, loc="left")
    eje_c.legend(loc="lower right", fontsize=8)
    figura.suptitle("Escenarios de demanda a 10 años con los nuevos grandes consumos (P5) · supuestos a calibrar, no es una previsión", x=0.01, ha="left")
    figura.tight_layout(rect=(0, 0, 1, 0.94))
    return _guardar_figura(figura, "19_escenarios_demanda.png")


def ejecutar_socioeconomico(anual_res: dict) -> dict:
    """Impacto socioeconómico del CPD de referencia (E39-E41) con las Tablas Input-Output del INE
    (`cpd.modelos.socioeconomico`). El consumo es la mediana del previsto en las provincias a 1 año."""
    import json

    from cpd import simulator as simulador
    from cpd.config import cargar_settings
    from cpd.fuentes.curado import CARPETA_TABLAS
    from cpd.modelos import socioeconomico as se

    ajustes = cargar_settings()
    validos = {f.name for f in dataclasses.fields(simulador.CPDParams)}
    params = simulador.CPDParams(**{k: v for k, v in ajustes.get("cpd_por_defecto", {}).items() if k in validos})
    reparto = {str(k): float(v) for k, v in ajustes["impacto_socioeconomico"]["reparto_capex"].items()}
    ramas = pd.read_csv(CARPETA_TABLAS / "tio_ramas.csv", dtype={"codigo": str})
    leontief = pd.read_csv(CARPETA_TABLAS / "tio_leontief_interior.csv", dtype={"codigo": str}).set_index("codigo")
    provincias_op = anual_res["json"]["operacion"]["provincias"]
    consumo = float(np.median([p["consumo_previsto_mwh"] for p in provincias_op.values()]))
    res = se.impacto(params, dict(ajustes["precios"]), reparto, consumo, ramas, leontief)
    c, o = res["construccion"], res["operacion"]
    paro = pd.read_csv(CARPETA_TABLAS / "paro.csv", dtype={"codigo_provincia": str})
    mes_paro = paro["mes"].max()
    paro_ult = paro[paro["mes"] == mes_paro].set_index("codigo_provincia")["paro_registrado"]
    tabla = se.por_provincia(o["directo"]["vab_meur"], o["directo"]["empleo_etc"], pd.read_csv(CARPETA_TABLAS / "pib_provincia.csv", dtype={"codigo_provincia": str}), paro_ult)
    print(
        f"  construcción: {c['empleo_etc']:.0f} empleos-año, VAB {c['vab_meur']:.0f} M€ (de {params.inversion_eur / 1e6:.0f} M€, {c['demanda_interior_meur']:.0f} M€ en España); "
        f"operación: {o['directo']['empleo_etc']:.0f} directos + {o['indirecto']['empleo_etc']:.0f} indirectos, VAB {o['vab_total_meur']:.0f} M€/año"
    )
    nombres = {k: v.get("nombre", k) for k, v in anual_res["json"]["temperatura"]["provincias"].items()}
    redondeo = lambda d: {k: round(float(v), 1) for k, v in d.items()}  # noqa: E731
    salida = {
        "fuente": "INE, Tablas Input-Output 2022 (inversa interior de Leontief) y Contabilidad Regional (PIB provincial)",
        "cpd": {"inversion_eur": params.inversion_eur, "personal": params.personal, "potencia_ti_mw": params.potencia_ti_mw},
        "reparto_capex": reparto, "consumo_mwh": round(consumo, 0),
        "construccion": {
            "inversion_meur": params.inversion_eur / 1e6, "en_espana_meur": round(c["demanda_interior_meur"], 1),
            "produccion_meur": round(c["produccion_meur"], 1), "vab_meur": round(c["vab_meur"], 1), "empleo_anio": round(c["empleo_etc"], 0),
        },
        "operacion": {
            "directo": redondeo(o["directo"]), "indirecto": {"empleo_etc": round(o["indirecto"]["empleo_etc"], 0), "vab_meur": round(o["indirecto"]["vab_meur"], 1)},
            "empleo_total": round(o["empleo_total"], 0), "vab_total_meur": round(o["vab_total_meur"], 1),
            "multiplicador_empleo": round(res["multiplicador_empleo_operacion"], 2), "cuentas_meur": {k: round(v / 1e6, 2) for k, v in res["operacion_eur"].items()},
        },
        "mes_paro": str(mes_paro)[:7], "anio_pib": int(tabla["anio_pib"].iloc[0]),
        "provincias": {
            f.codigo_provincia: {"nombre": nombres.get(f.codigo_provincia, f.codigo_provincia), "pct_pib": round(f.pct_pib, 3), "pct_paro_directo": round(f.pct_paro_directo, 2)}
            for f in tabla.itertuples()
        },
    }
    c["por_producto"].to_csv(RUTA_SALIDAS / "socioeconomico_construccion_por_producto.csv")
    o["indirecto"]["por_producto"].to_csv(RUTA_SALIDAS / "socioeconomico_operacion_por_producto.csv")
    tabla.to_csv(RUTA_SALIDAS / "socioeconomico_provincia.csv", index=False)
    (RUTA_SALIDAS / "impacto_socioeconomico.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    datos = {"resultado": res, "tabla": tabla, "ramas": ramas, "json": salida}
    return {**datos, "figura": _figura_socioeconomico(datos)}


@_con_estilo
def _figura_socioeconomico(datos: dict) -> str:
    """Figura 18: (a) empleo de la construcción por producto (empleos-año), (b) empleo de un año de operación (directo e
    indirecto por producto) y (c) VAB directo del CPD sobre el PIB de las 15 provincias donde más pesa."""
    res, ramas, j = datos["resultado"], datos["ramas"].set_index("codigo"), datos["json"]
    corto = lambda codigo: textwrap.shorten(str(ramas.loc[codigo, "nombre"]), 42, placeholder="…")  # noqa: E731
    coma = lambda v, d=0: f"{v:,.{d}f}".replace(",", " ").replace(".", ",").replace(" ", ".")  # noqa: E731
    figura, ejes = plt.subplots(1, 3, figsize=(17, 6.6), gridspec_kw={"width_ratios": [1.15, 1.15, 1]})

    def barras(eje, serie: pd.Series, titulo: str, unidad: str, dec: int = 0, colores: list[str] | None = None) -> None:
        y = np.arange(len(serie))
        eje.barh(y, serie.to_numpy(), 0.62, color=colores or COLOR_PREVISTO, edgecolor=FONDO, lw=1)
        for yi, v in zip(y, serie.to_numpy()):
            eje.annotate(f"{coma(v, dec)}{unidad}", (v, yi), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=TINTA_2)
        eje.set_yticks(y, serie.index, fontsize=8)
        eje.invert_yaxis()
        eje.set_xlim(0, serie.max() * 1.25)
        eje.xaxis.set_major_formatter(lambda x, _: f"{x:,.10g}".replace(",", " ").replace(".", ",").replace(" ", "."))
        eje.set_title(titulo, fontsize=9.5, loc="left")
        eje.grid(False)
        eje.grid(axis="x")

    c = res["construccion"]["por_producto"]["empleo_etc"].head(8)
    barras(ejes[0], c.rename(index=corto), f"(a) Construcción: {coma(j['construccion']['empleo_anio'])} empleos-año", "")
    ind = res["operacion"]["indirecto"]["por_producto"]["empleo_etc"].head(7)
    oper = pd.concat([pd.Series({"Plantilla del CPD (directo)": j["operacion"]["directo"]["empleo_etc"]}), ind.rename(index=corto)])
    barras(
        ejes[1], oper, f"(b) Operación: {coma(j['operacion']['empleo_total'])} empleos al año (×{coma(j['operacion']['multiplicador_empleo'], 1)})", "",
        colores=[COLOR_REAL] + [COLOR_PREVISTO] * len(ind),
    )
    ejes[1].annotate("azul: plantilla del CPD (directo) · naranja: proveedores (indirecto)", (0, -0.09), xycoords="axes fraction", fontsize=7.5, color=TINTA_3)
    prov = pd.DataFrame.from_dict(j["provincias"], orient="index").nlargest(15, "pct_pib")
    barras(ejes[2], prov.set_index("nombre")["pct_pib"], f"(c) VAB directo / PIB provincial ({j['anio_pib']})", " %", 2)
    figura.suptitle(
        f"Impacto socioeconómico del CPD de referencia ({coma(j['construccion']['inversion_meur'])} M€, {j['cpd']['personal']} empleados): INE, tablas input-output 2022",
        x=0.01, ha="left",
    )
    figura.tight_layout(rect=(0, 0, 1, 0.94))
    return _guardar_figura(figura, "18_impacto_socioeconomico.png")


def ejecutar_medio_plazo() -> dict:
    """Sostenibilidad operativa del CPD a 10 años (A3): temperatura → PUE → consumo y reserva de agua del ámbito
    (`cpd.modelos.medio_plazo`)."""
    import json

    from cpd import simulator as simulador
    from cpd.config import cargar_settings
    from cpd.fuentes.curado import CARPETA_TABLAS
    from cpd.fuentes.embalses import AMBITO_POR_PROVINCIA
    from cpd.modelos import medio_plazo as medio

    ajustes = cargar_settings()
    validos = {f.name for f in dataclasses.fields(simulador.CPDParams)}
    params = simulador.CPDParams(**{k: v for k, v in ajustes.get("cpd_por_defecto", {}).items() if k in validos})
    nombres = pd.read_csv(CARPETA_TABLAS / "provincias.csv", dtype={"codigo_provincia": str}).set_index("codigo_provincia")["provincia"].to_dict()

    temp = medio.anual_completo(pd.read_csv(CARPETA_TABLAS / "clima_mensual_largo.csv", dtype={"codigo_provincia": str}), "mes", "codigo_provincia", "tmedia_c")
    res_t = medio.evaluar(temp, medio.PRIMER_ORIGEN_TEMPERATURA)
    prev_t = medio.prevision(temp, res_t)
    consumo = medio.validar_consumo(res_t, params)
    tabla_op = medio.operacion_10_anios(prev_t, temp.iloc[-10:].mean(), params)
    # Sensibilidad (no es la previsión elegida): si sigue la tendencia de 30 años, cuánto cambiarían la temperatura y el PUE.
    con_tendencia = medio.candidatos()["media_10_con_tendencia"]
    t_tendencia = pd.Series({c: float(con_tendencia(temp[c].dropna(), medio.HORIZONTE_ANIOS)[-1]) for c in temp.columns})
    escenario = {
        "temp_final_c": round(float(t_tendencia.mean()), 2),
        "pendiente_c_decada": round(float(np.mean([10 * medio._pendiente(temp[c].dropna()) for c in temp.columns])), 2),
        "pue_final": round(float(np.mean([simulador.pue_estimado(t, params.tipo_refrigeracion) for t in t_tendencia])), 3),
        "cambio_consumo_pct": round(float(100 * (medio.consumo_cpd(t_tendencia.to_numpy(), params).mean() / medio.consumo_cpd(temp.iloc[-10:].mean().to_numpy(), params).mean() - 1)), 2),
    }

    reservas = medio.anual_completo(pd.read_csv(CARPETA_TABLAS / "reservas_ambito_mensual.csv"), "mes", "ambito", "reserva_pct_media_mes")
    res_r = medio.evaluar(reservas, medio.PRIMER_ORIGEN_RESERVAS)
    prev_r = medio.prevision(reservas, res_r, limites=(0.0, 100.0))
    decada_t, decada_r = medio.acierto_media_decada(res_t), medio.acierto_media_decada(res_r)
    print(
        f"  temperatura a 10 años: {res_t['elegido']} · {res_t['acierto_validacion']:.1f} % / {res_t['acierto_test']:.1f} % "
        f"(MAE {res_t['mae_validacion']:.2f} / {res_t['mae_test']:.2f} °C); consumo {consumo['acierto_validacion']:.1f} % / {consumo['acierto_test']:.1f} %"
    )
    print(f"  reservas a 10 años: año a año {res_r['acierto_validacion']:.1f} % / {res_r['acierto_test']:.1f} %; media de la década {decada_r['acierto_decada_validacion']:.1f} % / {decada_r['acierto_decada_test']:.1f} %")

    def resumen(res: dict, decada: dict, anual: pd.DataFrame) -> dict:
        return {
            "modelo": res["elegido"], "miembros": res["miembros"],
            "acierto_validacion": round(res["acierto_validacion"], 1), "acierto_test": round(res["acierto_test"], 1),
            "mae_validacion": round(res["mae_validacion"], 2), "mae_test": round(res["mae_test"], 2),
            "acierto_decada_validacion": round(decada["acierto_decada_validacion"], 1), "acierto_decada_test": round(decada["acierto_decada_test"], 1),
            "origenes_validacion": [res["origenes_validacion"][0], res["origenes_validacion"][-1]], "origen_test": res["origen_test"],
            "historia_desde": int(anual.index.min()), "historia_hasta": int(anual.index.max()),
        }

    ultimo = int(temp.index.max())
    salida = {
        "anio_base": ultimo, "anio_final": ultimo + medio.HORIZONTE_ANIOS,
        "cpd": {"potencia_ti_mw": params.potencia_ti_mw, "factor_carga": params.factor_carga, "tipo_refrigeracion": params.tipo_refrigeracion},
        "temperatura": {
            **resumen(res_t, decada_t, temp), "consumo_acierto_validacion": round(consumo["acierto_validacion"], 1), "consumo_acierto_test": round(consumo["acierto_test"], 1),
            "media_espana_10a_c": round(float(temp.iloc[-10:].mean().mean()), 2), "media_espana_final_c": round(float(tabla_op["temp_final_c"].mean()), 2),
            "pue_medio_final": round(float(tabla_op["pue_final"].mean()), 3), "escenario_tendencia": escenario,
        },
        "reservas": resumen(res_r, decada_r, reservas),
        "provincias": {}, "ambitos": {},
    }
    for ambito, d in prev_r.groupby("serie"):
        salida["ambitos"][ambito] = {
            "media_10a_real_pct": round(float(reservas[ambito].iloc[-10:].mean()), 1),
            "media_decada_prevista_pct": round(float(d["prevision"].mean()), 1),
            "inferior_anual_pct": round(float(d["inferior"].min()), 1),
        }
    final_t = prev_t[prev_t["horizonte_anios"] == medio.HORIZONTE_ANIOS].set_index("serie")
    for f in tabla_op.itertuples():
        ambito = AMBITO_POR_PROVINCIA.get(f.codigo_provincia)
        salida["provincias"][f.codigo_provincia] = {
            "nombre": nombres.get(f.codigo_provincia, f.codigo_provincia),
            "temp_10a_c": round(f.temp_10a_c, 2), "temp_final_c": round(f.temp_final_c, 2),
            "temp_final_inferior_c": round(float(final_t.loc[f.codigo_provincia, "inferior"]), 2), "temp_final_superior_c": round(float(final_t.loc[f.codigo_provincia, "superior"]), 2),
            "pue_10a": round(f.pue_10a, 3), "pue_final": round(f.pue_final, 3),
            "consumo_10a_mwh": round(f.consumo_10a_mwh, 0), "consumo_final_mwh": round(f.consumo_final_mwh, 0), "cambio_consumo_pct": round(f.cambio_consumo_pct, 2),
            "ambito": ambito, "reserva_decada_prevista_pct": salida["ambitos"].get(ambito, {}).get("media_decada_prevista_pct") if ambito else None,
        }
    for nombre, res in (("temperatura", res_t), ("reservas", res_r)):
        res["metricas"].to_csv(RUTA_SALIDAS / f"medio_plazo_metricas_{nombre}.csv", index=False)
    prev_t.to_csv(RUTA_SALIDAS / "medio_plazo_prevision_temperatura.csv", index=False)
    prev_r.to_csv(RUTA_SALIDAS / "medio_plazo_prevision_reservas.csv", index=False)
    tabla_op.to_csv(RUTA_SALIDAS / "medio_plazo_operacion_cpd.csv", index=False)
    (RUTA_SALIDAS / "prevision_medio_plazo.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    datos = {"temp": temp, "res_t": res_t, "prev_t": prev_t, "reservas": reservas, "res_r": res_r, "prev_r": prev_r, "tabla": tabla_op, "json": salida}
    return {**datos, "figura": _figura_medio_plazo(datos)}


@_con_estilo
def _figura_medio_plazo(datos: dict) -> str:
    """Figura 16: (a) temperatura media de España (media de las 52 capitales), lo que se habría previsto en el test y
    previsión a 10 años; (b) reserva media de los embalses por ámbito: últimos 10 años y próxima década."""
    j = datos["json"]
    temp, res_t, prev_t = datos["temp"], datos["res_t"], datos["prev_t"]
    figura, (eje_t, eje_r) = plt.subplots(1, 2, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1.35, 1]})

    espana = temp.mean(axis=1)
    pred = res_t["predicciones"]
    test = pred[(pred["modelo"] == res_t["elegido"]) & (pred["particion"] == "test")].groupby("anio")["prevision"].mean()
    futuro = prev_t.groupby("anio")[["prevision", "inferior", "superior"]].mean()
    origen_test, ultimo = res_t["origen_test"], int(espana.index.max())
    eje_t.fill_between(futuro.index, futuro["inferior"], futuro["superior"], color=COLOR_PREVISTO, alpha=0.14, lw=0, label="intervalo 10-90 % (media de las bandas)")
    eje_t.plot(espana.index, espana.values, color=COLOR_REAL, label="real (NASA POWER, media de las 52 capitales)", zorder=4)
    eje_t.plot([origen_test, *test.index], [espana.loc[origen_test], *test.values], color=COLOR_PREVISTO, alpha=0.6, lw=1.2, ls=(0, (4, 3)), label=f"lo que habría previsto desde {origen_test} (test)")
    nombre = informe.NOMBRES_MODELO.get(res_t["elegido"], res_t["elegido"])
    eje_t.plot([ultimo, *futuro.index], [espana.iloc[-1], *futuro["prevision"]], color=COLOR_PREVISTO, label=f"previsión a 10 años ({nombre})", zorder=4)
    _punto_final(eje_t, ultimo, float(espana.iloc[-1]), f"{espana.iloc[-1]:.1f} °C".replace(".", ","), COLOR_REAL, arriba=True)
    _punto_final(eje_t, int(futuro.index[-1]), float(futuro["prevision"].iloc[-1]), f"{futuro['prevision'].iloc[-1]:.1f} °C".replace(".", ","), COLOR_PREVISTO)
    t = j["temperatura"]
    eje_t.set_title(f"(a) Temperatura media anual · acierto {t['acierto_validacion']:.1f} % validación, {t['acierto_test']:.1f} % test".replace(".", ","), fontsize=10.5)
    eje_t.set_ylabel("°C")
    eje_t.xaxis.set_major_locator(MaxNLocator(integer=True))
    eje_t.legend(loc="upper left", fontsize=8)

    ambitos = pd.DataFrame.from_dict(j["ambitos"], orient="index").sort_values("media_decada_prevista_pct")
    y = np.arange(len(ambitos))
    eje_r.hlines(y, ambitos["media_10a_real_pct"], ambitos["media_decada_prevista_pct"], color=TINTA_3, lw=1, zorder=1)
    eje_r.plot(ambitos["media_10a_real_pct"], y, "o", ms=6, color=COLOR_REAL, mec=FONDO, mew=1.2, label=f"media real {ultimo - 9}-{ultimo}", zorder=3)
    eje_r.plot(ambitos["media_decada_prevista_pct"], y, "o", ms=6.5, color=COLOR_PREVISTO, mec=FONDO, mew=1.2, label=f"media prevista {ultimo + 1}-{ultimo + 10}", zorder=4)
    eje_r.set_yticks(y, ambitos.index, fontsize=8)
    eje_r.set_xlim(0, 100)
    eje_r.grid(False)
    eje_r.grid(axis="x")
    eje_r.set_xlabel("Reserva media de los embalses (% de la capacidad)")
    r = j["reservas"]
    eje_r.set_title(f"(b) Reserva media de la década · acierto {r['acierto_decada_validacion']:.1f} % / {r['acierto_decada_test']:.1f} %".replace(".", ","), fontsize=10.5)
    eje_r.legend(loc="lower right", fontsize=8)
    figura.suptitle(f"Medio plazo (10 años): clima y agua para la operación del CPD ({ultimo + 1}-{ultimo + 10})", x=0.01, ha="left")
    figura.tight_layout(rect=(0, 0, 1, 0.95))
    return _guardar_figura(figura, "16_medio_plazo_10_anios.png")


def ejecutar_sismico() -> dict:
    """Probabilidad de algún terremoto M ≥ 3 el año siguiente por provincia (`cpd.modelos.sismico`)."""
    from cpd.fuentes.curado import CARPETA_TABLAS
    from cpd.fuentes.provincias import CODIGOS
    from cpd.modelos import sismico

    panel = sismico.panel_anual(pd.read_csv(CARPETA_TABLAS / "sismos.csv", dtype={"codigo_provincia": str}), sorted(CODIGOS))
    ruta_norma = CARPETA_TABLAS / "peligrosidad_sismica.csv"
    norma = pd.read_csv(ruta_norma, dtype={"codigo_provincia": str}) if ruta_norma.exists() else None
    resultado = sismico.evaluar(panel, norma)
    m = resultado["metricas"].set_index(["modelo", "particion"])
    print(f"  elegido {resultado['elegido']} · accuracy {100 * m.loc[(resultado['elegido'], 'validacion'), 'accuracy']:.1f} % (validación)")
    resultado["metricas"].to_csv(RUTA_SALIDAS / "metricas_sismico.csv", index=False)
    resultado["prevision"].to_csv(RUTA_SALIDAS / "prevision_sismico.csv", index=False)
    return resultado


def control_de_acierto(anual_res: dict, diez: dict, prob: dict, medio: dict | None = None) -> pd.DataFrame:
    """Tabla del requisito de acierto (≥ 85 %, < 99,9 %) de los modelos que usa el proyecto, y su gráfico."""
    from cpd.modelos.metricas import ACIERTO_MINIMO, ACIERTO_OBJETIVO, ACIERTO_SOSPECHOSO, control_acierto

    j = anual_res["json"]
    filas = [
        ("Demanda por comunidad a 1 año", j["demanda"]["acierto_validacion"], j["demanda"]["acierto_test"], "100 − WAPE"),
        ("Reservas de agua a 1 año", j["reservas"]["acierto_validacion"], j["reservas"]["acierto_test"], "100 − WAPE"),
        ("Temperatura por provincia a 1 año", j["temperatura"]["acierto_validacion"], j["temperatura"]["acierto_test"], "100 − WAPE (en °C)"),
        ("Renovables por comunidad a 1 año (mes a mes)", j["renovables"]["acierto_validacion"], j["renovables"]["acierto_test"], "100 − WAPE"),
        ("Renovables por comunidad: % medio de 12 meses", j["renovables"]["acierto_anual_validacion"], j["renovables"]["acierto_anual_test"], "100 − WAPE de la media anual"),
        ("Generación renovable por comunidad a 1 año (mes a mes)", j["cobertura_renovable"]["acierto_validacion"], j["cobertura_renovable"]["acierto_test"], "100 − WAPE (MWh)"),
        ("Generación renovable por comunidad: total de 12 meses", j["cobertura_renovable"]["acierto_anual_validacion"], j["cobertura_renovable"]["acierto_anual_test"], "100 − WAPE del total anual"),
        ("Operación del CPD a 1 año: consumo", j["operacion"]["acierto_consumo"], None, f"100 − WAPE del total anual ({j['operacion']['origenes']} orígenes comunes)"),
        ("Operación del CPD a 1 año: emisiones", j["operacion"]["acierto_emisiones"], None, f"100 − WAPE del total anual ({j['operacion']['origenes']} orígenes comunes)"),
    ]
    if "impacto_local" in j:
        filas.append(
            ("Impacto eléctrico local a 1 año (P2)", j["impacto_local"]["acierto_validacion"], j["impacto_local"]["acierto_test"], "100 − WAPE del % del CPD sobre la demanda de su comunidad")
        )
    nombres_gt = {"gas": "Gas natural (MIBGAS)", "eolica": "Eólica de España (tiempo)", "solar": "Solar de España (tiempo)", "hidraulica": "Hidráulica de España (tiempo)"}
    for clave, m in (j.get("gas_tiempo") or {}).get("modelos", {}).items():
        filas.append((f"{nombres_gt.get(clave, clave)} a 1 año · entrada del precio, inestable", m["acierto_validacion"], m["acierto_test"], "100 − WAPE"))
    filas += [
        ("Precio de la luz a 1 año", j["precio"]["acierto_validacion"], j["precio"]["acierto_test"], "100 − WAPE"),
        ("Demanda nacional a 10 años", diez["acierto"], None, "100 − WAPE (backtesting 2012-2025)"),
    ]
    if medio is not None:
        t, r = medio["json"]["temperatura"], medio["json"]["reservas"]
        filas += [
            ("Temperatura por provincia a 10 años", t["acierto_validacion"], t["acierto_test"], f"100 − WAPE (en °C; test desde {t['origen_test']})"),
            ("Operación del CPD a 10 años: consumo", t["consumo_acierto_validacion"], t["consumo_acierto_test"], "100 − WAPE (temperatura prevista → PUE → consumo)"),
            ("Reservas de agua a 10 años: media de la década", r["acierto_decada_validacion"], r["acierto_decada_test"], "100 − WAPE de la media de los 10 años"),
            ("Reservas de agua a 10 años: año a año", r["acierto_validacion"], r["acierto_test"], "100 − WAPE de cada año"),
        ]
    filas.append(("Probabilidad de CPD (prob_cpd)", 100 * prob["metricas_umbral"]["accuracy"], None, "accuracy fuera de pliegue"))
    if "sismico" in anual_res:
        s = anual_res["sismico"]
        m = s["metricas"].set_index(["modelo", "particion"])
        filas.append(
            (
                "Riesgo sísmico: algún M ≥ 3 el año siguiente", 100 * m.loc[(s["elegido"], "validacion"), "accuracy"],
                100 * m.loc[(s["elegido"], "test"), "accuracy"], f"accuracy (validación {s['anios_validacion']}, test {s['anio_test']})",
            )
        )
    tabla = pd.DataFrame(filas, columns=["modelo", "acierto_validacion", "acierto_test", "definicion"])
    peor = tabla[["acierto_validacion", "acierto_test"]].min(axis=1)
    mejor = tabla[["acierto_validacion", "acierto_test"]].max(axis=1)
    tabla["estado"] = [control_acierto(p) if m < ACIERTO_SOSPECHOSO else control_acierto(m) for p, m in zip(peor, mejor)]
    tabla.to_csv(RUTA_SALIDAS / "control_acierto.csv", index=False)
    for fila in tabla.itertuples():
        if not fila.estado.startswith("cumple"):
            print(f"  AVISO control de acierto: {fila.modelo} → {fila.estado}")

    anual_res["figuras"]["control"] = _figura_control(tabla)
    return tabla


@_con_estilo
def _figura_control(tabla: pd.DataFrame) -> str:
    """Barras de acierto (validación y test) de cada modelo frente al mínimo, el objetivo y el umbral de sospecha."""
    from cpd.modelos.metricas import ACIERTO_MINIMO, ACIERTO_OBJETIVO, ACIERTO_SOSPECHOSO

    coma = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    figura, eje = plt.subplots(figsize=(11, 1.6 + 0.62 * len(tabla)))
    y = np.arange(len(tabla))
    con_test = tabla["acierto_test"].notna().to_numpy()
    y_val = y - 0.18 * con_test
    eje.barh(y_val, tabla["acierto_validacion"], 0.36, color=COLOR_REAL, edgecolor=FONDO, lw=1, label="validación / backtesting")
    eje.barh(y[con_test] + 0.18, tabla.loc[con_test, "acierto_test"], 0.36, color=COLOR_PREVISTO, edgecolor=FONDO, lw=1, label="test")
    for yi, valor in zip(y_val, tabla["acierto_validacion"]):
        eje.annotate(coma(valor), (valor, yi), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=TINTA_2)
    for yi, valor in zip(y[con_test] + 0.18, tabla.loc[con_test, "acierto_test"]):
        eje.annotate(coma(valor), (valor, yi), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=TINTA_2)
    for x, texto, alineacion, altura in ((ACIERTO_MINIMO, "mínimo 85 % ", "right", 4), (ACIERTO_OBJETIVO, " objetivo 90 %", "left", 4), (ACIERTO_SOSPECHOSO, "99,9 %: sospecha de fuga de datos", "right", 16)):
        eje.axvline(x, color=TINTA_2 if x == ACIERTO_MINIMO else TINTA_3, lw=1, ls="-" if x == ACIERTO_MINIMO else (0, (4, 3)), zorder=1)
        eje.annotate(texto, (x, 1), xycoords=("data", "axes fraction"), xytext=(0, altura), textcoords="offset points", ha=alineacion, fontsize=7.5, color=TINTA_2)
    eje.set_yticks(y, [f"{m}\n{e}" for m, e in zip(tabla["modelo"], tabla["estado"])], fontsize=8.5)
    eje.grid(False)
    eje.grid(axis="x")
    eje.set_xlim(0, 104)
    eje.set_xlabel("Acierto (%)")
    eje.set_title("Control de acierto de los modelos (requisito: 85 % ≤ acierto < 99,9 %)", pad=30)
    eje.legend(loc="upper left", bbox_to_anchor=(0, -0.13), ncols=2)
    eje.invert_yaxis()
    return _guardar_figura(figura, "08_control_acierto.png")


def main() -> None:
    """Punto de entrada de `python -m cpd.modelos`."""
    parser = argparse.ArgumentParser(description="EDA, modelos e informes del Proyecto 3")
    parser.add_argument("--sin-eda", action="store_true", help="no regenera las figuras ni el informe EDA")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # consola de Windows (cp1252): que «→» o «≥» no paren la ejecución
        sys.stdout.reconfigure(errors="replace")
    inicio = time.time()
    fecha = dt.date.today().strftime("%d/%m/%Y")
    panel = pd.read_parquet(RUTA_PANEL)

    print("Diccionario de features")
    filas = [{"modelo": "demanda_ccaa", "horizonte_meses": h, **dataclasses.asdict(f)} for h in md.HORIZONTES for f in diccionario_features_demanda(h)]
    filas += [{"modelo": "prob_cpd", "horizonte_meses": None, **dataclasses.asdict(f)} for f in diccionario_features_provincia()]
    filas += [{"modelo": "precio_luz", "horizonte_meses": "1-12", **dataclasses.asdict(f)} for f in fprecio.diccionario_features_precio()]
    RUTA_SALIDAS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(RUTA_SALIDAS / "diccionario_features.csv", index=False)

    if not args.sin_eda:
        print("EDA")
        eda = meda.generar(panel)
        eda["atipicos_demanda"].to_csv(RUTA_SALIDAS / "atipicos_demanda.csv", index=False)
        _escribir(informe.informe_eda(eda, fecha), RUTA_DOCS / "analisis" / "eda_panel.md")

    print("Demanda por comunidad")
    demanda = ejecutar_demanda(panel)
    print("Probabilidad de CPD por provincia")
    prob, tabla, figura_roc = ejecutar_prob_cpd(panel)
    print("Precio de la luz")
    precio = ejecutar_precio()
    print("Previsión a 1 año (demanda y precio)")
    anual_res = ejecutar_anual(panel)
    print("Demanda nacional a 10 años")
    diez = ejecutar_10_anios()
    print("Escenarios de demanda con los nuevos grandes consumos (P5)")
    anual_res["escenarios"] = ejecutar_escenarios(diez, anual_res)
    print("Medio plazo: clima y agua a 10 años (A3)")
    anual_res["medio_plazo"] = ejecutar_medio_plazo()
    print("Impacto socioeconómico (E39-E41)")
    anual_res["socioeconomico"] = ejecutar_socioeconomico(anual_res)
    print("Riesgo sísmico (P8)")
    anual_res["sismico"] = ejecutar_sismico()
    print("Control de acierto")
    control = control_de_acierto(anual_res, diez, prob, anual_res["medio_plazo"])

    print("Informes")
    _escribir(informe.informe_anual(anual_res, fecha, diez, control), RUTA_DOCS / "analisis" / "previsiones_1_anio.md")
    _escribir(informe.informe_metricas(demanda, prob, fecha, precio), RUTA_DOCS / "analisis" / "metricas.md")
    _escribir(informe.ficha_demanda(demanda, fecha), RUTA_DOCS / "modelos" / "demanda_ccaa.md")
    _escribir(informe.ficha_prob_cpd(prob, tabla, figura_roc, fecha), RUTA_DOCS / "modelos" / "prob_cpd.md")
    _escribir(informe.ficha_precio(precio, fecha), RUTA_DOCS / "modelos" / "precio_luz.md")
    print(f"Hecho en {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()
