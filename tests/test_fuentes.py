"""Tests OFFLINE de la capa de datos por API (src/cpd/fuentes).

No se conecta a internet: los parsers se alimentan con fixtures de tests/fixtures/ y los polígonos
provinciales de prueba son una versión simplificada guardada en el repositorio.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cpd.fuentes import curado, http, ine, meteo, omie, peeringdb, provincias, red_capacidad, ree, sepe, sismicidad
from cpd.fuentes import actualizar, natura, subestaciones

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "tests" / "fixtures"


def cargar_json(nombre: str):
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def poligonos() -> dict:
    return provincias.cargar_poligonos(FIXTURES / "provincias_simplificadas.geojson")


# ---------------------------------------------------------------- provincias

def test_hay_52_provincias_con_codigos_ine_unicos():
    assert len(provincias.CODIGOS) == 52
    assert provincias.CODIGOS == tuple(f"{i:02d}" for i in range(1, 53))


def test_ccaa_y_geo_ids_de_ree_son_coherentes():
    tabla = provincias.tabla_provincias()
    assert set(tabla["codigo_ccaa"]) <= set(provincias.CCAA_INE)
    assert set(tabla["ree_geo_id"]) <= set(provincias.REE_GEO_ID_CCAA.values())
    assert provincias.ficha("28").ccaa == "Madrid" and provincias.ficha("28").ree_geo_id == 13
    assert provincias.ficha("35").ccaa_codigo == "05" and provincias.ficha("35").ree_geo_id == 8742
    assert provincias.ficha("51").ree_geo_id == 8744  # Ceuta
    assert provincias.ficha("08").ccaa_codigo == "09"  # Barcelona -> Cataluña


def test_emparejar_nombres_del_ine_tolera_caracteres_rotos():
    assert provincias.emparejar_nombre_ine("Almer�a") == "04"
    assert provincias.emparejar_nombre_ine("Coru�ia, A") == "15"
    assert provincias.emparejar_nombre_ine("Palmas, Las") == "35"
    assert provincias.emparejar_nombre_ine("Balears, Illes") == "07"
    assert provincias.emparejar_nombre_ine("Total Nacional") is None


def test_point_in_polygon_asigna_provincias_conocidas(poligonos):
    casos = {
        (40.42, -3.70): "28",  # Madrid
        (41.39, 2.17): "08",  # Barcelona
        (37.39, -5.98): "41",  # Sevilla
        (27.92, -15.58): "35",  # interior de Gran Canaria
        (35.89, -5.32): "51",  # Ceuta
        (35.0, -20.0): None,  # océano Atlántico
    }
    for (lat, lon), esperado in casos.items():
        assert provincias.provincia_de_punto(lat, lon, poligonos) == esperado


def test_poligonos_cubren_las_52_provincias(poligonos):
    assert set(poligonos) == set(provincias.CODIGOS)


# ---------------------------------------------------------------- http

def test_pedir_reintenta_y_falla_con_mensaje_claro(monkeypatch):
    llamadas = []

    class RespuestaMala:
        status_code = 503
        text = "servicio no disponible"

    def fingir_get(self, url, **kwargs):
        llamadas.append(url)
        return RespuestaMala()

    monkeypatch.setattr(http.requests.Session, "get", fingir_get)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    with pytest.raises(http.ErrorFuente, match="HTTP 503"):
        http.pedir("https://ejemplo.invalid/x", reintentos=3, etiqueta="prueba")
    assert len(llamadas) == 3


def test_registrar_escribe_en_el_registro_con_columnas_del_proyecto(tmp_path, monkeypatch):
    registro = tmp_path / "registro.csv"
    monkeypatch.setattr(http, "REGISTRO", registro)
    http.registrar("Fuente X", "Prueba", "https://ejemplo.es/a", tmp_path / "a.json", 12.4)
    cabecera, fila = registro.read_text(encoding="utf-8").splitlines()
    assert cabecera == "fecha_descarga,fuente,descripcion,url,archivo,tam_kb"
    assert fila.split(",")[1] == "Fuente X"


# ---------------------------------------------------------------- meteo

def test_filas_diarias_de_open_meteo():
    ubicacion = {
        "daily": {
            "time": ["2025-01-01", "2025-01-02"],
            "temperature_2m_max": [7.0, 8.5],
            "temperature_2m_min": [-2.9, 1.0],
            "temperature_2m_mean": [0.8, 4.0],
            "relative_humidity_2m_mean": [84, 80],
            "precipitation_sum": [0.0, 5.5],
            "wind_speed_10m_mean": [7.5, 10.0],
            "et0_fao_evapotranspiration": [0.78, 0.9],
        }
    }
    filas = meteo.filas_diarias(ubicacion, "28")
    assert len(filas) == 2
    assert filas[1]["codigo_provincia"] == "28" and filas[1]["precipitacion_mm"] == 5.5
    assert filas[0]["tmedia_c"] == 0.8


def test_free_cooling_cuenta_horas_por_debajo_de_18_grados():
    horas = [f"2025-07-01T{h:02d}:00" for h in range(24)]
    temperaturas = [15.0] * 6 + [25.0] * 18  # 6 horas frescas
    ubicacion = {"hourly": {"time": horas, "temperature_2m": temperaturas}}
    tabla = meteo._tabla_free_cooling([meteo.free_cooling_de_ubicacion(ubicacion, "28")])
    assert tabla.loc[0, "horas_free_cooling"] == 6
    assert tabla.loc[0, "horas_con_dato"] == 24
    assert tabla.loc[0, "pct_horas_free_cooling"] == 25.0


# ---------------------------------------------------------------- ree

def test_precios_diarios_promedian_spot_y_pvpc_por_dia():
    tabla = ree._precios_diarios(cargar_json("ree_precios_muestra.json"))
    dia1 = tabla[tabla["fecha"] == pd.Timestamp("2026-10-01")].iloc[0]
    assert dia1["precio_spot_eur_mwh"] == pytest.approx(82.0)
    assert dia1["precio_pvpc_eur_mwh"] == pytest.approx(110.0)
    # el valor nulo del día 2 se ignora
    dia2 = tabla[tabla["fecha"] == pd.Timestamp("2026-10-02")].iloc[0]
    assert dia2["precio_spot_eur_mwh"] == pytest.approx(60.0)


def test_generacion_renovable_calcula_porcentaje_sin_contar_el_total():
    filas = ree.generacion_desde_respuesta(cargar_json("ree_generacion_muestra.json"), "13")
    resumen = ree.resumen_renovable(pd.DataFrame(filas))
    assert resumen.loc[0, "generacion_total_mwh"] == 1000.0
    assert resumen.loc[0, "generacion_renovable_mwh"] == 600.0
    assert resumen.loc[0, "pct_renovable"] == 60.0


def test_omie_interpreta_marginalpdbc_con_coma_decimal():
    texto = (FIXTURES / "omie_marginalpdbc_muestra.txt").read_text(encoding="utf-8")
    tabla = omie.interpretar_marginalpdbc(texto, pd.Timestamp("2026-11-10").date())
    assert len(tabla) == 4
    assert tabla.loc[1, "precio_es_eur_mwh"] == pytest.approx(179.14)
    assert tabla.loc[1, "momento"] == pd.Timestamp("2026-11-10 01:00")


# ---------------------------------------------------------------- ine / sepe

def test_poblacion_ine_ignora_totales_nacionales_y_secretos():
    tabla = ine.poblacion_desde_series(cargar_json("ine_series_muestra.json"))
    assert set(tabla["codigo_provincia"]) == {"04", "28"}
    almeria = tabla[tabla["codigo_provincia"] == "04"].set_index("anio")["poblacion"]
    assert almeria.loc[2024] == 731000.0
    assert not ((tabla["codigo_provincia"] == "28") & (tabla["anio"] == 2023)).any()  # dato secreto


def test_renta_ine_separa_metricas_por_columna():
    tabla = ine.renta_desde_series(cargar_json("ine_renta_muestra.json"))
    assert set(tabla["codigo_provincia"]) == {"04", "28"}
    almeria = tabla[tabla["codigo_provincia"] == "04"].iloc[0]
    assert almeria["renta_neta_media_persona_eur"] == 12100.0
    assert almeria["renta_neta_media_hogar_eur"] == 28000.0
    madrid = tabla[tabla["codigo_provincia"] == "28"].iloc[0]
    assert madrid["mediana_renta_unidad_consumo_eur"] == 21000.0
    assert pd.isna(madrid["renta_neta_media_persona_eur"])


def test_sepe_agrega_municipios_a_provincia_y_respeta_el_formato_latin1():
    contenido = (FIXTURES / "sepe_muestra.csv").read_text(encoding="utf-8").encode("latin-1")
    agregado = sepe.agregar_provincias(sepe.leer_csv_sepe(contenido))
    almeria = agregado[agregado["codigo_provincia"] == "04"].iloc[0]
    assert almeria["paro_registrado"] == 95  # 65 + 30
    assert almeria["municipios"] == 2
    assert str(almeria["mes"].date()) == "2026-01-01"
    assert set(agregado["codigo_provincia"]) == {"04", "11", "48"}


# ---------------------------------------------------------------- peeringdb / sismos / capacidad / OSM / Natura

def test_peeringdb_asigna_centros_por_coordenadas_o_ciudad(poligonos):
    registros = [
        {"id": 1, "name": "DC Madrid", "city": "Alcobendas", "latitude": 40.5368, "longitude": -3.6486, "net_count": 3},
        {"id": 2, "name": "DC sin coordenadas", "city": "Bilbao", "latitude": None, "longitude": None, "net_count": 1},
        {"id": 3, "name": "DC en el mar", "city": "Desconocida", "latitude": 35.0, "longitude": -20.0, "net_count": 0},
    ]
    fac = peeringdb.asignar_fac(peeringdb._leer_fac(registros), poligonos)
    codigos = fac.set_index("id")["codigo_provincia"]
    assert codigos.loc[1] == "28" and codigos.loc[2] == "48"
    assert pd.isna(codigos.loc[3])  # fuera de España: sin provincia
    assert peeringdb.provincia_de_ciudad("Barcelona") == "08"
    assert peeringdb.provincia_de_ciudad("Burgos") == "09"


def test_resumen_conectividad_cuenta_por_provincia():
    fac = pd.DataFrame({"codigo_provincia": ["28", "28", "08"]})
    ixps = pd.DataFrame({"codigo_provincia": ["28"]})
    resumen = peeringdb.resumen_por_provincia(fac, ixps).set_index("codigo_provincia")
    assert resumen.loc["28", "n_centros_datos"] == 2
    assert resumen.loc["28", "n_ixp"] == 1
    assert resumen.loc["08", "distancia_ixp_km"] == pytest.approx(
        peeringdb.distancia_km(41.39, 2.17, 40.42, -3.70), abs=0.2
    )


def test_sismos_por_provincia_y_anio_descartan_eventos_fuera_de_espana(poligonos):
    eventos = pd.DataFrame(
        [
            {"id": f["id"], "tiempo": f["properties"]["time"], "lat": f["geometry"]["coordinates"][1],
             "lon": f["geometry"]["coordinates"][0], "magnitud": f["properties"]["mag"]}
            for f in cargar_json("emsc_muestra.json")["features"]
        ]
    )
    eventos["anio"] = pd.to_datetime(eventos["tiempo"], utc=True).dt.year
    resumen = sismicidad.sismos_por_provincia_anual(eventos, poligonos).set_index(["codigo_provincia", "anio"])
    madrid = resumen.loc[("28", 2025)]
    assert madrid["n_terremotos"] == 2
    assert madrid["magnitud_max"] == 3.2
    assert madrid["n_terremotos_m3_plus"] == 1
    assert ("08", 2025) in resumen.index
    assert len(resumen) == 2  # el evento del Atlántico no cuenta


def test_capacidad_de_acceso_suma_demanda_por_comunidad():
    tabla = red_capacidad.leer_capacidad(FIXTURES / "ree_capacidad_muestra.csv")
    fila = tabla.set_index("codigo_ccaa")
    assert fila.loc["07", "capacidad_demanda_rdt_disponible_mw"] == 2000.0  # 1500 + 500
    assert fila.loc["07", "nudos"] == 2
    assert fila.loc["16", "capacidad_demanda_rdt_disponible_mw"] == 920.0
    assert fila.loc["09", "capacidad_demanda_rdt_disponible_mw"] == 300.0  # 'N/A' no cuenta


def test_subestaciones_cuentan_220_400_kv_por_provincia(poligonos):
    elementos = cargar_json("overpass_muestra.json")["elements"]
    tabla = subestaciones.contar_por_provincia(elementos, poligonos).set_index("codigo_provincia")
    assert tabla.loc["28", "subestaciones_220_400kv"] == 2
    assert tabla.loc["28", "subestaciones_400kv"] == 1
    assert tabla.loc["08", "subestaciones_400kv"] == 1  # voltaje "220000;400000" cuenta como 400 kV
    assert tabla["subestaciones_220_400kv"].sum() == 3  # el elemento del Atlántico se descarta


def test_natura_convierte_anillos_esri_en_geometria():
    anillos = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
    geometria = natura._anillos_a_geometria(anillos)
    assert geometria.area == pytest.approx(1.0)
    assert natura._anillos_a_geometria([]) is None


# ---------------------------------------------------------------- curado / actualizar

def _tablas_sinteticas() -> dict[str, pd.DataFrame]:
    provincias_df = provincias.tabla_provincias()
    meses = ["2025-01-01", "2025-02-01"]
    clima = pd.DataFrame(
        [
            {"fecha": f"{mes[:8]}{d:02d}", "codigo_provincia": codigo, "tmax_c": 10.0, "tmin_c": 2.0, "tmedia_c": 6.0,
             "humedad_relativa_media_pct": 70.0, "precipitacion_mm": 1.0, "viento_medio_kmh": 5.0, "et0_mm": 2.0}
            for codigo in provincias.CODIGOS
            for mes in meses
            for d in (1, 2)
        ]
    )
    return {
        "provincias": provincias_df,
        "clima_diario": clima,
        "free_cooling": pd.DataFrame(
            [{"mes": "2025-01-01", "codigo_provincia": "28", "horas_free_cooling": 300, "horas_con_dato": 744,
              "pct_horas_free_cooling": 40.32}]
        ),
        "ccaa_demanda": pd.DataFrame([{"codigo_ccaa": "13", "fecha": "2025-01-01", "demanda_mwh": 1000.0}]),
        "poblacion": pd.DataFrame([{"codigo_provincia": "28", "anio": 2025, "poblacion": 6900000.0}]),
        "paro": pd.DataFrame([{"codigo_provincia": "28", "mes": "2025-01-01", "paro_registrado": 690000}]),
        "conectividad": pd.DataFrame([{"codigo_provincia": "28", "n_centros_datos": 9, "n_ixp": 3, "distancia_ixp_km": 0.0}]),
        "precios_diarios": pd.DataFrame([{"fecha": "2025-01-01", "precio_spot_eur_mwh": 80.0, "precio_pvpc_eur_mwh": 120.0}]),
        "tiempo_real_provincia": pd.DataFrame([{"codigo_provincia": "28", "temperatura_actual_c": 12.3}]),
        "energia_tiempo_real": pd.DataFrame([{"demanda_tiempo_real_mw": 33000.0, "precio_spot_actual_eur_mwh": 90.0,
                                              "precio_spot_manana_medio_eur_mwh": 85.0}]),
    }


def test_panel_tiene_una_fila_por_provincia_y_mes_con_nan_donde_falta_dato():
    tablas = _tablas_sinteticas()
    panel = curado.construir_panel(tablas, hasta=pd.Timestamp("2025-02-01"))
    meses = (2025 - 2015) * 12 + 2  # 2015-01 a 2025-02
    assert len(panel) == 52 * meses
    assert {"codigo_provincia", "mes", "tmedia_mes_c", "poblacion", "n_centros_datos"} <= set(panel.columns)
    madrid_ene = panel[(panel["codigo_provincia"] == "28") & (panel["mes"] == pd.Timestamp("2025-01-01"))].iloc[0]
    assert madrid_ene["tmedia_mes_c"] == pytest.approx(6.0)
    assert madrid_ene["horas_free_cooling"] == 300
    assert madrid_ene["demanda_ccaa_mwh"] == 1000.0  # Madrid, CCAA 13
    assert madrid_ene["paro_por_1000_hab"] == pytest.approx(100.0)  # 690000 / 6.9 M * 1000
    # Sin datos de clima para 2015: NaN, no cero
    antiguo = panel[(panel["codigo_provincia"] == "28") & (panel["mes"] == pd.Timestamp("2015-01-01"))].iloc[0]
    assert pd.isna(antiguo["tmedia_mes_c"])
    # Provincia sin conectividad: NaN
    assert pd.isna(panel[panel["codigo_provincia"] == "01"]["n_centros_datos"].iloc[0])


def test_provincias_actual_tiene_52_filas_y_campos_de_tiempo_real():
    tablas = _tablas_sinteticas()
    panel = curado.construir_panel(tablas, hasta=pd.Timestamp("2025-02-01"))
    actual = curado.provincias_actual(panel, tablas)
    assert len(actual) == 52
    madrid = actual.set_index("codigo_provincia").loc["28"]
    assert madrid["temperatura_actual_c"] == 12.3
    assert madrid["demanda_tiempo_real_mw"] == 33000.0
    assert madrid["cpd_existentes"] == 9
    assert madrid["tmedia_mes_c"] == pytest.approx(6.0)  # último mes con dato


def test_diccionario_describe_columnas_del_panel():
    diccionario = curado.diccionario_para(["tmedia_mes_c", "columna_rara"])
    assert diccionario.loc[0, "unidad"] == "°C"
    assert diccionario.loc[1, "descripcion"].startswith("Columna sin descripción")


def test_actualizar_aisla_los_fallos_de_una_fuente(monkeypatch):
    monkeypatch.setattr(actualizar, "_guardar", lambda nombre, tabla: None)  # no escribir en data/curated
    acta = actualizar.Actualizacion()

    def fuente_rota():
        raise http.ErrorFuente("servidor caído")

    actualizar._paso(acta, "fuente_rota", fuente_rota)
    actualizar._paso(acta, "fuente_ok", lambda: pd.DataFrame({"codigo_provincia": ["01"]}))
    estados = {r.nombre: r.estado for r in acta.resultados}
    assert estados["fuente_rota"] == "fallo"
    assert estados["fuente_ok"] == "ok"
