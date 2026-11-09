"""Tests de las fórmulas del simulador con valores calculados a mano."""

import math

import pytest

from cpd import simulator as sim
from cpd.simulator import CPDParams


def test_consumo_anual_ejemplo_50mw():
    # 50 MW × 0.8 × 1.3 × 8760 = 455 520 MWh
    assert sim.consumo_anual_mwh(50, 0.8, 1.3) == pytest.approx(455_520)


def test_potencia_total():
    assert sim.potencia_total_mw(50, 1.3) == pytest.approx(65.0)


def test_agua_l_dia_y_m3_anual():
    # 50 000 kW × 0.8 × 24 h × 0.5 L/kWh = 480 000 L/día
    assert sim.agua_l_dia(50, 0.8, 0.5) == pytest.approx(480_000)
    # 480 000 × 365 / 1000 = 175 200 m³/año
    assert sim.agua_m3_anual(50, 0.8, 0.5) == pytest.approx(175_200)


def test_coste_energia_descuenta_autoproduccion():
    # (455 520 − 100 000) × 75 €/MWh = 26 664 000 €
    assert sim.coste_energia_eur(455_520, 100_000, 75) == pytest.approx(26_664_000)


def test_coste_energia_no_negativo_si_autoproduccion_supera_consumo():
    assert sim.coste_energia_eur(1000, 5000, 75) == 0.0


def test_coste_agua():
    assert sim.coste_agua_eur(175_200, 2.0) == pytest.approx(350_400)


def test_opex_total_ejemplo():
    # energía 34 164 000 + agua 350 400 + personal 2 700 000
    # + mantenimiento 8 000 000 + impuestos 2 000 000 = 47 214 400
    consumo = sim.consumo_anual_mwh(50, 0.8, 1.3)
    coste_e = sim.coste_energia_eur(consumo, 0, 75)
    coste_a = sim.coste_agua_eur(sim.agua_m3_anual(50, 0.8, 0.5), 2.0)
    total = sim.opex_eur(coste_e, coste_a, 60, 45_000, 400e6, 0.02, 0.005)
    assert total == pytest.approx(47_214_400)


def test_desglose_opex_suma_componentes():
    d = sim.desglose_opex(1_000, 200, 2, 50_000, 10_000, 0.1, 0.05)
    assert d["personal"] == 100_000
    assert d["mantenimiento"] == 1_000
    assert d["impuestos_locales"] == 500
    assert d["total"] == pytest.approx(1_000 + 200 + 100_000 + 1_000 + 500)


def test_co2_con_renovable_parcial():
    # 455 520 × (1 − 0.8) × 0.10 = 9 110.4 t
    assert sim.co2_t(455_520, 0.8, 0.10) == pytest.approx(9_110.4)


def test_impacto_local_pct_y_division_por_cero():
    assert sim.impacto_local_pct(455_520, 9_110_400) == pytest.approx(5.0)
    assert sim.impacto_local_pct(455_520, 0) is None
    assert sim.impacto_local_pct(455_520, None) is None
    assert sim.impacto_local_pct(455_520, float("nan")) is None


def test_latencia_rtt():
    # 100 km × 0.01 × 1.5 = 1.5 ms
    assert sim.latencia_rtt_ms(100, 1.5) == pytest.approx(1.5)


def test_horas_free_cooling_ignora_nan():
    assert sim.horas_free_cooling([10, 20, 17.9, float("nan"), 25], umbral_c=18) == 2


def test_pue_estimado_heuristica_orden():
    assert sim.pue_estimado(15, "aire") == pytest.approx(1.45)
    assert sim.pue_estimado(5, "aire") < sim.pue_estimado(25, "aire")
    assert sim.pue_estimado(15, "inmersion") < sim.pue_estimado(15, "aire")
    with pytest.raises(ValueError):
        sim.pue_estimado(15, "magia")


def test_ingresos_anuales():
    # 50 × 1000 × 120 × 12 × 0.85 = 61 200 000 €
    assert sim.ingresos_anuales_eur(50, 120, 0.85) == pytest.approx(61_200_000)


def test_van_sin_tasa_es_suma_menos_inversion():
    assert sim.van([100, 100], 0.0, 150) == pytest.approx(50)


def test_van_con_descuento():
    # −150 + 100/1.1 + 100/1.21 = 23.554...
    expected = -150 + 100 / 1.1 + 100 / 1.21
    assert sim.van([100, 100], 0.10, 150) == pytest.approx(expected)


def test_roi():
    # (300 − 200) / 200 = 0.5
    assert sim.roi([100, 100, 100], 200) == pytest.approx(0.5)
    assert sim.roi([100], 0) is None


def test_payback_exacto_y_no_recuperado():
    assert sim.payback_anos([100, 100, 100], 200) == pytest.approx(2.0)
    # acumulado: −150, −100, 0 => recupera en el año 3
    assert sim.payback_anos([50, 50, 100], 200) == pytest.approx(3.0)
    assert sim.payback_anos([10, 10], 200) is None


def test_cpd_params_valores_por_defecto():
    p = CPDParams()
    assert p.potencia_ti_mw == 50
    assert p.pue == 1.3
    assert p.tipo_refrigeracion == "aire"
    assert math.isclose(p.pct_renovable, 0.8)
