"""Pruebas sin conexión de los conectores y cálculos de clima, agua y población (fixtures pequeñas)."""

from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from cpd.fuentes import agua, curado, embalses, nasa_power, padron
from cpd.fuentes.provincias import CODIGOS


# ------------------------------------------------------------------ NASA POWER

def _respuesta_diaria(valores_t2m: list[float]) -> dict:
    return {
        "properties": {
            "parameter": {
                "T2M": {f"2024010{i + 1}": v for i, v in enumerate(valores_t2m)},
                "WS10M": {f"2024010{i + 1}": 2.0 for i in range(len(valores_t2m))},
            }
        }
    }


def test_nasa_power_convierte_relleno_y_unidades():
    respuesta = _respuesta_diaria([10.0, -999.0, 12.5])
    tabla = nasa_power.parsear_respuesta(respuesta, {"T2M": "tmedia_c", "WS10M": "viento_medio_kmh"}, "%Y%m%d")
    assert list(tabla["tiempo"].dt.strftime("%Y-%m-%d")) == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert pd.isna(tabla.loc[1, "tmedia_c"])  # -999 es ausencia, no temperatura
    assert tabla.loc[0, "viento_medio_kmh"] == pytest.approx(7.2)  # 2 m/s -> 7,2 km/h


def test_nasa_power_horario_usa_formato_con_hora():
    respuesta = {"properties": {"parameter": {"T2M": {"2024010100": 3.4, "2024010101": 2.9}}}}
    tabla = nasa_power.parsear_respuesta(respuesta, {"T2M": "temperatura_c"}, "%Y%m%d%H")
    assert tabla["tiempo"].iloc[1] == pd.Timestamp("2024-01-01 01:00")


def test_nasa_power_respuesta_sin_bloque_lanza_error():
    from cpd.fuentes.http import ErrorFuente

    with pytest.raises(ErrorFuente):
        nasa_power.parsear_respuesta({"otra": 1}, {"T2M": "x"}, "%Y%m%d")


def test_tramos_cubren_los_anios_sin_solapes():
    assert nasa_power._tramos(2015, 2026, 5) == [(2015, 2019), (2020, 2024), (2025, 2026)]
    assert nasa_power._tramos(2015, 2017, 3) == [(2015, 2017)]


def test_free_cooling_cuenta_horas_bajo_18_grados_y_omite_nan():
    horas = pd.date_range("2024-01-01", periods=48, freq="h")
    temperaturas = [10.0] * 24 + [20.0] * 24
    temperaturas[3] = float("nan")  # sin dato: no cuenta ni como frío ni como hora válida
    horario = pd.DataFrame({"tiempo": horas, "temperatura_c": temperaturas})
    tabla = nasa_power.tabla_free_cooling([nasa_power.free_cooling_de_horario(horario, "28")])
    assert tabla.loc[0, "horas_free_cooling"] == 23
    assert tabla.loc[0, "horas_con_dato"] == 47
    assert tabla.loc[0, "pct_horas_free_cooling"] == pytest.approx(48.94)


def test_et0_hargreaves_da_valores_fisicamente_plausibles():
    fechas = pd.Series(pd.to_datetime(["2024-07-15", "2024-01-15"]))
    tabla = pd.DataFrame({"fecha": fechas, "tmax_c": [34.0, 12.0], "tmin_c": [19.0, 3.0], "tmedia_c": [26.0, 7.5]})
    et0 = nasa_power.et0_hargreaves_mm(tabla, 40.4)
    assert 5.0 < et0.iloc[0] < 9.0  # verano en Madrid
    assert 0.5 < et0.iloc[1] < 2.5  # invierno en Madrid
    assert et0.iloc[0] > et0.iloc[1]


# ------------------------------------------------------------------ Embalses (MITECO)

