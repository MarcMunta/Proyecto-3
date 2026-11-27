"""Tests de las capas Bronze/Silver/Gold, los watermarks y la capa Gold del dashboard (sin red)."""

import csv
import datetime as dt
import os
import time

import duckdb
import pandas as pd
import pytest

from cpd import capas
from cpd.almacen import _lector_csv, construir


# ------------------------------------------------------------------------------------------ Silver → Parquet

def test_tablas_a_parquet_conserva_codigos_y_no_repite_si_no_cambia(tmp_path):
    pd.DataFrame({"codigo_provincia": ["01", "08"], "valor": [1.5, 2.5]}).to_csv(tmp_path / "t.csv", index=False)
    escritas = capas.tablas_a_parquet(tmp_path, _lector_csv)
    assert escritas == [tmp_path / "t.parquet"]
    tabla = pd.read_parquet(tmp_path / "t.parquet")
    assert tabla["codigo_provincia"].tolist() == ["01", "08"]  # R-4: los ceros a la izquierda no se pierden
    assert capas.tablas_a_parquet(tmp_path, _lector_csv) == []  # nada cambió: no se repite el trabajo


def test_tablas_a_parquet_regenera_si_el_csv_es_mas_nuevo(tmp_path):
    ruta = tmp_path / "t.csv"
    pd.DataFrame({"x": [1]}).to_csv(ruta, index=False)
    capas.tablas_a_parquet(tmp_path, _lector_csv)
    pd.DataFrame({"x": [1, 2]}).to_csv(ruta, index=False)
    futuro = time.time() + 10
    os.utime(ruta, (futuro, futuro))
    assert capas.tablas_a_parquet(tmp_path, _lector_csv) == [tmp_path / "t.parquet"]
    assert len(pd.read_parquet(tmp_path / "t.parquet")) == 2


# ------------------------------------------------------------------------------------------------ Watermarks

def test_watermarks_toman_la_ultima_fecha_de_cada_tabla():
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA fuentes")
        con.execute("CREATE TABLE fuentes.a AS SELECT * FROM (VALUES (DATE '2026-01-01'), (DATE '2026-03-01')) t(fecha)")
        con.execute("CREATE TABLE fuentes.b AS SELECT * FROM (VALUES (2024), (2025)) t(anio)")
        con.execute("CREATE TABLE fuentes.sin_tiempo AS SELECT 1 AS x")
        marcas = capas.watermarks(con, ("fuentes",)).set_index("tabla")
    assert marcas.loc["a", "watermark"] == "2026-03-01"
    assert marcas.loc["b", "watermark"] == "2025"
    assert "sin_tiempo" not in marcas.index


def test_fecha_de_watermark_entiende_fechas_meses_y_anios():
    assert capas.fecha_de_watermark("2026-03-01") == pd.Timestamp(2026, 3, 1)
    assert capas.fecha_de_watermark("2025") == pd.Timestamp(2025, 12, 31)
    assert capas.fecha_de_watermark("no es fecha") is None


def test_historial_de_watermarks_detecta_si_avanzan(tmp_path):
    ruta = tmp_path / "historial.csv"
    primera = pd.DataFrame([{"esquema": "fuentes", "tabla": "a", "columna": "fecha", "watermark": "2026-01-01",
                             "filas": 10}])
    salida = capas.guardar_historial(primera, ruta, dt.datetime(2026, 11, 1))
    assert salida["avanza"].tolist() == [True] and salida["anterior"].tolist() == [""]
    igual = capas.guardar_historial(primera, ruta, dt.datetime(2026, 11, 2))
    assert igual["avanza"].tolist() == [False]
    nueva = primera.assign(watermark="2026-02-01", filas=11)
    avanza = capas.guardar_historial(nueva, ruta, dt.datetime(2026, 11, 3))
    assert avanza["avanza"].tolist() == [True] and avanza["anterior"].tolist() == ["2026-01-01"]
    with ruta.open(encoding="utf-8") as f:
        assert len(list(csv.reader(f))) == 4  # cabecera + tres construcciones: queda traza de cada una


# ----------------------------------------------------------------------------------------- Bronze y formatos

def test_inventario_bronze_agrupa_por_carpeta_y_por_api(tmp_path):
    raw = tmp_path / "raw"
    (raw / "api" / "ree").mkdir(parents=True)
    (raw / "demografia").mkdir()
    (raw / "api" / "ree" / "a.json").write_text("{}", encoding="utf-8")
    (raw / "api" / "ree" / "b.json").write_text("{}", encoding="utf-8")
    (raw / "demografia" / "p.csv").write_text("x\n1\n", encoding="utf-8")
    (raw / ".gitkeep").write_text("", encoding="utf-8")
    tabla = capas.inventario_bronze(raw).set_index("carpeta")
    assert tabla.loc["api/ree", "ficheros"] == 2 and tabla.loc["api/ree", "formatos"] == "json"
    assert tabla.loc["demografia", "ficheros"] == 1
    assert "(raíz)" not in tabla.index  # .gitkeep no cuenta


