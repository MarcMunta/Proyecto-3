"""Clima por provincia desde Open-Meteo (API libre, sin clave).

Endpoints usados:
- Archivo histórico ERA5 (diario y horario, desde 1940, hasta ayer):
  https://archive-api.open-meteo.com/v1/archive
- Previsión y estado actual (tiempo real):
  https://api.open-meteo.com/v1/forecast

Se pide un año entero para las 52 capitales en UNA sola llamada (la API admite varias
coordenadas separadas por comas). Cada año se cachea en data/raw/api/meteo/ y los años
cerrados no se vuelven a pedir.

Free-cooling: nº de horas del mes con temperatura del aire inferior a 18 °C (umbral de
referencia para enfriar con aire exterior sin compresor). Se calcula sobre la serie horaria.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, leer_cache_json, registrar
from cpd.fuentes.provincias import PROVINCIAS

URL_ARCHIVO: str = "https://archive-api.open-meteo.com/v1/archive"
URL_PREVISION: str = "https://api.open-meteo.com/v1/forecast"
ETIQUETA: str = "Open-Meteo"
CARPETA: Path = RUTA_API / "meteo"
ZONA_HORARIA: str = "Europe/Madrid"
UMBRAL_FREE_COOLING_C: float = 18.0
TAMANO_LOTE: int = 52  # todas las provincias de una vez

VARIABLES_DIARIAS: tuple[str, ...] = (
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "precipitation_sum",
    "wind_speed_10m_mean",
    "et0_fao_evapotranspiration",
)
NOMBRES_DIARIOS: dict[str, str] = {
    "temperature_2m_max": "tmax_c",
    "temperature_2m_min": "tmin_c",
    "temperature_2m_mean": "tmedia_c",
    "relative_humidity_2m_mean": "humedad_relativa_media_pct",
    "precipitation_sum": "precipitacion_mm",
    "wind_speed_10m_mean": "viento_medio_kmh",
    "et0_fao_evapotranspiration": "et0_mm",
}


def _coordenadas() -> tuple[list[str], list[str], list[str]]:
    """Códigos y coordenadas (lat, lon) de las capitales, en el orden de PROVINCIAS."""
    codigos = [p.codigo for p in PROVINCIAS]
    lats = [str(p.lat) for p in PROVINCIAS]
    lons = [str(p.lon) for p in PROVINCIAS]
    return codigos, lats, lons


def _series_por_ubicacion(respuesta: Any, bloque: str, etiqueta: str) -> list[dict]:
    """Open-Meteo devuelve un dict si hay una coordenada y una lista si hay varias."""
    if isinstance(respuesta, dict):
        respuesta = [respuesta]
    if not isinstance(respuesta, list) or len(respuesta) != len(PROVINCIAS):
        raise ErrorFuente(f"{etiqueta}: se esperaban {len(PROVINCIAS)} ubicaciones y llegaron otra cosa")
    for ubicacion in respuesta:
        if bloque not in ubicacion:
            raise ErrorFuente(f"{etiqueta}: falta el bloque '{bloque}' en la respuesta")
    return respuesta


def _pedir_anio(anio: int, horario: bool, fin: dt.date) -> list[dict]:
    """Pide un año (o hasta `fin`) para todas las capitales. Usa caché si el año está cerrado."""
    hoy = dt.date.today()
    cerrado = anio < hoy.year
    ruta = CARPETA / ("horario" if horario else "diario") / f"{anio}.json"
    cache = leer_cache_json(ruta) if cerrado else None
    if cache is not None:
        return cache
    _, lats, lons = _coordenadas()
    inicio = dt.date(anio, 1, 1)
    parametros: dict[str, Any] = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "start_date": inicio.isoformat(),
        "end_date": fin.isoformat(),
        "timezone": ZONA_HORARIA,
    }
    if horario:
        parametros["hourly"] = "temperature_2m"
        url = URL_ARCHIVO
    else:
        parametros["daily"] = ",".join(VARIABLES_DIARIAS)
        url = URL_ARCHIVO
    datos = json_de(url, params=parametros, etiqueta=f"{ETIQUETA} {'horario' if horario else 'diario'} {anio}")
    datos = _series_por_ubicacion(datos, "hourly" if horario else "daily", f"{ETIQUETA} {anio}")
    guardar_cache_json(ruta, datos)
    registrar(
        "Open-Meteo",
        f"Archivo {'horario' if horario else 'diario'} ERA5 {anio} (52 capitales)",
        url,
        ruta,
        ruta.stat().st_size / 1024,
    )
    return datos


def clima_diario(anio_inicio: int = 2015, anio_fin: int | None = None) -> pd.DataFrame:
    """Clima diario por provincia (ERA5) entre dos años, hasta ayer.

    Returns:
        DataFrame largo: fecha, codigo_provincia, tmax_c, tmin_c, tmedia_c,
        humedad_relativa_media_pct, precipitacion_mm, viento_medio_kmh, et0_mm.
    """
    hoy = dt.date.today()
    fin_global = hoy - dt.timedelta(days=1)  # el archivo llega hasta ayer
    anio_fin = anio_fin or fin_global.year
    filas = []
    codigos, _, _ = _coordenadas()
    for anio in range(anio_inicio, anio_fin + 1):
        fin = min(dt.date(anio, 12, 31), fin_global)
        if fin < dt.date(anio, 1, 1):
            break
        for codigo, ubicacion in zip(codigos, _pedir_anio(anio, horario=False, fin=fin)):
            filas.extend(filas_diarias(ubicacion, codigo))
    tabla = pd.DataFrame(filas)
    return tabla.sort_values(["codigo_provincia", "fecha"]).reset_index(drop=True)


def filas_diarias(ubicacion: dict, codigo: str) -> list[dict]:
    """Filas diarias de una ubicación de Open-Meteo (bloque 'daily') con nombres del proyecto."""
    diario = ubicacion["daily"]
    filas = []
    for indice, dia in enumerate(diario["time"]):
        fila = {"fecha": pd.Timestamp(dia), "codigo_provincia": codigo}
        for variable, nombre in NOMBRES_DIARIOS.items():
            valores = diario.get(variable, [])
            fila[nombre] = valores[indice] if indice < len(valores) else None
        filas.append(fila)
    return filas


def free_cooling_mensual(anio_inicio: int = 2015, anio_fin: int | None = None) -> pd.DataFrame:
    """Horas mensuales con temperatura < 18 °C por provincia, desde la serie horaria ERA5.

    Returns:
        DataFrame: mes (inicio de mes), codigo_provincia, horas_free_cooling,
        horas_con_dato, pct_horas_free_cooling.
    """
    fin_global = dt.date.today() - dt.timedelta(days=1)
    anio_fin = anio_fin or fin_global.year
    codigos, _, _ = _coordenadas()
    partes = []
    for anio in range(anio_inicio, anio_fin + 1):
        fin = min(dt.date(anio, 12, 31), fin_global)
        if fin < dt.date(anio, 1, 1):
            break
        for codigo, ubicacion in zip(codigos, _pedir_anio(anio, horario=True, fin=fin)):
            partes.append(free_cooling_de_ubicacion(ubicacion, codigo))
    return _tabla_free_cooling(partes)


def free_cooling_de_ubicacion(ubicacion: dict, codigo: str) -> pd.DataFrame:
    """Horas con temperatura < 18 °C por mes para una ubicación (bloque 'hourly')."""
    horario = ubicacion["hourly"]
    serie = pd.DataFrame({"tiempo": pd.to_datetime(horario["time"]), "t": horario["temperature_2m"]})
    serie = serie.dropna(subset=["t"])
    serie["mes"] = serie["tiempo"].dt.to_period("M").dt.to_timestamp()
    serie["frio"] = serie["t"] < UMBRAL_FREE_COOLING_C
    agregado = serie.groupby("mes").agg(horas_free_cooling=("frio", "sum"), horas_con_dato=("frio", "size")).reset_index()
    agregado["codigo_provincia"] = codigo
    return agregado


def _tabla_free_cooling(partes: list[pd.DataFrame]) -> pd.DataFrame:
    columnas = ["mes", "codigo_provincia", "horas_free_cooling", "horas_con_dato", "pct_horas_free_cooling"]
    if not partes:
        return pd.DataFrame(columns=columnas)
    tabla = pd.concat(partes, ignore_index=True)
    tabla["horas_free_cooling"] = tabla["horas_free_cooling"].astype(int)
    tabla["pct_horas_free_cooling"] = (100 * tabla["horas_free_cooling"] / tabla["horas_con_dato"]).round(2)
    return tabla[columnas].sort_values(["codigo_provincia", "mes"]).reset_index(drop=True)


def clima_actual() -> pd.DataFrame:
    """Tiempo actual en cada capital (Open-Meteo forecast, campo 'current'). Sin caché: es tiempo real.

    Returns:
        DataFrame: codigo_provincia, momento_observacion, temperatura_actual_c,
        humedad_relativa_actual_pct, viento_actual_kmh, precipitacion_actual_mm.
    """
    codigos, lats, lons = _coordenadas()
    parametros = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        "timezone": ZONA_HORARIA,
    }
    datos = json_de(URL_PREVISION, params=parametros, etiqueta=f"{ETIQUETA} tiempo actual")
    datos = _series_por_ubicacion(datos, "current", f"{ETIQUETA} actual")
    filas = []
    for codigo, ubicacion in zip(codigos, datos):
        actual = ubicacion["current"]
        filas.append(
            {
                "codigo_provincia": codigo,
                "momento_observacion": actual.get("time"),
                "temperatura_actual_c": actual.get("temperature_2m"),
                "humedad_relativa_actual_pct": actual.get("relative_humidity_2m"),
                "viento_actual_kmh": actual.get("wind_speed_10m"),
                "precipitacion_actual_mm": actual.get("precipitation"),
            }
        )
    return pd.DataFrame(filas)


def prevision_corta(dias: int = 7) -> pd.DataFrame:
    """Previsión de los próximos `dias` días en cada capital (Open-Meteo, una sola petición).

    Returns:
        DataFrame: codigo_provincia, temp_prevision_7d_media_c, temp_prevision_7d_max_c,
        precipitacion_prevision_7d_mm (medias y sumas de los días previstos).
    """
    codigos, lats, lons = _coordenadas()
    parametros = {
        "latitude": ",".join(lats),
        "longitude": ",".join(lons),
        "daily": "temperature_2m_mean,temperature_2m_max,precipitation_sum",
        "forecast_days": dias,
        "timezone": ZONA_HORARIA,
    }
    datos = json_de(URL_PREVISION, params=parametros, etiqueta=f"{ETIQUETA} previsión")
    datos = _series_por_ubicacion(datos, "daily", f"{ETIQUETA} previsión")
    filas = []
    for codigo, ubicacion in zip(codigos, datos):
        diario = ubicacion["daily"]
        medias = [v for v in diario.get("temperature_2m_mean", []) if v is not None]
        maximas = [v for v in diario.get("temperature_2m_max", []) if v is not None]
        lluvia = [v for v in diario.get("precipitation_sum", []) if v is not None]
        filas.append(
            {
                "codigo_provincia": codigo,
                "temp_prevision_7d_media_c": round(sum(medias) / len(medias), 2) if medias else None,
                "temp_prevision_7d_max_c": max(maximas) if maximas else None,
                "precipitacion_prevision_7d_mm": round(sum(lluvia), 2) if lluvia else None,
            }
        )
    return pd.DataFrame(filas)