def _tabla_access() -> dict[str, list]:
    """Tabla con el formato de access-parser: decimales con coma y nombres de ámbito dañados."""
    return {
        "FECHA": ["2025-01-07 00:00:00", "2025-01-07 00:00:00", "2025-01-07 00:00:00", "2025-01-14 00:00:00",
                  "2025-01-14 00:00:00", "2025-01-07 00:00:00"],
        "AMBITO_NOMBRE": ["Mi�o - Sil", "Mi�o - Sil", "J�car", "Mi�o - Sil", "Mi�o - Sil", "Mi�o - Sil"],
        "EMBALSE_NOMBRE": ["A", "B", "C", "A", "B", "D"],
        "AGUA_TOTAL": ["100,00", "300,50", "50,00", "100,00", "300,50", "0,00"],
        "AGUA_ACTUAL": ["50,00", "150,25", "10,00", "25,00", "300,50", "5,00"],
    }


def test_access_convierte_decimales_y_normaliza_ambitos():
    tabla = embalses.tabla_access_a_dataframe(_tabla_access())
    assert tabla.loc[0, "capacidad_hm3"] == pytest.approx(100.0)
    assert tabla.loc[1, "volumen_hm3"] == pytest.approx(150.25)
    assert set(tabla["ambito"]) == {"Miño-Sil", "Júcar"}


def test_reservas_semanales_usan_solo_embalses_con_capacidad():
    semanal = embalses.reservas_semanales(embalses.tabla_access_a_dataframe(_tabla_access()))
    enero_7 = semanal[(semanal["fecha"] == "2025-01-07") & (semanal["ambito"] == "Miño-Sil")].iloc[0]
    # A y B con capacidad (100 + 300,5); D tiene capacidad 0 y se ignora
    assert enero_7["reserva_pct"] == pytest.approx(100 * (50 + 150.25) / 400.5, abs=0.01)
    assert enero_7["embalses"] == 2


def test_reservas_mensuales_son_media_de_las_semanas():
    semanal = embalses.reservas_semanales(embalses.tabla_access_a_dataframe(_tabla_access()))
    mensual = embalses.reservas_mensuales(semanal)
    fila = mensual[mensual["ambito"] == "Miño-Sil"].iloc[0]
    assert fila["mes"] == pd.Timestamp("2025-01-01")
    assert fila["semanas_con_dato"] == 2
    esperada = (100 * 200.25 / 400.5 + 100 * 325.5 / 400.5) / 2
    assert fila["reserva_pct_media_mes"] == pytest.approx(esperada, abs=0.01)


def test_asignacion_provincia_ambito_cubre_las_52_provincias():
    assert set(embalses.AMBITO_POR_PROVINCIA) == set(CODIGOS)
    usados = {v for v in embalses.AMBITO_POR_PROVINCIA.values() if v}
    assert usados <= set(embalses.AMBITOS)
    assert embalses.AMBITO_POR_PROVINCIA["28"] == "Tajo"
    assert embalses.AMBITO_POR_PROVINCIA["35"] is None  # Las Palmas: sin embalses en la base


def test_nombre_de_ambito_danado_se_reconoce():
    assert embalses.ambito_canonico("Cuencas Internas de Catalu�a") == "Cuencas Internas de Cataluña"
    assert embalses.ambito_canonico(None) is None


# ------------------------------------------------------------------ WRI y agua

def _zip_wri(tmp_path) -> object:
    filas = []
    for ccaa, score in [("AndalucÃ­a", 4.0), ("Galicia", 2.0)]:
        for peso, factor in [("Tot", 1.0), ("Irr", 0.5)]:
            filas.append({"name_0": "Spain", "name_1": ccaa, "indicator_name": "bws", "weight": peso,
                          "score": score * factor})
    filas.append({"name_0": "Spain", "name_1": "Galicia", "indicator_name": "rfr", "weight": "Tot", "score": 9.0})
    hoja = pd.DataFrame(filas)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        hoja.to_excel(escritor, sheet_name="province_baseline", index=False)
    ruta = tmp_path / "wri.zip"
    with zipfile.ZipFile(ruta, "w") as zf:
        zf.writestr("Aqueduct/ranking.xlsx", buffer.getvalue())
    return ruta


