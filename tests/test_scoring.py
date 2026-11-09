"""Tests de filtros eliminatorios, sub-scores, score global y ranking."""

import numpy as np
import pandas as pd
import pytest

from cpd.config import RUTA_DEMO, cargar_settings
from cpd.scoring import (
    ESTADO_CONDICIONES,
    ESTADO_NO_VIABLE,
    ESTADO_VIABLE,
    INDICADORES_POR_BLOQUE,
    aplicar_filtros,
    evaluar,
    normalizar_min_max,
    pesos_normalizados,
    preparar_escenario,
)
from cpd.simulator import CPDParams


@pytest.fixture(scope="module")
def settings():
    return cargar_settings()


@pytest.fixture(scope="module")
def demo():
    return pd.read_csv(RUTA_DEMO, dtype={"codigo_ine": str})


def fila_buena(**cambios):
    """Municipio sin ningún problema por defecto; se pueden sobrescribir campos."""
    base = {
        "zona_inundable": 0,
        "red_natura": 0,
        "dist_subestacion_km": 5.0,
        "capacidad_acceso_mw": 200.0,
        "dist_ixp_km": 50.0,
        "estres_hidrico_idx": 0.3,
        "peligrosidad_sismica_g": 0.05,
        "temp_max_hist_c": 38.0,
        "suelo_industrial_ha": 50.0,
        "temp_media_c": 14.0,
    }
    base.update(cambios)
    return base


def test_repercusion_energia_suma_a_ingresos_y_mejora_van(settings):
    """Los ingresos incluyen la energía repercutida; sin repercusión el VAN es menor."""
    from copy import deepcopy

    from cpd.scoring import simular_municipio

    fila = fila_buena(precio_suelo_eur_m2=40.0, consumo_electrico_municipal_mwh=500_000.0)
    params = CPDParams()
    con = simular_municipio(fila, params, settings)
    pct = settings["precios"]["repercusion_energia_pct"]
    assert con["ingresos_energia_eur"] == pytest.approx(con["coste_energia_eur"] * pct)
    assert con["ingresos_anuales_eur"] == pytest.approx(con["ingresos_alquiler_eur"] + con["ingresos_energia_eur"])

    sin_settings = deepcopy(settings)
    sin_settings["precios"]["repercusion_energia_pct"] = 0.0
    sin = simular_municipio(fila, params, sin_settings)
    assert sin["ingresos_energia_eur"] == 0
    assert sin["van_eur"] < con["van_eur"]


def test_pesos_de_settings_suman_uno(settings):
    assert sum(settings["pesos"].values()) == pytest.approx(1.0)


def test_pesos_normalizados_renormalizan(settings):
    pesos = pesos_normalizados({"energia": 2, "costes": 2}, settings)
    assert sum(pesos.values()) == pytest.approx(1.0)
    assert pesos["energia"] == pytest.approx(0.5)
    assert pesos["impacto"] == 0.0


def test_pesos_negativos_o_nulos_fallan(settings):
    with pytest.raises(ValueError):
        pesos_normalizados({"energia": -1}, settings)
    with pytest.raises(ValueError):
        pesos_normalizados({"energia": 0}, settings)


def test_municipio_sin_problemas_es_viable(settings):
    estado, motivos = aplicar_filtros(fila_buena(), CPDParams(), settings)
    assert estado == ESTADO_VIABLE
    assert motivos and "Cumple" in motivos[0]


def test_zona_inundable_es_no_viable(settings):
    estado, motivos = aplicar_filtros(fila_buena(zona_inundable=1), CPDParams(), settings)
    assert estado == ESTADO_NO_VIABLE
    assert any("inundable" in m.lower() for m in motivos)


def test_red_natura_es_no_viable(settings):
    estado, _ = aplicar_filtros(fila_buena(red_natura=1), CPDParams(), settings)
    assert estado == ESTADO_NO_VIABLE


def test_evaporativa_con_estres_alto_es_no_viable(settings):
    params = CPDParams(tipo_refrigeracion="evaporativa")
    estado, _ = aplicar_filtros(fila_buena(estres_hidrico_idx=0.8), params, settings)
    assert estado == ESTADO_NO_VIABLE


