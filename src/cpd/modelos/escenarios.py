"""Escenarios de demanda eléctrica a 10 años con los nuevos grandes consumos (pregunta P5), añadido el 18/11/2026.

La previsión a 10 años (`cpd.modelos.largo_plazo`, 97,3 % en backtesting) es **tendencial**: no sabe que llegan centros
de datos, hidrógeno o industria electrificada. Red Eléctrica publica cuánta **capacidad de acceso a la red de
transporte** ya ha **otorgado** a nuevos consumos y cuánta está **en trámite** (`capacidad_ccaa.csv`). Aquí se suma a la
previsión tendencial la energía de esa capacidad en varios escenarios.

Supuestos (`config/settings.yaml → escenarios_demanda`, **a calibrar**; recomendación, no viene de clase):
- **Energía de la capacidad:** MW × 8.760 h × factor de utilización (por defecto el factor de carga del CPD de
  referencia del simulador). La capacidad de acceso es un máximo: un consumo real nunca la usa entera todo el año.
- **Realización:** qué parte de lo otorgado llega a consumir antes del año 10 (no hay dato abierto: REE solo publica el
  último mes, sin histórico). Se dan varios escenarios en lugar de una cifra.
- **Rampa:** la capacidad entra de forma lineal a lo largo de los 10 años.

No es una previsión con acierto medible: es un escenario. La capacidad incluye todos los grandes consumos, no solo CPD.
"""

from __future__ import annotations

import pandas as pd

HORAS_ANIO: float = 8760.0


def energia_twh(potencia_mw: float, factor_utilizacion: float) -> float:
    """Energía anual (TWh) de una potencia (MW) usada en promedio a una fracción `factor_utilizacion` (0-1)."""
    return potencia_mw * HORAS_ANIO * factor_utilizacion / 1e6


def escenarios_nacionales(
    prevision: pd.DataFrame, otorgada_mw: float, pendiente_mw: float, factor_utilizacion: float, realizaciones: list[float]
) -> pd.DataFrame:
    """Demanda nacional por año en cada escenario (TWh).

    Args:
        prevision: previsión tendencial (`anio`, `horizonte_anios`, `prevision_twh`).
        otorgada_mw, pendiente_mw: capacidad de acceso de demanda otorgada y en trámite en España (MW).
        realizaciones: fracciones de lo otorgado que llegan a consumir al final de los 10 años.

    Returns:
        `anio`, `escenario`, `demanda_twh`, `extra_twh`. Escenarios: «tendencial», «otorgada_<p>» para cada
        realización y «techo» (otorgada + en trámite enteras).
    """
    horizonte = int(prevision["horizonte_anios"].max())
    filas = []
    casos = [("tendencial", 0.0)] + [(f"otorgada_{round(100 * r)}", r * otorgada_mw) for r in realizaciones] + [("techo", otorgada_mw + pendiente_mw)]
    for nombre, mw in casos:
        for f in prevision.itertuples():
            extra = energia_twh(mw, factor_utilizacion) * f.horizonte_anios / horizonte  # rampa lineal
            filas.append({"anio": int(f.anio), "escenario": nombre, "demanda_twh": float(f.prevision_twh) + extra, "extra_twh": extra})
    return pd.DataFrame(filas)


def por_ccaa(capacidad: pd.DataFrame, demanda_mwh: pd.Series, factor_utilizacion: float) -> pd.DataFrame:
    """Peso de lo otorgado y lo pedido en cada comunidad frente a su demanda actual.

    Args:
        capacidad: `capacidad_ccaa.csv` (codigo_ccaa, ccaa, capacidad_demanda_rdt_otorgada_mw, …_pendiente_mw).
        demanda_mwh: demanda de los últimos 12 meses por código de comunidad (MWh).

    Returns:
        codigo_ccaa, ccaa, otorgada_mw, pendiente_mw, demanda_twh, otorgada_twh, pendiente_twh, pct_otorgada, pct_pendiente.
    """
    t = capacidad.assign(codigo_ccaa=capacidad["codigo_ccaa"].astype(str).str.zfill(2)).rename(
        columns={"capacidad_demanda_rdt_otorgada_mw": "otorgada_mw", "capacidad_demanda_rdt_pendiente_mw": "pendiente_mw"}
    )[["codigo_ccaa", "ccaa", "otorgada_mw", "pendiente_mw"]]
    t["demanda_twh"] = t["codigo_ccaa"].map(demanda_mwh) / 1e6
    t["otorgada_twh"] = [energia_twh(v, factor_utilizacion) for v in t["otorgada_mw"].fillna(0)]
    t["pendiente_twh"] = [energia_twh(v, factor_utilizacion) for v in t["pendiente_mw"].fillna(0)]
    t["pct_otorgada"] = 100 * t["otorgada_twh"] / t["demanda_twh"]
    t["pct_pendiente"] = 100 * t["pendiente_twh"] / t["demanda_twh"]
    return t.sort_values("pct_otorgada", ascending=False).reset_index(drop=True)
