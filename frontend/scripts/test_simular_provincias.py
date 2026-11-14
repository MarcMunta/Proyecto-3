"""Tests de la simulación provincial del mapa (frontend/scripts/simular_provincias.py).

Ejecutar desde la raíz del repositorio:
    .venv\\Scripts\\python.exe -m pytest frontend/scripts -q
Necesita los datos curados (data/curated/provincias_actual.* y panel_provincia_mes.*); si no están, se omiten.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simular_provincias as sp  # noqa: E402

HAY_DATOS = (sp.CURADO / "provincias_actual.parquet").exists() or (sp.CURADO / "provincias_actual.csv").exists()


def test_clases_rentabilidad_no_viable_y_tercios():
    estado = ["Viable", "No viable", "Viable", "Viable con condiciones", "Viable", "Viable", "Viable"]
    van = [30.0, 50.0, 20.0, 10.0, -5.0, 25.0, None]
    c = sp.clases_rentabilidad(estado, van)
    assert c[1] == "no_rentable"  # no viable aunque tenga VAN alto
    assert c[4] == "no_rentable"  # VAN negativo
    assert c[6] == "no_rentable"  # sin VAN
    assert [c[0], c[5], c[2], c[3]] == ["alta", "alta", "media", "baja"]


@pytest.fixture(scope="module")
def datos():
    if not HAY_DATOS:
        pytest.skip("faltan los datos curados en data/curated")
    return sp.simular()


def test_cubre_las_52_provincias(datos):
    provincias = datos["provincias"]
    codigos = [p["codigo_provincia"] for p in provincias]
    assert len(provincias) == 52
    assert len(set(codigos)) == 52
    assert {f"{i:02d}" for i in range(1, 53)} == set(codigos)


def test_cada_provincia_tiene_clase_y_cifras(datos):
    for p in datos["provincias"]:
        assert p["rentabilidad_clase"] in sp.CLASES
        assert p["estado"] in ("Viable", "Viable con condiciones", "No viable")
        for campo in ("van_eur", "roi", "capex_eur", "opex_eur_anual", "score_viabilidad", "temp_media_anual_c"):
            assert p[campo] is not None and math.isfinite(p[campo]), (p["provincia"], campo)
        if p["estado"] == "No viable":
            assert p["rentabilidad_clase"] == "no_rentable"
        assert isinstance(p["motivos"], list) and p["motivos"]


def test_usa_el_precio_de_12_meses_y_dice_la_fecha(datos):
    assert datos["tipo"] == "simulacion"
    assert datos["precio_luz_usado_eur_mwh"] > 0
    assert datos["mes_referencia"]
    assert all(p["precio_luz_usado_eur_mwh"] == datos["precio_luz_usado_eur_mwh"] for p in datos["provincias"])


def test_las_cuatro_clases_aparecen(datos):
    clases = {p["rentabilidad_clase"] for p in datos["provincias"]}
    assert {"alta", "media", "baja"} <= clases