def test_wri_usa_ponderacion_tot_reescala_y_asigna_a_provincias(tmp_path):
    ruta = _zip_wri(tmp_path)
    tabla = agua.estres_hidrico_wri(ruta).set_index("codigo_provincia")
    assert tabla.loc["04", "estres_hidrico_wri_0_1"] == pytest.approx(0.8)  # Andalucía 4,0 / 5
    assert tabla.loc["15", "estres_hidrico_wri_0_1"] == pytest.approx(0.4)  # Galicia 2,0 / 5
    assert pd.isna(tabla.loc["28", "estres_hidrico_wri_0_1"])  # Madrid no aparece en la hoja


def test_balance_hidrico_no_rellena_huecos():
    balance = agua.balance_hidrico_mm(pd.Series([50.0, np.nan]), pd.Series([30.0, 20.0]))
    assert balance.iloc[0] == pytest.approx(20.0)
    assert pd.isna(balance.iloc[1])


def _mensual(precipitaciones: list[float], codigo: str = "28") -> pd.DataFrame:
    meses = pd.date_range("2015-01-01", periods=len(precipitaciones), freq="MS")
    return pd.DataFrame({"mes": meses, "codigo_provincia": codigo, "precipitacion_mes_mm": precipitaciones})


def test_precipitacion_12_meses_exige_ventana_completa():
    acumulado = agua.precipitacion_12_meses(_mensual([10.0] * 13))
    assert acumulado["precipitacion_12m_mm"].iloc[:11].isna().all()
    assert acumulado["precipitacion_12m_mm"].iloc[11] == pytest.approx(120.0)


def test_indice_sequia_negativo_en_anio_seco():
    # 4 años de 12 meses: tres años normales y un año con la mitad de lluvia
    serie = [60.0] * 36 + [30.0] * 12
    indice = agua.indice_sequia_12m(_mensual(serie))
    seco = indice.iloc[-1]["indice_sequia_12m"]
    assert seco < -1.0


def test_indice_sequia_sin_referencia_suficiente_es_nan():
    indice = agua.indice_sequia_12m(_mensual([50.0] * 24))
    assert indice["indice_sequia_12m"].isna().all()  # sin variación: desviación 0 y pocos años


# ------------------------------------------------------------------ Padrón y población

_CSV_PADRON = """﻿Municipios;Sexo;Periodo;Total
28001 Uno;Total;2023;1.250
28001 Uno;Hombres;2023;600
28001 Uno;Total;2022;1.200
28002 Dos;Total;2023;
28002 Dos;Total;2022;800
28003 Tres;Total;2023;2.000
28003 Tres;Total;2022;2.000
"""


def test_padron_suma_provincia_y_marca_municipios_desaparecidos(tmp_path):
    ruta = tmp_path / "padron.csv"
    ruta.write_text(_CSV_PADRON, encoding="utf-8")
    tabla = padron.leer_padron(ruta).set_index(["codigo_provincia", "anio"])
    assert tabla.loc[("28", 2023), "poblacion_padron"] == pytest.approx(3250.0)  # 1.250 + 2.000 (sin el sin-dato)
    assert tabla.loc[("28", 2023), "municipios_sin_dato"] == 1  # 28002 tenía dato en 2022 y no en 2023
    assert tabla.loc[("28", 2022), "poblacion_padron"] == pytest.approx(4000.0)  # 1.200 + 800 + 2.000
    assert tabla.loc[("28", 2022), "municipios_sin_dato"] == 0


def test_combinar_poblacion_prefiere_tempus_y_usa_padron_despues():
    tempus = pd.DataFrame([{"codigo_provincia": "28", "anio": 2021, "poblacion": 6_800_000.0}])
    pad = pd.DataFrame([
        {"codigo_provincia": "28", "anio": 2021, "poblacion_padron": 6_850_000.0, "municipios": 179, "municipios_sin_dato": 0},
        {"codigo_provincia": "28", "anio": 2022, "poblacion_padron": 6_750_336.0, "municipios": 179, "municipios_sin_dato": 0},
    ])
    combinada = padron.combinar_poblacion(tempus, pad).set_index("anio")
    assert combinada.loc[2021, "poblacion"] == 6_800_000.0
    assert combinada.loc[2021, "fuente_poblacion"] == "INE Tempus3 (2852)"
    assert combinada.loc[2022, "poblacion"] == 6_750_336.0
    assert combinada.loc[2022, "fuente_poblacion"] == "INE padrón (29005)"
    assert combinada.loc[2021, "diferencia_padron_vs_tempus_pct"] == pytest.approx(0.74, abs=0.01)