def test_comparar_formatos_da_la_misma_media_con_todos_los_motores(tmp_path):
    datos = pd.DataFrame({"codigo_provincia": ["01"] * 200, "valor_c": [float(i) for i in range(200)]})
    datos.to_csv(tmp_path / "t.csv", index=False)
    datos.to_parquet(tmp_path / "t.parquet", index=False)
    assert capas.columna_numerica(tmp_path / "t.parquet") == "valor_c"
    res = capas.comparar_formatos(tmp_path / "t.csv", tmp_path / "t.parquet", "valor_c", repeticiones=1)
    assert set(zip(res["formato"], res["motor"])) == {("CSV", "pandas"), ("Parquet", "pandas"),
                                                       ("CSV", "DuckDB"), ("Parquet", "DuckDB")}
    assert res["media"].round(6).nunique() == 1 and res["media"].iloc[0] == pytest.approx(99.5)


# ------------------------------------------------------------------------------- Gold: de punta a punta

@pytest.fixture
def proyecto(tmp_path):
    raiz = tmp_path / "repo"
    curado = raiz / "data" / "curated"
    (curado / "tablas").mkdir(parents=True)
    raw = raiz / "data" / "raw"
    (raw / "api" / "meteo").mkdir(parents=True)
    (raw / "api" / "meteo" / "2025.json").write_text("{}", encoding="utf-8")
    pd.DataFrame({"codigo_provincia": ["08", "28"], "provincia": ["Barcelona", "Madrid"]}).to_csv(
        curado / "tablas" / "provincias.csv", index=False)
    pd.DataFrame({"codigo_provincia": ["08", "28"], "fecha": ["2026-11-01", "2026-11-20"],
                  "tmedia_c": [12.0, 9.0]}).to_csv(curado / "tablas" / "clima_diario.csv", index=False)
    panel = pd.DataFrame({"codigo_provincia": ["08", "28"], "mes": pd.to_datetime(["2026-10-01", "2026-10-01"]),
                          "tmedia_mes_c": [15.0, 12.0]})
    panel.to_csv(curado / "panel_provincia_mes.csv", index=False)
    panel.to_parquet(curado / "panel_provincia_mes.parquet", index=False)
    registro = raw / "_registro_descargas.csv"
    with registro.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha_descarga", "fuente", "descripcion", "url", "archivo", "tam_kb"])
        w.writerow(["2026-11-13T19:00:00", "Open-Meteo", "Clima 2025", "https://archive-api.open-meteo.com/v1/a",
                    "data/raw/api/meteo/2025.json", 1024])
        w.writerow(["2026-11-14T10:00:00", "Fuente nueva", "Algo", "https://ejemplo.org/x", "data/raw/x.csv", 512])
    return raiz, curado, registro


def test_construir_crea_la_capa_gold_del_dashboard(proyecto):
    raiz, curado, registro = proyecto
    ruta = raiz / "data" / "almacen" / "p3_cpd.duckdb"
    resumen = construir(ruta, curado, registro)
    for tabla in ("capas", "inventario_bronze", "apis", "descargas_dia", "watermark", "tablas", "formatos", "kpis"):
        assert f"gold.{tabla}" in resumen
    assert (curado / "tablas" / "clima_diario.parquet").exists()  # Silver también en Parquet
    with duckdb.connect(str(ruta), read_only=True) as con:
        apis = con.execute("SELECT fuente, descargas, modulo, megabytes FROM gold.apis").df().set_index("fuente")
        tablas = con.execute("SELECT esquema, tabla, capa, formato FROM gold.tablas").df().set_index("tabla")
        marca = con.execute("SELECT watermark FROM gold.watermark WHERE tabla = 'clima_diario'").fetchall()[0][0]
        kpis = con.execute("SELECT fuentes, descargas FROM gold.kpis").fetchall()[0]
        capas_df = con.execute("SELECT capa, ficheros FROM gold.capas").df().set_index("capa")
    assert apis.loc["Open-Meteo", "modulo"] == "cpd.fuentes.meteo"
    assert apis.loc["Fuente nueva", "modulo"] == "sin catalogar"  # se ve, no se esconde
    assert apis.loc["Open-Meteo", "megabytes"] == pytest.approx(1.0)
    assert tablas.loc["clima_diario", "capa"] == "silver" and tablas.loc["clima_diario", "formato"] == "parquet"
    assert str(marca).startswith("2026-11-20")
    assert kpis == (2, 2)
    assert capas_df.loc["bronze", "ficheros"] == 2  # el JSON de la API y el registro
    assert (ruta.parent / capas.NOMBRE_HISTORIAL).exists()


def test_el_catalogo_cubre_las_fuentes_del_codigo():
    modulos = {f.modulo for f in capas.CATALOGO_APIS.values() if f.modulo.startswith("cpd.fuentes.")}
    for modulo in modulos:
        __import__(modulo)  # cada módulo citado existe
    assert {f.naturaleza for f in capas.CATALOGO_APIS.values()} <= {"estático", "semiestático", "dinámico"}
