"""Clima histórico por provincia desde NASA POWER (API pública, sin clave).

Endpoints:
- Diario:  https://power.larc.nasa.gov/api/temporal/daily/point
- Horario: https://power.larc.nasa.gov/api/temporal/hourly/point
Comunidad "AG" (agroclimatología): incluye temperatura, humedad, precipitación, viento y radiación. La evapotranspiración de referencia se calcula con Hargreaves (FAO-56) desde temperaturas y latitud; EVPTRNS (evapotranspiración real) no se usa por su escala poco fiable en la capital.
Hora estándar local (time-standard=LST).

Por qué NASA POWER y no Open-Meteo para la historia: el archivo de Open-Meteo devolvió HTTP 429
("Daily API request limit exceeded") durante la carga; Open-Meteo queda solo para el clima actual
y la previsión corta.

Cobertura: reanálisis MERRA-2 (malla de ~0,5° x 0,625°): el valor de cada capital es el de la celda
más cercana. Es un clima a escala regional, no una medición de estación.

Caché: data/raw/api/nasa_power/{diario,horario}/<codigo>_<anio_ini>_<anio_fin>.json por bloque de
años. Los bloques cerrados no se vuelven a pedir; el bloque que contiene el año en curso sí se
actualiza en cada refresco. Los valores de relleno (-999) se convierten en NaN.
"""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, leer_cache_json, registrar
from cpd.fuentes.provincias import PROVINCIAS

FUENTE: str = "NASA POWER"
URL_DIARIO: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
URL_HORARIO: str = "https://power.larc.nasa.gov/api/temporal/hourly/point"
COMUNIDAD: str = "AG"
ZONA_HORARIA: str = "LST"  # hora local estándar
VALOR_AUSENTE: float = -999.0
UMBRAL_FREE_COOLING_C: float = 18.0
UMBRAL_CALOR_EXTREMO_C: float = 35.0
MJ_POR_MM_EVAPORADO: float = 2.45  # calor latente de vaporización: 1 mm de agua ≈ 2,45 MJ/m²
RETRASO_PUBLICACION_DIAS: int = 2  # POWER publica con unos días de retraso
TRAMO_DIARIO_ANIOS: int = 5
TRAMO_HORARIO_ANIOS: int = 3
CARPETA: Path = RUTA_API / "nasa_power"

# Variable POWER -> (nombre en el proyecto, conversión de unidades)
VARIABLES_DIARIAS: dict[str, str] = {
    "T2M": "tmedia_c",
    "T2M_MAX": "tmax_c",
    "T2M_MIN": "tmin_c",
    "RH2M": "humedad_relativa_media_pct",
    "PRECTOTCORR": "precipitacion_mm",
    "WS10M": "viento_medio_kmh",            # m/s -> km/h (se convierte al leer)
    "ALLSKY_SFC_SW_DWN": "radiacion_solar_kwh_m2_dia",
}
VARIABLES_HORARIAS: dict[str, str] = {"T2M": "temperatura_c"}


def radiacion_extraterrestre_mj(fechas: pd.Series, latitud_grados: float) -> pd.Series:
    """Radiación extraterrestre diaria Ra (MJ/m²/día) según FAO-56 (ecuaciones 21 a 25)."""
    j = fechas.dt.day_of_year.to_numpy(dtype=float)
    phi = np.radians(latitud_grados)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    delta = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    return pd.Series(ra, index=fechas.index)


def et0_hargreaves_mm(tabla: pd.DataFrame, latitud_grados: float) -> pd.Series:
    """ET0 de referencia por Hargreaves-Samani (FAO-56 ec. 52), en mm/día.

    ET0 = 0,0023 · (Ra / 2,45) · (Tmedia + 17,8) · raíz(Tmax − Tmin). Usa solo temperaturas y latitud;
    NaN si falta alguna temperatura. Es una estimación: no sustituye a Penman-Monteith completo.
    """
    ra_mm = radiacion_extraterrestre_mj(tabla["fecha"], latitud_grados) / MJ_POR_MM_EVAPORADO
    rango = (tabla["tmax_c"] - tabla["tmin_c"]).clip(lower=0)
    return (0.0023 * ra_mm * (tabla["tmedia_c"] + 17.8) * np.sqrt(rango)).round(3)