def test_combinar_poblacion_sin_tempus_usa_solo_padron():
    pad = pd.DataFrame([{"codigo_provincia": "28", "anio": 2025, "poblacion_padron": 7_137_031.0,
                         "municipios": 179, "municipios_sin_dato": 0}])
    combinada = padron.combinar_poblacion(pd.DataFrame(), pad)
    assert combinada.loc[0, "poblacion"] == 7_137_031.0


# ------------------------------------------------------------------ Curado (clima mensual y panel)

def _clima_dias(dias_por_mes: dict[str, int], codigo: str = "28") -> pd.DataFrame:
    filas = []
    for mes, dias in dias_por_mes.items():
        for d in range(1, dias + 1):
            filas.append({"fecha": pd.Timestamp(f"{mes}-{d:02d}"), "codigo_provincia": codigo, "tmedia_c": 20.0,
                          "tmax_c": 36.0 if d == 1 else 30.0, "tmin_c": 10.0, "humedad_relativa_media_pct": 50.0,
                          "precipitacion_mm": 1.0, "viento_medio_kmh": 8.0, "radiacion_solar_kwh_m2_dia": 6.0,
                          "et0_hargreaves_mm": 3.0})
    return pd.DataFrame(filas)


def test_clima_mensual_acumulados_solo_con_mes_completo():
    clima = _clima_dias({"2025-01": 31, "2025-02": 10})
    mensual = curado._clima_mensual(clima).set_index("mes")
    enero = mensual.loc[pd.Timestamp("2025-01-01")]
    febrero = mensual.loc[pd.Timestamp("2025-02-01")]
    assert enero["precipitacion_mes_mm"] == pytest.approx(31.0)
    assert enero["et0_hargreaves_mes_mm"] == pytest.approx(93.0)
    assert enero["dias_mas_35c"] == 1
    assert pd.isna(febrero["precipitacion_mes_mm"])  # febrero incompleto: no se suma
    assert febrero["tmedia_mes_c"] == pytest.approx(20.0)  # las medias sí se calculan


def test_panel_une_balance_reservas_y_wri():
    clima = _clima_dias({"2025-01": 31})
    reservas = pd.DataFrame([{"mes": "2025-01-01", "ambito": "Tajo", "reserva_pct_media_mes": 55.0,
                              "volumen_hm3_media_mes": 1000.0, "capacidad_hm3_media_mes": 1800.0,
                              "semanas_con_dato": 4}])
    wri = pd.DataFrame([{"codigo_provincia": "28", "estres_hidrico_wri_0_1": 0.8}])
    from cpd.fuentes import provincias

    tablas = {"provincias": provincias.tabla_provincias(), "clima_diario": clima,
              "reservas_ambito_mensual": reservas, "estres_hidrico_wri": wri}
    panel = curado.construir_panel(tablas, hasta=pd.Timestamp("2025-01-01"))
    madrid = panel[(panel["codigo_provincia"] == "28") & (panel["mes"] == pd.Timestamp("2025-01-01"))].iloc[0]
    assert madrid["ambito_hidrografico"] == "Tajo"
    assert madrid["reserva_hidrica_pct"] == pytest.approx(55.0)
    assert madrid["balance_hidrico_mes_mm"] == pytest.approx(31.0 - 93.0)
    assert madrid["estres_hidrico_wri_0_1"] == pytest.approx(0.8)
    assert pd.isna(madrid["indice_sequia_12m"])  # sin 12 meses de historia
    assert panel["codigo_provincia"].nunique() == 52
