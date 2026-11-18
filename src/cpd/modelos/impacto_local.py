"""Impacto previsto del CPD sobre los recursos locales (pregunta P2; variables E43, E44 y E14), añadido el 18/11/2026.

El enunciado pregunta «¿qué impacto tendrá el CPD sobre los recursos locales?». No hay consumo eléctrico ni de agua
abierto por municipio o provincia (E8, E14), así que el impacto se mide frente a lo que sí se publica por comunidad:

- **Electricidad**: consumo previsto del CPD a 1 año (temperatura prevista → PUE → consumo, `cpd.modelos.operacion`)
  frente a la **demanda prevista de su comunidad** en los mismos 12 meses (modelo de demanda, 95,6 % en test).
- **Red**: potencia máxima del CPD (potencia TI × PUE) frente a la **capacidad de acceso disponible** para nueva
  demanda en su comunidad (Red Eléctrica). Por encima del 100 % el CPD no cabe en la red libre de hoy.
- **Agua**: agua anual del CPD (WUE del simulador) frente al **agua registrada y distribuida** por la red pública de su
  comunidad (INE, «Estadística sobre el suministro y saneamiento del agua», último año publicado).
- **Habitantes equivalentes**: consumo del CPD dividido por el consumo por habitante de su comunidad (electricidad:
  demanda total / población; agua: agua distribuida / población). Incluye todos los usos (hogares, industria,
  servicios), así que es una comparación de escala, no un número de hogares.

Validación de punta a punta del impacto eléctrico: en los orígenes comunes de los modelos de temperatura y demanda se
calcula el % previsto (consumo con la temperatura prevista / demanda prevista) y el real (con la temperatura y la
demanda reales) y se mide el acierto (100 − WAPE).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from cpd import simulator as sim
from cpd.modelos.anual import HORIZONTE
from cpd.modelos.metricas import acierto_pct
from cpd.modelos.operacion import _medias_anuales, operacion_anual

CODIGO_CEUTA_MELILLA: str = "18-19"


def _ccaa_agua(codigo_ccaa: str) -> str:
    """El INE publica Ceuta y Melilla juntas."""
    return CODIGO_CEUTA_MELILLA if codigo_ccaa in ("18", "19") else codigo_ccaa


def potencia_pico_mw(params: sim.CPDParams, pue: float) -> float:
    """Potencia máxima que pide el CPD a la red (MW): potencia TI × PUE (con toda la TI encendida)."""
    return params.potencia_ti_mw * pue


def impacto_provincias(
    operacion: dict[str, dict[str, Any]],
    demanda_ccaa: dict[str, dict[str, Any]],
    capacidad: pd.DataFrame,
    agua: pd.DataFrame,
    poblacion_ccaa: pd.Series,
    ccaa_de: dict[str, str],
    params: sim.CPDParams,
) -> pd.DataFrame:
    """Impacto previsto del CPD de referencia por provincia (una fila por provincia).

    Args:
        operacion: `previsiones_1_anio.json["operacion"]["provincias"]` (pue_previsto, consumo_previsto_mwh, agua_m3).
        demanda_ccaa: `previsiones_1_anio.json["demanda"]["ccaa"]` (ultimos_12m, prevision_12m en MWh).
        capacidad: `capacidad_ccaa.csv` (codigo_ccaa, capacidad_demanda_rdt_disponible_mw).
        agua: `agua_ccaa.csv` (codigo_ccaa, anio, agua_registrada_miles_m3); se usa el último año de cada comunidad.
        poblacion_ccaa: población del último año por código de comunidad (con «18-19» para Ceuta y Melilla juntas).
        ccaa_de: provincia → comunidad.

    Returns:
        codigo_provincia, codigo_ccaa, consumo_cpd_mwh, demanda_ccaa_prevista_mwh, pct_demanda_ccaa,
        habitantes_eq_electricidad, potencia_pico_mw, capacidad_disponible_mw, pct_capacidad_disponible,
        sin_capacidad_libre, agua_cpd_m3,
        agua_ccaa_m3, anio_agua, pct_agua_ccaa, habitantes_eq_agua.
    """
    cap = capacidad.assign(codigo_ccaa=capacidad["codigo_ccaa"].astype(str).str.zfill(2)).set_index("codigo_ccaa")["capacidad_demanda_rdt_disponible_mw"]
    ultimo_agua = agua.sort_values("anio").groupby("codigo_ccaa").last()
    filas = []
    for provincia, o in sorted(operacion.items()):
        ccaa = ccaa_de.get(provincia)
        if ccaa is None:
            continue
        consumo, pue, agua_cpd = o.get("consumo_previsto_mwh"), o.get("pue_previsto"), o.get("agua_m3")
        d = demanda_ccaa.get(ccaa, {})
        demanda, demanda_12m = d.get("prevision_12m"), d.get("ultimos_12m")
        pob = poblacion_ccaa.get(ccaa)
        clave_agua = _ccaa_agua(ccaa)
        agua_ccaa = float(ultimo_agua.loc[clave_agua, "agua_registrada_miles_m3"]) * 1e3 if clave_agua in ultimo_agua.index else np.nan
        pob_agua = poblacion_ccaa.get(clave_agua, pob) if clave_agua == CODIGO_CEUTA_MELILLA else pob
        pico = potencia_pico_mw(params, pue) if pue is not None else np.nan
        disponible = float(cap.get(ccaa, np.nan))
        filas.append(
            {
                "codigo_provincia": provincia, "codigo_ccaa": ccaa,
                "consumo_cpd_mwh": consumo, "demanda_ccaa_prevista_mwh": demanda,
                "pct_demanda_ccaa": 100 * consumo / demanda if consumo and demanda else np.nan,
                "habitantes_eq_electricidad": consumo / (demanda_12m / pob) if consumo and demanda_12m and pob else np.nan,
                "potencia_pico_mw": pico, "capacidad_disponible_mw": disponible,
                "pct_capacidad_disponible": 100 * pico / disponible if disponible and disponible > 0 else np.nan,
                # 0 MW libres: el CPD no cabe hoy en la red de acceso de su comunidad (NaN = sin dato de Red Eléctrica).
                "sin_capacidad_libre": bool(disponible == 0),
                "agua_cpd_m3": agua_cpd, "agua_ccaa_m3": agua_ccaa,
                "anio_agua": int(ultimo_agua.loc[clave_agua, "anio"]) if clave_agua in ultimo_agua.index else None,
                "pct_agua_ccaa": 100 * agua_cpd / agua_ccaa if agua_cpd and agua_ccaa > 0 else np.nan,
                "habitantes_eq_agua": agua_cpd / (agua_ccaa / pob_agua) if agua_cpd and agua_ccaa > 0 and pob_agua else np.nan,
            }
        )
    return pd.DataFrame(filas)


def _demanda_anual(res_demanda: dict[str, Any], particion: str) -> pd.DataFrame:
    """Suma de los 12 meses previstos y reales de la demanda (modelo elegido) por (comunidad, origen)."""
    pred = res_demanda["predicciones"]
    pred = pred[(pred["modelo"] == res_demanda["elegido"]) & (pred["particion"] == particion)]
    sumas = pred.groupby(["serie", "origen"]).agg(dem_prev=("prevision", "sum"), dem_real=("real", "sum"), n=("real", "size"))
    return sumas[sumas["n"] == HORIZONTE].drop(columns="n").reset_index().rename(columns={"serie": "ccaa"})


def validar_impacto_electrico(
    res_temperatura: dict[str, Any], res_demanda: dict[str, Any], ccaa_de: dict[str, str], params: sim.CPDParams, particion: str = "validacion"
) -> dict[str, Any]:
    """Acierto (100 − WAPE) del % del consumo del CPD sobre la demanda de su comunidad a 1 año, de punta a punta.

    Returns:
        `acierto` (%, o None si no hay orígenes comunes), `origenes`, `provincias` y `detalle`.
    """
    temp = _medias_anuales(res_temperatura, particion).rename(columns={"serie": "provincia", "prevision": "temp_prev", "real": "temp_real"})
    temp["ccaa"] = temp["provincia"].map(ccaa_de)
    datos = temp.merge(_demanda_anual(res_demanda, particion), on=["ccaa", "origen"], how="inner")
    if datos.empty:
        return {"acierto": None, "origenes": 0, "provincias": 0, "detalle": datos}
    consumo = lambda t: operacion_anual(float(t), 0.0, params, 0.0)["consumo_mwh"]  # noqa: E731
    datos["pct_prev"] = [100 * consumo(t) / d for t, d in zip(datos["temp_prev"], datos["dem_prev"])]
    datos["pct_real"] = [100 * consumo(t) / d for t, d in zip(datos["temp_real"], datos["dem_real"])]
    return {
        "acierto": acierto_pct(datos["pct_real"], datos["pct_prev"]), "origenes": int(datos["origen"].nunique()),
        "provincias": int(datos["provincia"].nunique()), "detalle": datos,
    }