def test_aire_con_estres_alto_es_condicionado(settings):
    params = CPDParams(tipo_refrigeracion="aire")
    estado, motivos = aplicar_filtros(fila_buena(estres_hidrico_idx=0.8), params, settings)
    assert estado == ESTADO_CONDICIONES
    assert any("hídrico" in m for m in motivos)


def test_capacidad_insuficiente_es_no_viable(settings):
    # 50 MW × PUE 1.3 = 65 MW necesarios; con 60 MW de acceso no basta
    estado, _ = aplicar_filtros(fila_buena(capacidad_acceso_mw=60.0), CPDParams(pue=1.3, usar_pue_estimado=False), settings)
    assert estado == ESTADO_NO_VIABLE


def test_distancia_subestacion_para_cpd_grande(settings):
    lejos = fila_buena(dist_subestacion_km=30.0)
    estado, _ = aplicar_filtros(lejos, CPDParams(potencia_ti_mw=50), settings)
    assert estado == ESTADO_NO_VIABLE
    estado_pequeno, _ = aplicar_filtros(lejos, CPDParams(potencia_ti_mw=10), settings)
    assert estado_pequeno == ESTADO_VIABLE


def test_sismicidad_alta_es_condicionado(settings):
    estado, _ = aplicar_filtros(fila_buena(peligrosidad_sismica_g=0.2), CPDParams(), settings)
    assert estado == ESTADO_CONDICIONES


def test_datos_ausentes_no_provocan_ko(settings):
    fila = {"zona_inundable": np.nan}
    estado, motivos = aplicar_filtros(fila, CPDParams(), settings)
    assert estado == ESTADO_VIABLE
    assert any("datos ausentes" in m for m in motivos)


def test_normalizar_min_max_respeta_direccion():
    serie = pd.Series([1.0, 2.0, 3.0])
    assert normalizar_min_max(serie, +1).tolist() == pytest.approx([0.0, 50.0, 100.0])
    assert normalizar_min_max(serie, -1).tolist() == pytest.approx([100.0, 50.0, 0.0])


def test_normalizar_valores_iguales_da_100():
    assert normalizar_min_max(pd.Series([5.0, 5.0]), -1).tolist() == [100.0, 100.0]


def test_evaluar_demo_limites_y_orden(demo, settings):
    out = evaluar(demo, CPDParams(), settings)
    assert len(out) == len(demo)
    assert out["score_global"].between(0, 100).all()
    for columna in INDICADORES_POR_BLOQUE:
        assert out[f"sub_{columna}"].dropna().between(0, 100).all()
    # Todos los estados presentes en el demo y ordenados: viables primero, no viables al final
    assert set(out["estado"]) == {ESTADO_VIABLE, ESTADO_CONDICIONES, ESTADO_NO_VIABLE}
    orden = out["estado"].map({ESTADO_VIABLE: 0, ESTADO_CONDICIONES: 1, ESTADO_NO_VIABLE: 2})
    assert orden.is_monotonic_increasing
    assert out["ranking"].tolist() == list(range(1, len(out) + 1))


def test_evaluar_no_modifica_el_dataframe_original(demo, settings):
    copia = demo.copy()
    evaluar(demo, CPDParams(), settings)
    pd.testing.assert_frame_equal(demo, copia)


def test_evaluar_tolera_columnas_que_faltan(settings):
    df = pd.DataFrame([{"municipio": "X", "codigo_ine": "00001", "temp_media_c": 14.0}])
    out = evaluar(df, CPDParams(), settings)
    assert len(out) == 1
    assert 0 <= out["score_global"].iloc[0] <= 100 or pd.isna(out["score_global"].iloc[0])


def test_escenario_sube_precio_y_estres(demo, settings):
    df_esc, params_esc, settings_esc = preparar_escenario(
        demo, CPDParams(), settings, pct_precio_electricidad=0.2, incremento_estres=0.1,
        tipo_refrigeracion="inmersion",
    )
    assert settings_esc["precios"]["precio_electricidad_eur_mwh"] == pytest.approx(
        settings["precios"]["precio_electricidad_eur_mwh"] * 1.2
    )
    assert params_esc.tipo_refrigeracion == "inmersion"
    assert (df_esc["estres_hidrico_idx"] >= demo["estres_hidrico_idx"]).all()
    # El original no cambia
    assert settings["precios"]["precio_electricidad_eur_mwh"] == 75