def _tramos(anio_inicio: int, anio_fin: int, anios: int) -> list[tuple[int, int]]:
    """Divide [anio_inicio, anio_fin] en bloques de `anios` años."""
    tramos = []
    inicio = anio_inicio
    while inicio <= anio_fin:
        fin = min(inicio + anios - 1, anio_fin)
        tramos.append((inicio, fin))
        inicio = fin + 1
    return tramos


def _fin_disponible(fin: int) -> dt.date:
    """Último día pedible para un bloque: no posterior a hoy menos el retraso de publicación."""
    limite = dt.date.today() - dt.timedelta(days=RETRASO_PUBLICACION_DIAS)
    return min(dt.date(fin, 12, 31), limite)


def parsear_respuesta(respuesta: dict[str, Any], variables: dict[str, str], formato_fecha: str) -> pd.DataFrame:
    """Convierte la respuesta JSON de POWER en una tabla con una fila por instante.

    Args:
        respuesta: JSON devuelto por POWER (bloque properties.parameter).
        variables: variable POWER -> nombre de columna del proyecto.
        formato_fecha: "%Y%m%d" (diario) o "%Y%m%d%H" (horario).

    Returns:
        DataFrame con columna `tiempo` (datetime) y las variables renombradas, sin valores -999.
    """
    try:
        parametros = respuesta["properties"]["parameter"]
    except (KeyError, TypeError) as error:
        raise ErrorFuente("NASA POWER: la respuesta no contiene properties.parameter") from error
    tabla = pd.DataFrame({var: parametros.get(var, {}) for var in variables})
    tabla.index = pd.to_datetime(tabla.index.astype(str), format=formato_fecha)
    tabla = tabla.replace(VALOR_AUSENTE, float("nan")).astype(float)
    tabla = tabla.rename(columns=variables).reset_index(names="tiempo")
    if "viento_medio_kmh" in tabla:
        tabla["viento_medio_kmh"] = tabla["viento_medio_kmh"] * 3.6
    return tabla.sort_values("tiempo").reset_index(drop=True)


def _pedir_bloque(url: str, variables: dict[str, str], lat: float, lon: float, anio_ini: int, anio_fin: int,
                  ruta: Path, horario: bool, codigo: str) -> dict[str, Any]:
    """Pide un bloque de años a POWER para un punto, con caché si el bloque está cerrado."""
    cerrado = anio_fin < dt.date.today().year
    if cerrado:
        cache = leer_cache_json(ruta)
        if cache is not None:
            return cache
    fin = _fin_disponible(anio_fin)
    parametros = {
        "parameters": ",".join(variables),
        "community": COMUNIDAD,
        "latitude": lat,
        "longitude": lon,
        "start": f"{anio_ini}0101",
        "end": fin.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": ZONA_HORARIA,
    }
    datos = json_de(url, params=parametros, etiqueta=f"{FUENTE} {codigo} {anio_ini}-{anio_fin}")
    if not isinstance(datos, dict) or "properties" not in datos:
        raise ErrorFuente(f"{FUENTE} {codigo} {anio_ini}-{anio_fin}: respuesta inesperada")
    guardar_cache_json(ruta, datos)
    registrar(FUENTE, f"{'Horario' if horario else 'Diario'} {codigo} {anio_ini}-{anio_fin}", url, ruta,
              ruta.stat().st_size / 1024)
    return datos


def _serie_provincia(codigo: str, lat: float, lon: float, anio_inicio: int, anio_fin: int, horario: bool) -> pd.DataFrame:
    """Serie diaria u horaria de una provincia uniendo sus bloques de años."""
    url = URL_HORARIO if horario else URL_DIARIO
    variables = VARIABLES_HORARIAS if horario else VARIABLES_DIARIAS
    carpeta = CARPETA / ("horario" if horario else "diario")
    anios = TRAMO_HORARIO_ANIOS if horario else TRAMO_DIARIO_ANIOS
    partes = []
    for ini, fin in _tramos(anio_inicio, anio_fin, anios):
        ruta = carpeta / f"{codigo}_{ini}_{fin}.json"
        respuesta = _pedir_bloque(url, variables, lat, lon, ini, fin, ruta, horario, codigo)
        partes.append(parsear_respuesta(respuesta, variables, "%Y%m%d%H" if horario else "%Y%m%d"))
        time.sleep(0.5)  # cortesía con POWER entre bloques
    serie = pd.concat(partes, ignore_index=True).drop_duplicates("tiempo")
    return serie.dropna(how="all", subset=[c for c in serie.columns if c != "tiempo"])


