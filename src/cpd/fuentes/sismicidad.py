"""Sismicidad: terremotos de la zona de España desde el servicio FDSN del EMSC, asignados a provincias.

Servicio: https://www.seismicportal.eu/fdsnws/event/1/query (JSON, sin clave, tiempo real e histórico).
Se pide un año por petición dentro de una caja que cubre la península, Baleares, Canarias,
Ceuta y Melilla con margen. Los eventos fuera de cualquier polígono provincial (mar, Portugal,
Marruecos, Argelia...) se cuentan aparte y no se asignan.

Magnitud mínima descargada: 1.5 (el catálogo es más completo a partir de ~2.5 en el área).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from shapely.geometry.base import BaseGeometry

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, leer_cache_json, registrar
from cpd.fuentes.provincias import provincia_de_punto

FUENTE: str = "EMSC (FDSN)"
URL: str = "https://www.seismicportal.eu/fdsnws/event/1/query"
CARPETA: Path = RUTA_API / "emsc_v2"  # v2: filtra eventos al año pedido (la v1 duplicaba el 1 de enero)
CAJA: dict[str, float] = {"minlat": 27.0, "maxlat": 44.8, "minlon": -19.0, "maxlon": 5.0}
MAGNITUD_MINIMA: float = 1.5
LIMITE_EVENTOS: int = 20000


def _descargar_anio(anio: int) -> list[dict]:
    """Eventos de un año dentro de la caja (caché si el año está cerrado)."""
    hoy = dt.date.today()
    ruta = CARPETA / f"{anio}.json"
    if anio < hoy.year and (cache := leer_cache_json(ruta)) is not None:
        return cache
    parametros = {
        "format": "json",
        "starttime": f"{anio}-01-01",
        "endtime": f"{anio + 1}-01-01" if anio < hoy.year else (hoy + dt.timedelta(days=1)).isoformat(),
        "minmagnitude": MAGNITUD_MINIMA,
        "limit": LIMITE_EVENTOS,
        **CAJA,
    }
    datos = json_de(URL, params=parametros, etiqueta=f"{FUENTE} {anio}", reintentos=4)
    if not isinstance(datos, dict) or "features" not in datos:
        raise ErrorFuente(f"{FUENTE}: respuesta inesperada para {anio}")
    eventos = [
        {
            "id": f["properties"].get("unid"),
            "tiempo": f["properties"].get("time"),
            "lat": f["geometry"]["coordinates"][1],
            "lon": f["geometry"]["coordinates"][0],
            "magnitud": f["properties"].get("mag"),
        }
        for f in datos["features"]
    ]
    # El filtro por fechas es inclusivo: los eventos del 1 de enero del año siguiente se descartan aquí
    eventos = [e for e in eventos if str(e["tiempo"])[:4] == str(anio)]
    guardar_cache_json(ruta, eventos)
    registrar(FUENTE, f"Terremotos M>={MAGNITUD_MINIMA} {anio}", URL, ruta, ruta.stat().st_size / 1024)
    return eventos


def terremotos(anio_inicio: int = 2015, anio_fin: int | None = None) -> pd.DataFrame:
    """Eventos sísmicos en la caja de España entre dos años (incluidos)."""
    anio_fin = anio_fin or dt.date.today().year
    filas = []
    for anio in range(anio_inicio, anio_fin + 1):
        filas.extend(_descargar_anio(anio))
    tabla = pd.DataFrame(filas, columns=["id", "tiempo", "lat", "lon", "magnitud"]).drop_duplicates("id")
    if not tabla.empty:
        tabla["anio"] = pd.to_datetime(tabla["tiempo"], utc=True).dt.year
    return tabla


def sismos_por_provincia_anual(eventos: pd.DataFrame, poligonos: dict[str, BaseGeometry]) -> pd.DataFrame:
    """Nº de terremotos y magnitud máxima por provincia y año (solo eventos dentro de la provincia).

    Returns:
        DataFrame: codigo_provincia, anio, n_terremotos, magnitud_max, n_terremotos_m3_plus.
    """
    columnas = ["codigo_provincia", "anio", "n_terremotos", "magnitud_max", "n_terremotos_m3_plus"]
    if eventos.empty:
        return pd.DataFrame(columns=columnas)
    eventos = eventos.copy()
    eventos["codigo_provincia"] = [provincia_de_punto(la, lo, poligonos) for la, lo in zip(eventos["lat"], eventos["lon"])]
    dentro = eventos.dropna(subset=["codigo_provincia"])
    if dentro.empty:
        return pd.DataFrame(columns=columnas)
    agregado = dentro.groupby(["codigo_provincia", "anio"]).agg(
        n_terremotos=("id", "size"),
        magnitud_max=("magnitud", "max"),
        n_terremotos_m3_plus=("magnitud", lambda m: int((m >= 3.0).sum())),
    )
    return agregado.reset_index()[columnas]
