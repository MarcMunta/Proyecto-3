"""Tests de la previsión mensual baseline (forma, fechas, intervalo y tendencia)."""

import numpy as np
import pandas as pd
import pytest

from cpd.config import RUTA_DEMANDA_LIMPIA
from cpd.forecast import prever_mensual


def serie_sintetica(anios: int = 10) -> pd.Series:
    """Serie mensual con tendencia lineal creciente y estacionalidad anual."""
    fechas = pd.date_range("2015-01-01", periods=anios * 12, freq="MS")
    t = np.arange(len(fechas))
    estacional = 1 + 0.1 * np.sin(2 * np.pi * fechas.month.values / 12)
    valores = (1000 + 2 * t) * estacional
    return pd.Series(valores, index=fechas)


def test_longitud_y_columnas_por_defecto():
    previsiones = prever_mensual(serie_sintetica(), horizonte_meses=120)
    assert len(previsiones) == 120
    assert list(previsiones.columns) == ["fecha", "prevision", "inferior", "superior"]


def test_fechas_empiezan_tras_el_ultimo_mes_historico():
    serie = serie_sintetica()
    previsiones = prever_mensual(serie, horizonte_meses=12)
    assert previsiones["fecha"].iloc[0] == pd.Timestamp("2025-01-01")
    assert previsiones["fecha"].iloc[-1] == pd.Timestamp("2025-12-01")


def test_intervalo_contiene_la_prevision():
    previsiones = prever_mensual(serie_sintetica(), horizonte_meses=120)
    assert (previsiones["inferior"] <= previsiones["prevision"]).all()
    assert (previsiones["prevision"] <= previsiones["superior"]).all()


def test_el_intervalo_crece_con_el_horizonte():
    previsiones = prever_mensual(serie_sintetica(), horizonte_meses=120)
    ancho = previsiones["superior"] - previsiones["inferior"]
    assert ancho.iloc[-1] > ancho.iloc[0]


def test_sigue_la_tendencia_creciente():
    previsiones = prever_mensual(serie_sintetica(), horizonte_meses=120)
    media_primer_anio = previsiones["prevision"].iloc[:12].mean()
    media_ultimo_anio = previsiones["prevision"].iloc[-12:].mean()
    assert media_ultimo_anio > media_primer_anio
    # La serie sintética crece 24 unidades al año. Entre la media del primer año previsto
    # y la del último hay 9 años de diferencia => 9 × 24 = 216 unidades.
    assert media_ultimo_anio - media_primer_anio == pytest.approx(24 * 9, rel=0.02)


def test_estacionalidad_se_conserva():
    previsiones = prever_mensual(serie_sintetica(), horizonte_meses=12)
    # Mes con seno máximo (marzo, mes 3) frente a mes con seno mínimo (septiembre, mes 9)
    assert previsiones.loc[2, "prevision"] > previsiones.loc[8, "prevision"]


def test_historia_insuficiente_falla():
    corta = serie_sintetica(anios=1)
    with pytest.raises(ValueError):
        prever_mensual(corta)


def test_horizonte_no_positivo_falla():
    with pytest.raises(ValueError):
        prever_mensual(serie_sintetica(), horizonte_meses=0)


def test_serie_real_si_existe_el_csv():
    if not RUTA_DEMANDA_LIMPIA.exists():
        pytest.skip("No existe data/clean/ree_demanda_mensual.csv (ejecutar el ETL de REData)")
    datos = pd.read_csv(RUTA_DEMANDA_LIMPIA, parse_dates=["fecha"])
    serie = pd.Series(datos["demanda_mwh"].values, index=pd.DatetimeIndex(datos["fecha"]))
    previsiones = prever_mensual(serie, horizonte_meses=120)
    assert len(previsiones) == 120
    assert previsiones["prevision"].gt(0).all()
