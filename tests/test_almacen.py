"""Tests del almacén DuckDB (sin red): se construye a partir de tablas de ejemplo en una carpeta temporal."""

import csv

import duckdb
import pandas as pd
import pytest

from cpd.almacen import construir


@pytest.fixture
def datos(tmp_path):
    curado = tmp_path / "curated"
    tablas = curado / "tablas"
    tablas.mkdir(parents=True)
    pd.DataFrame({"codigo_provincia": ["01", "08", "28"], "provincia": ["Araba/Álava", "Barcelona", "Madrid"],
                  "ccaa": ["País Vasco", "Cataluña", "Madrid"]}).to_csv(tablas / "provincias.csv", index=False)
    pd.DataFrame({"codigo_provincia": ["01", "28"], "temperatura_actual_c": [9.5, 13.5]}).to_csv(
        tablas / "clima_actual.csv", index=False)
    panel = pd.DataFrame({
        "codigo_provincia": ["08", "08", "28", "28"],
        "mes": pd.to_datetime(["2025-11-01", "2026-01-01", "2025-11-01", "2026-01-01"]),
        "temp_media_c": [14.0, 10.0, 11.0, 6.0],
    })
    panel.to_parquet(curado / "panel_provincia_mes.parquet", index=False)
    pd.DataFrame({"codigo_provincia": ["08", "28"], "cpd_existentes": [12, 30]}).to_csv(
        curado / "provincias_actual.csv", index=False)
    registro = tmp_path / "_registro_descargas.csv"
    with registro.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha_descarga", "fuente", "descripcion", "url", "archivo", "tam_kb"])
        w.writerow(["2026-11-13T19:00:00", "Open-Meteo", "Clima", "https://api.open-meteo.com", "data/raw/api/meteo", 1])
        w.writerow(["2026-11-13T19:05:00", "Open-Meteo", "Clima", "https://api.open-meteo.com", "data/raw/api/meteo", 2])
    return tmp_path / "almacen.duckdb", curado, registro


def test_construye_esquemas_y_tablas(datos):
    ruta, curado, registro = datos
    resumen = construir(ruta, curado, registro)
    assert resumen["fuentes.provincias"] == 3
    assert resumen["fuentes.clima_actual"] == 2
    assert resumen["modelo.panel_provincia_mes"] == 4
    assert resumen["modelo.provincias_actual"] == 2
    assert resumen["dw.dim_provincia"] == 3
    assert resumen["dw.dim_fuente"] == 1  # dos descargas de la misma fuente se agrupan


def test_codigos_conservan_ceros_a_la_izquierda(datos):
    ruta, curado, registro = datos
    construir(ruta, curado, registro)
    with duckdb.connect(str(ruta), read_only=True) as con:
        codigos = [r[0] for r in con.execute(
            "SELECT codigo_provincia FROM dw.dim_provincia ORDER BY 1").fetchall()]
    assert codigos == ["01", "08", "28"]


def test_dim_tiempo_cubre_todos_los_meses_del_panel(datos):
    ruta, curado, registro = datos
    construir(ruta, curado, registro)
    with duckdb.connect(str(ruta), read_only=True) as con:
        meses = [r[0] for r in con.execute("SELECT etiqueta FROM dw.dim_tiempo ORDER BY mes").fetchall()]
        filas_hecho = con.execute("SELECT count(*) FROM dw.fact_provincia_mes").fetchall()[0][0]
    assert meses == ["2025-11", "2025-12", "2026-01"]  # incluye el mes sin datos (diciembre)
    assert filas_hecho == 4


def test_registro_de_carga_y_reconstruccion(datos):
    ruta, curado, registro = datos
    construir(ruta, curado, registro)
    construir(ruta, curado, registro)  # reconstruir no duplica nada
    with duckdb.connect(str(ruta), read_only=True) as con:
        cargas = con.execute("SELECT count(*) FROM meta.carga").fetchall()[0][0]
    assert cargas == 4  # provincias, clima_actual, panel, provincias_actual
    assert not ruta.with_suffix(".tmp.duckdb").exists()
