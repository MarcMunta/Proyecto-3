"""Atracción empresarial por provincia (variable E42), añadido el 18/11/2026.

Indicador con datos reales: **sociedades mercantiles constituidas** cada mes en la provincia (INE, Estadística de
Sociedades Mercantiles, tabla 6295, desde 2008). Se prevén los 12 meses siguientes con el mismo protocolo que el resto
de previsiones a 1 año (`cpd.modelos.anual`: 24 orígenes de validación, test un año que ningún modelo ve, combinación
de los 3 mejores) y con los mismos candidatos que la generación renovable en MWh (estacionales, anomalía persistente
y ETS de 5 años, también sobre el logaritmo).

Indicador para el mapa: sociedades creadas previstas en 12 meses **por cada 10.000 habitantes** (para comparar
provincias de distinto tamaño) y su cambio frente a los 12 meses anteriores. Es un indicador de dinamismo empresarial
(recomendación, no viene de clase): no mide qué empresas se instalan por el CPD.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from cpd.modelos import anual


def reales_sociedades(tabla: pd.DataFrame) -> pd.DataFrame:
    """`sociedades_provincia.csv` → formato de evaluación (`serie` = código de provincia, `mes`, `real`)."""
    return pd.DataFrame({"serie": tabla["codigo_provincia"].astype(str).str.zfill(2), "mes": pd.to_datetime(tabla["mes"]), "real": tabla["sociedades_creadas"].astype(float)})


def _base(reales: pd.DataFrame) -> dict[str, anual.Candidato]:
    return anual.candidatos_renovables(reales, maximo=np.inf, con_log=True)


def candidatos(reales: pd.DataFrame) -> dict[str, anual.Candidato]:
    """Candidatos de la generación renovable en MWh (conteos positivos, con estacionalidad y crecimiento proporcional)
    y su versión **por día hábil** (afinado del 18/11/2026): las sociedades se inscriben en días hábiles, así que se
    prevé el número por día hábil y se multiplica por los días hábiles del mes previsto (`cpd.features.calendario`).
    En validación todas las versiones por día hábil mejoraron a su candidato base."""
    return {**_base(reales), **anual.candidatos_por_dia_habil(_base, reales)}


def evaluar(reales: pd.DataFrame) -> dict[str, Any]:
    """Backtesting a 1 año (validación y test) y acierto del total de 12 meses."""
    res = anual.evaluar(candidatos(reales), reales, anual.definir_origenes(reales["mes"].max()), "mae")
    res["acierto_anual"] = anual.acierto_media_anual(res)
    return res


def indicador(reales: pd.DataFrame, prevision: pd.DataFrame, poblacion: pd.Series) -> pd.DataFrame:
    """Sociedades creadas en los últimos 12 meses y previstas en los 12 siguientes, por 10.000 habitantes.

    Args:
        prevision: salida de `anual.prevision_final` (`serie`, `mes`, `prevision`).
        poblacion: población del último año por código de provincia.

    Returns:
        codigo_provincia, ultimos_12m, prevision_12m, por_10000_hab, cambio_pct.
    """
    ultimos = reales.sort_values("mes").groupby("serie").tail(12).groupby("serie")["real"].sum()
    previstas = prevision.groupby("serie")["prevision"].sum()
    tabla = pd.DataFrame({"ultimos_12m": ultimos, "prevision_12m": previstas}).dropna()
    tabla["por_10000_hab"] = 1e4 * tabla["prevision_12m"] / poblacion.reindex(tabla.index)
    tabla["cambio_pct"] = 100 * (tabla["prevision_12m"] / tabla["ultimos_12m"] - 1)
    return tabla.rename_axis("codigo_provincia").reset_index()
