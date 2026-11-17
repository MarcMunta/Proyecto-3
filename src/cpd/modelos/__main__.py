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
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
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
    return resultado, tabla, _figura_roc(tabla, resultado["probabilidades"])


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
COLORES_MODELO = {
    "combinacion": "#e47b2f", "ets": "#5b8def", "estacional": "#9b59b6", "ridge": "#2c714e", "ridge_gas": "#16a085",
    "naive": "#7f8c8d", "media_12m": "#b8383f", "gradient_boosting": "#c9a227", "estacional_tendencia": "#8e6c4a",
}


def _guardar_figura(figura: plt.Figure, nombre: str) -> str:
    RUTA_FIG_PREVISIONES.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_FIG_PREVISIONES / nombre
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


def _figuras_anual(precio: dict, demanda: dict, mensual: pd.DataFrame, serie: pd.DataFrame) -> dict[str, str]:
    """Gráficos de la previsión a 1 año: precio, demanda por comunidad, errores por horizonte, modelos y backtesting."""
    figuras: dict[str, str] = {}
    nombre = lambda m: informe.NOMBRES_MODELO.get(m, m)  # noqa: E731

    # 1. Precio: historia, test (lo que habría previsto hace un año) y previsión de los 12 meses siguientes.
    r, f = precio["resultado"], precio["prevision"]
    historia = mensual["precio_eur_mwh"].dropna().loc["2021-01-01":]
    test = r["predicciones"].query("particion == 'test' and modelo == @r['elegido']").sort_values("mes")
    figura, eje = plt.subplots(figsize=(12, 4.8))
    eje.plot(historia.index, historia.values, color="#2c714e", lw=1.8, label="precio real")
    eje.plot(test["mes"], test["prevision"], color="#e47b2f", ls=":", lw=1.6, label=f"lo que habría previsto hace un año (test, MAE {precio['error_test']:.0f} €/MWh)")
    eje.plot(f["mes"], f["prevision"], color="#e47b2f", lw=2.2, label=f"previsión a 1 año ({nombre(r['elegido'])})")
    eje.fill_between(f["mes"], f["inferior"], f["superior"], color="#e47b2f", alpha=0.15, label="intervalo mensual 10-90 %")
    gas = mensual.get("gas_y1_eur_mwh")
    if gas is not None:
        eje2 = eje.twinx()
        eje2.plot(gas.dropna().loc["2021-01-01":].index, gas.dropna().loc["2021-01-01":].values, color="#5b8def", lw=1, alpha=0.7, label="futuro de gas a 1 año (MIBGAS, eje derecho)")
        eje2.set_ylabel("Gas, €/MWh")
        eje2.legend(loc="upper center", fontsize=8)
    tope = 1.4 * max(float(historia.max()), float(f["prevision"].max()))
    if float(f["superior"].max()) > tope:
        eje.set_ylim(0, tope)
        eje.annotate(f"el extremo alto del intervalo llega a {f['superior'].max():.0f} €/MWh (recortado)", xy=(0.99, 0.03), xycoords="axes fraction", ha="right", va="bottom", fontsize=8, color="#a0522d")
    eje.set_title("Precio de la luz (spot, media mensual): real, test y previsión a 1 año")
    eje.set_xlabel("Mes")
    eje.set_ylabel("Electricidad, €/MWh")
    eje.legend(loc="upper left", fontsize=8)
    figuras["precio"] = _guardar_figura(figura, "01_precio_luz_1_anio.png")

    # 2. Demanda: una gráfica por comunidad (últimos 3 años + 12 meses previstos con su intervalo).
    fd_ = demanda["prevision"]
    codigos = sorted(fd_["serie"].unique())
    nombres_ccaa = serie.drop_duplicates("codigo_ccaa").set_index("codigo_ccaa")["ccaa"]
    figura, ejes = plt.subplots(4, 5, figsize=(17, 12))
    for eje, codigo in zip(ejes.flat, codigos):
        s = serie[serie["codigo_ccaa"] == codigo].set_index("mes")["demanda_mwh"].iloc[-36:] / 1e3
        p = fd_[fd_["serie"] == codigo]
        eje.plot(s.index, s.values, color="#2c714e", lw=1.2)
        eje.plot(p["mes"], p["prevision"] / 1e3, color="#e47b2f", lw=1.6)
        eje.fill_between(p["mes"], p["inferior"] / 1e3, p["superior"] / 1e3, color="#e47b2f", alpha=0.18)
        eje.set_title(nombres_ccaa.get(codigo, codigo), fontsize=9)
        eje.xaxis.set_major_locator(mdates.YearLocator())
        eje.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        eje.tick_params(labelsize=7)
        eje.set_ylabel("GWh", fontsize=7)
    for eje in list(ejes.flat)[len(codigos):]:
        eje.axis("off")
    figura.suptitle(f"Demanda eléctrica por comunidad: últimos 3 años (verde) y previsión a 1 año (naranja, {nombre(demanda['resultado']['elegido'])}, intervalo 10-90 %)")
    figura.tight_layout()
    figuras["demanda"] = _guardar_figura(figura, "02_demanda_ccaa_1_anio.png")

    # 3. Error por horizonte (validación) de todos los modelos.
    figura, (a, b) = plt.subplots(1, 2, figsize=(13, 4.5))
    for eje, res, col, etiqueta in ((a, demanda["resultado"], "mape_pct", "MAPE (%)"), (b, precio["resultado"], "mae", "MAE (€/MWh)")):
        ph = res["por_horizonte"].query("particion == 'validacion'")
        for modelo, d in ph.groupby("modelo"):
            grueso = modelo == res["elegido"]
            eje.plot(d["horizonte_meses"], d[col], marker="o", ms=3, lw=2.4 if grueso else 1.1, color=COLORES_MODELO.get(modelo, "#555"), label=nombre(modelo))
        eje.set_xlabel("Meses vista")
        eje.set_ylabel(etiqueta)
        eje.set_xticks(range(1, 13))
        eje.legend(fontsize=7)
    a.set_title("Demanda: error por horizonte (validación)")
    b.set_title("Precio de la luz: error por horizonte (validación)")
    figura.tight_layout()
    figuras["horizonte"] = _guardar_figura(figura, "03_error_por_horizonte.png")

    # 4. Comparación de modelos: validación frente a test.
    figura, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8))
    for eje, res, col, etiqueta in ((a, demanda["resultado"], "mape_pct", "MAPE (%)"), (b, precio["resultado"], "mae", "MAE (€/MWh)")):
        tabla = res["metricas"].pivot(index="modelo", columns="particion", values=col).sort_values("validacion")
        x = np.arange(len(tabla))
        eje.bar(x - 0.2, tabla["validacion"], 0.4, color="#2c714e", label="validación (24 orígenes)")
        eje.bar(x + 0.2, tabla["test"], 0.4, color="#e47b2f", label="test (1 origen)")
        eje.set_xticks(x, [nombre(m) for m in tabla.index], rotation=35, ha="right", fontsize=7)
        eje.set_ylabel(etiqueta)
        eje.legend(fontsize=8)
    a.set_title("Demanda: error de cada modelo a 1 año")
    b.set_title("Precio de la luz: error de cada modelo a 1 año")
    figura.tight_layout()
    figuras["modelos"] = _guardar_figura(figura, "04_comparacion_modelos.png")

    # 5. Backtesting del precio: cada origen de validación y su previsión a 12 meses frente al real.
    figura, eje = plt.subplots(figsize=(12, 4.5))
    val = r["predicciones"].query("particion == 'validacion' and modelo == @r['elegido']")
    for _, d in val.groupby("origen"):
        eje.plot(d["mes"], d["prevision"], color="#e47b2f", alpha=0.35, lw=1)
    real = mensual["precio_eur_mwh"].dropna().loc[val["mes"].min() - pd.DateOffset(months=12) : val["mes"].max()]
    eje.plot(real.index, real.values, color="#2c714e", lw=2, label="precio real")
    eje.plot([], [], color="#e47b2f", alpha=0.6, label=f"previsiones a 1 año desde cada origen de validación ({nombre(r['elegido'])})")
    eje.set_title("Backtesting del precio de la luz: 24 previsiones a 1 año frente a lo que pasó")
    eje.set_xlabel("Mes")
    eje.set_ylabel("€/MWh")
    eje.legend(fontsize=8)
    figuras["backtesting_precio"] = _guardar_figura(figura, "05_backtesting_precio.png")
    return figuras


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

    RUTA_SALIDAS.mkdir(parents=True, exist_ok=True)
    (RUTA_SALIDAS / "previsiones_1_anio.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    for nombre_res, res in (("precio", res_p), ("demanda", res_d)):
        res["metricas"].to_csv(RUTA_SALIDAS / f"anual_metricas_{nombre_res}.csv", index=False)
        res["por_horizonte"].to_csv(RUTA_SALIDAS / f"anual_por_horizonte_{nombre_res}.csv", index=False)
    prev_p.to_csv(RUTA_SALIDAS / "anual_prevision_precio.csv", index=False)
    prev_d.to_csv(RUTA_SALIDAS / "anual_prevision_demanda.csv", index=False)

    precio = {"resultado": res_p, "prevision": prev_p, "error_test": error(res_p, "test"), "resumen": salida["precio"]}
    demanda = {"resultado": res_d, "prevision": prev_d, "resumen": salida["demanda"]}
    return {"precio": precio, "demanda": demanda, "figuras": _figuras_anual(precio, demanda, mensual, serie), "json": salida}


def main() -> None:
    """Punto de entrada de `python -m cpd.modelos`."""
    parser = argparse.ArgumentParser(description="EDA, modelos e informes del Proyecto 3")
    parser.add_argument("--sin-eda", action="store_true", help="no regenera las figuras ni el informe EDA")
    args = parser.parse_args()
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

    print("Informes")
    _escribir(informe.informe_anual(anual_res, fecha), RUTA_DOCS / "analisis" / "previsiones_1_anio.md")
    _escribir(informe.informe_metricas(demanda, prob, fecha, precio), RUTA_DOCS / "analisis" / "metricas.md")
    _escribir(informe.ficha_demanda(demanda, fecha), RUTA_DOCS / "modelos" / "demanda_ccaa.md")
    _escribir(informe.ficha_prob_cpd(prob, tabla, figura_roc, fecha), RUTA_DOCS / "modelos" / "prob_cpd.md")
    _escribir(informe.ficha_precio(precio, fecha), RUTA_DOCS / "modelos" / "precio_luz.md")
    print(f"Hecho en {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()
