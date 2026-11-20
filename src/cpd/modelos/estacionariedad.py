"""Estacionariedad de las series y efecto de las diferencias (técnicas de clase I51 e I52, C4 p.16-17), añadido el
18/11/2026.

Una serie es **estacionaria** si su media y su varianza no cambian con el tiempo. La clase pide comprobarlo con la
media y la varianza por año (C4 p.16) y usar **diferencias** cuando hay tendencia (p.17). Se aplica a la demanda
eléctrica mensual de cada comunidad en tres formas:

- **nivel** (MWh): tiene estacionalidad y tendencia;
- **logaritmo**: misma forma, escala proporcional;
- **diferencia estacional del logaritmo** (Δ₁₂ log y_t = log y_t − log y_(t−12)): crecimiento frente al mismo mes del
  año anterior. Es la forma que usan el Ridge (`f_desv_12m`), la `estacional_tendencia` y el modelo sobre
  diferencias (`anual._ar_diferencias`).

Además del criterio de clase se usa el test **ADF** (Dickey-Fuller aumentado, `statsmodels`; recomendación, no viene
de clase): p < 0,05 → se rechaza que la serie tenga raíz unitaria (es estacionaria).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

FORMAS: tuple[str, ...] = ("nivel", "log", "dif_estacional_log", "dif_doble_log")


def transformar(serie: pd.Series) -> dict[str, pd.Series]:
    """Las cuatro formas de una serie mensual positiva (índice de fechas): nivel, logaritmo, diferencia estacional del
    logaritmo (Δ₁₂) y doble diferencia (Δ₁ Δ₁₂: cambio del crecimiento interanual de un mes al siguiente)."""
    log = np.log(serie.astype(float))
    d12 = log.diff(12)
    return {"nivel": serie.astype(float), "log": log, "dif_estacional_log": d12.dropna(), "dif_doble_log": d12.diff(1).dropna()}


def media_varianza_por_anio(serie: pd.Series) -> pd.DataFrame:
    """Media y desviación típica por año natural de cada forma (criterio de la clase).

    Returns:
        forma, anio, media, desviacion.
    """
    filas = []
    for forma, s in transformar(serie).items():
        for anio, g in s.groupby(s.index.year):
            if len(g) >= 6:
                filas.append({"forma": forma, "anio": int(anio), "media": float(g.mean()), "desviacion": float(g.std(ddof=1))})
    return pd.DataFrame(filas)


def adf_pvalor(serie: pd.Series) -> float:
    """p-valor del test de Dickey-Fuller aumentado (con constante, retardos por AIC)."""
    from statsmodels.tsa.stattools import adfuller

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return float(adfuller(serie.dropna().to_numpy(dtype=float), autolag="AIC")[1])


def resumen_series(series: dict[str, pd.Series], alfa: float = 0.05) -> pd.DataFrame:
    """Para cada serie y forma: p-valor ADF, si es estacionaria (p < alfa), cuánto se mueve la media anual (rango de
    las medias por año / desviación típica de toda la forma; cerca de 0 = media estable) y cuánto cambia la varianza
    (desviación anual máxima / mínima; cerca de 1 = varianza estable).

    Returns:
        serie, forma, p_adf, estacionaria, deriva_media, ratio_varianza.
    """
    filas = []
    for nombre, s in series.items():
        mv = media_varianza_por_anio(s)
        for forma, x in transformar(s).items():
            m = mv[mv["forma"] == forma]
            escala = float(x.std(ddof=1))
            deriva = float((m["media"].max() - m["media"].min()) / escala) if len(m) > 1 and escala > 0 else np.nan
            ratio = float(m["desviacion"].max() / m["desviacion"].min()) if len(m) > 1 and m["desviacion"].min() > 0 else np.nan
            p = adf_pvalor(x)
            filas.append({"serie": nombre, "forma": forma, "p_adf": p, "estacionaria": bool(p < alfa), "deriva_media": deriva, "ratio_varianza": ratio})
    return pd.DataFrame(filas)


def series_demanda(serie: pd.DataFrame, hasta: str | None = None) -> dict[str, pd.Series]:
    """Series mensuales de demanda por comunidad sin meses imputados y, por defecto, hasta el último diciembre completo
    (para que la media y la varianza por año sean de años enteros)."""
    datos = serie[~serie["imputado"]] if "imputado" in serie.columns else serie
    fin = pd.Timestamp(hasta) if hasta else pd.Timestamp(int(datos["mes"].max().year) - 1, 12, 1)
    datos = datos[datos["mes"] <= fin]
    return {c: g.set_index("mes")["demanda_mwh"].sort_index().asfreq("MS").dropna() for c, g in datos.groupby("codigo_ccaa")}