def clima_diario_power(anio_inicio: int = 2015, anio_fin: int | None = None) -> pd.DataFrame:
    """Clima diario por provincia (capital) desde NASA POWER, hasta el último día publicado.

    Returns:
        DataFrame largo: fecha, codigo_provincia, tmedia_c, tmax_c, tmin_c, humedad_relativa_media_pct,
        precipitacion_mm, viento_medio_kmh, radiacion_solar_kwh_m2_dia, et0_hargreaves_mm.
    """
    anio_fin = anio_fin or dt.date.today().year
    partes = []
    for provincia in PROVINCIAS:
        serie = _serie_provincia(provincia.codigo, provincia.lat, provincia.lon, anio_inicio, anio_fin, horario=False)
        serie = serie.rename(columns={"tiempo": "fecha"})
        serie["codigo_provincia"] = provincia.codigo
        partes.append(serie)
    tabla = pd.concat(partes, ignore_index=True)
    limite = pd.Timestamp(dt.date.today() - dt.timedelta(days=1))
    tabla = tabla[tabla["fecha"] <= limite].copy()
    latitudes = {p.codigo: p.lat for p in PROVINCIAS}
    tabla["et0_hargreaves_mm"] = pd.concat(
        [et0_hargreaves_mm(g, latitudes[c]) for c, g in tabla.groupby("codigo_provincia")]
    ).reindex(tabla.index)
    return tabla.sort_values(["codigo_provincia", "fecha"]).reset_index(drop=True)


def free_cooling_de_horario(horario: pd.DataFrame, codigo: str) -> pd.DataFrame:
    """Horas mensuales con temperatura < 18 °C a partir de una serie horaria (columnas tiempo, temperatura_c)."""
    datos = horario.dropna(subset=["temperatura_c"]).copy()
    datos["mes"] = datos["tiempo"].dt.to_period("M").dt.to_timestamp()
    datos["frio"] = datos["temperatura_c"] < UMBRAL_FREE_COOLING_C
    agregado = datos.groupby("mes").agg(horas_free_cooling=("frio", "sum"), horas_con_dato=("frio", "size")).reset_index()
    agregado["codigo_provincia"] = codigo
    return agregado


def free_cooling_mensual_power(anio_inicio: int = 2015, anio_fin: int | None = None) -> pd.DataFrame:
    """Horas mensuales de free-cooling (T < 18 °C) por provincia desde la serie horaria de POWER.

    Returns:
        DataFrame: mes, codigo_provincia, horas_free_cooling, horas_con_dato, pct_horas_free_cooling.
    """
    anio_fin = anio_fin or dt.date.today().year
    partes = []
    for provincia in PROVINCIAS:
        horario = _serie_provincia(provincia.codigo, provincia.lat, provincia.lon, anio_inicio, anio_fin, horario=True)
        partes.append(free_cooling_de_horario(horario, provincia.codigo))
    return tabla_free_cooling(partes)


def tabla_free_cooling(partes: list[pd.DataFrame]) -> pd.DataFrame:
    """Une las tablas mensuales por provincia y calcula el porcentaje de horas en free-cooling."""
    columnas = ["mes", "codigo_provincia", "horas_free_cooling", "horas_con_dato", "pct_horas_free_cooling"]
    if not partes:
        return pd.DataFrame(columns=columnas)
    tabla = pd.concat(partes, ignore_index=True)
    tabla["horas_free_cooling"] = tabla["horas_free_cooling"].astype(int)
    tabla["pct_horas_free_cooling"] = (100 * tabla["horas_free_cooling"] / tabla["horas_con_dato"]).round(2)
    return tabla[columnas].sort_values(["codigo_provincia", "mes"]).reset_index(drop=True)
