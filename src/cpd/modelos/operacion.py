"""Operación prevista del CPD de referencia a 1 año por provincia (objetivo A3: sostenibilidad operativa).

Encadena modelos ya validados con las fórmulas del simulador (`cpd.simulator`):
- temperatura media prevista de los 12 meses (provincia) → PUE (`pue_estimado`) → consumo anual (MWh);
- % renovable medio previsto de los 12 meses (comunidad) → emisiones (t CO2) si el CPD se abastece con el mix de
  generación de su comunidad: consumo × (1 − % renovable) × factor de emisión del MWh no renovable.

Limitación: el mercado eléctrico es único y una comunidad que exporta no «vende» su propio mix; usar el mix de
generación de la comunidad es una aproximación (recomendación, no viene de clase).

Validación de punta a punta: en los orígenes de validación que comparten los dos modelos se calcula el consumo y las
emisiones del año siguiente con lo previsto y con lo real, y se mide el acierto (100 − WAPE) de esos totales.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from cpd import simulator as sim
from cpd.modelos.anual import HORIZONTE
from cpd.modelos.metricas import acierto_pct


def operacion_anual(temp_media_c: float, pct_renovable: float, params: sim.CPDParams, factor_emision_t_mwh: float) -> dict[str, float]:
    """PUE, consumo (MWh/año), emisiones (t CO2/año) y agua (m³/año) del CPD con una temperatura media anual (°C) y un
    % renovable (0-100) del mix con el que se abastece."""
    pue = sim.pue_estimado(temp_media_c, params.tipo_refrigeracion)
    consumo = sim.consumo_anual_mwh(params.potencia_ti_mw, params.factor_carga, pue)
    return {
        "pue": pue,
        "consumo_mwh": consumo,
        "emisiones_t": sim.co2_t(consumo, pct_renovable / 100, factor_emision_t_mwh),
        "agua_m3": sim.agua_m3_anual(params.potencia_ti_mw, params.factor_carga, params.wue_l_kwh),
    }


def _medias_anuales(resultado: dict[str, Any], particion: str) -> pd.DataFrame:
    """Media de los 12 meses previstos y reales del modelo elegido, por (serie, origen)."""
    pred = resultado["predicciones"]
    pred = pred[(pred["modelo"] == resultado["elegido"]) & (pred["particion"] == particion)]
    medias = pred.groupby(["serie", "origen"]).agg(prevision=("prevision", "mean"), real=("real", "mean"), n=("real", "size"))
    return medias[medias["n"] == HORIZONTE].drop(columns="n").reset_index()


def backtesting(
    res_temperatura: dict[str, Any],
    res_renovables: dict[str, Any],
    ccaa_de: dict[str, str],
    params: sim.CPDParams,
    factor_emision_t_mwh: float,
) -> dict[str, Any]:
    """Consumo y emisiones del año siguiente con lo previsto y con lo real, en los orígenes de validación comunes.

    Returns:
        `detalle` (provincia × origen), `acierto_consumo`, `acierto_emisiones` (100 − WAPE, %), `origenes` (nº) y
        `provincias` (nº).
    """
    temp = _medias_anuales(res_temperatura, "validacion").rename(columns={"serie": "provincia", "prevision": "temp_prev", "real": "temp_real"})
    renov = _medias_anuales(res_renovables, "validacion").rename(columns={"serie": "ccaa", "prevision": "pct_prev", "real": "pct_real"})
    temp["ccaa"] = temp["provincia"].map(ccaa_de)
    datos = temp.merge(renov, on=["ccaa", "origen"], how="inner")
    filas = []
    for f in datos.itertuples():
        prevista = operacion_anual(f.temp_prev, f.pct_prev, params, factor_emision_t_mwh)
        real = operacion_anual(f.temp_real, f.pct_real, params, factor_emision_t_mwh)
        filas.append(
            {
                "provincia": f.provincia, "origen": f.origen,
                "consumo_prev_mwh": prevista["consumo_mwh"], "consumo_real_mwh": real["consumo_mwh"],
                "emisiones_prev_t": prevista["emisiones_t"], "emisiones_real_t": real["emisiones_t"],
            }
        )
    detalle = pd.DataFrame(filas)
    return {
        "detalle": detalle,
        "acierto_consumo": acierto_pct(detalle["consumo_real_mwh"], detalle["consumo_prev_mwh"]),
        "acierto_emisiones": acierto_pct(detalle["emisiones_real_t"], detalle["emisiones_prev_t"]),
        "origenes": int(detalle["origen"].nunique()),
        "provincias": int(detalle["provincia"].nunique()),
    }


def prevision(
    temperatura: dict[str, dict[str, Any]],
    renovables: dict[str, dict[str, Any]],
    ccaa_de: dict[str, str],
    params: sim.CPDParams,
    factor_emision_t_mwh: float,
) -> pd.DataFrame:
    """Operación del CPD el último año (real) y los 12 meses siguientes (previsto) por provincia.

    Args:
        temperatura: `previsiones_1_anio.json["temperatura"]["provincias"]` (media_12m_actual, media_prevista en °C).
        renovables: `previsiones_1_anio.json["renovables"]["ccaa"]` (media_12m_actual, media_prevista en %).
        ccaa_de: provincia → comunidad.

    Returns:
        Una fila por provincia con PUE, consumo, emisiones y agua del último año y previstos. Las comunidades sin
        serie de % renovable (Ceuta: siempre 0 %) se calculan con 0 % renovable, que es su dato real.
    """
    filas = []
    for provincia, t in temperatura.items():
        r = renovables.get(ccaa_de.get(provincia, ""), {"media_12m_actual": 0.0, "media_prevista": 0.0})
        actual = operacion_anual(t["media_12m_actual"], r["media_12m_actual"], params, factor_emision_t_mwh)
        prevista = operacion_anual(t["media_prevista"], r["media_prevista"], params, factor_emision_t_mwh)
        filas.append(
            {
                "codigo_provincia": provincia,
                **{f"{k}_actual": v for k, v in actual.items()},
                **{f"{k}_previsto": v for k, v in prevista.items()},
            }
        )
    tabla = pd.DataFrame(filas)
    tabla["cambio_emisiones_pct"] = np.where(
        tabla["emisiones_t_actual"] > 0, 100 * (tabla["emisiones_t_previsto"] / tabla["emisiones_t_actual"] - 1), np.nan
    )
    return tabla
