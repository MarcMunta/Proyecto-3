"""PeeringDB: centros de datos (facilities) e IXP de España, asignados a provincias.

API pública: https://www.peeringdb.com/api/fac?country=ES  y  https://www.peeringdb.com/api/ix?country=ES
Límite anónimo por minuto: se espacian las peticiones y se cachea la respuesta.

Asignación a provincia:
- Centros de datos: por coordenadas (latitude/longitude) dentro del polígono provincial;
  si no tienen coordenadas se usa la ciudad.
- IXP: PeeringDB no publica coordenadas del IXP; se asigna por su ciudad (nombre de
  provincia o ciudad conocida). Los IXP sin ciudad reconocible quedan sin provincia.
"""

from __future__ import annotations

import math
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry.base import BaseGeometry

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, leer_cache_json, registrar
from cpd.fuentes.provincias import PROVINCIAS, emparejar_nombre_ine, ficha, provincia_de_punto

FUENTE: str = "PeeringDB"
CARPETA: Path = RUTA_API / "peeringdb"
URL_FAC: str = "https://www.peeringdb.com/api/fac"
URL_IX: str = "https://www.peeringdb.com/api/ix"

# Ciudades habituales de centros de datos e IXP que no coinciden con el nombre de la provincia.
CIUDAD_PROVINCIA: dict[str, str] = {
    "madrid": "28", "barcelona": "08", "valencia": "46", "bilbao": "48", "sevilla": "41", "seville": "41",
    "malaga": "29", "zaragoza": "50", "palma": "07", "palma de mallorca": "07", "las palmas": "35",
    "las palmas de gran canaria": "35", "santa cruz de tenerife": "38", "tenerife": "38", "vigo": "36",
    "a coruna": "15", "coruna": "15", "santiago de compostela": "15", "murcia": "30", "valladolid": "47",
    "girona": "17", "gerona": "17", "tarragona": "43", "leon": "24", "alicante": "03", "castello": "12",
    "castellon": "12", "pamplona": "31", "vitoria": "01", "vitoria-gasteiz": "01", "gijon": "33",
    "oviedo": "33", "san sebastian": "20", "donostia": "20", "hospitalet": "08", "badalona": "08",
    "terrassa": "08", "sabadell": "08", "cartagena": "30", "almeria": "04", "granada": "18", "cordoba": "14",
    "cadiz": "11", "jerez": "11", "huelva": "21", "jaen": "23", "salamanca": "37", "burgos": "09",
    "logrono": "26", "toledo": "45", "albacete": "02", "badajoz": "06", "caceres": "10", "ceuta": "51",
    "melilla": "52", "santander": "39", "huesca": "22", "lleida": "25", "lerida": "25", "ourense": "32",
    "lugo": "27", "pontevedra": "36", "ferrol": "15", "alcala de henares": "28", "getafe": "28",
    "leganes": "28", "rivas-vaciamadrid": "28", "majadahonda": "28", "alcobendas": "28", "tres cantos": "28",
    "san fernando de henares": "28", "coslada": "28", "pozuelo de alarcon": "28",
}


def _normalizar(texto: str | None) -> str:
    if not texto:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return sin_tildes.encode("ascii", "ignore").decode("ascii").lower().strip()


def provincia_de_ciudad(ciudad: str | None) -> str | None:
    """Provincia de una ciudad (por nombre de provincia o tabla de ciudades conocidas)."""
    nombre = _normalizar(ciudad)
    if not nombre:
        return None
    if nombre in CIUDAD_PROVINCIA:
        return CIUDAD_PROVINCIA[nombre]
    return emparejar_nombre_ine(ciudad or "")


def _descargar(url: str, nombre: str) -> list[dict[str, Any]]:
    """Descarga un endpoint de PeeringDB (lista 'data') con caché de la última respuesta."""
    ruta = CARPETA / f"{nombre}_ES.json"
    datos = json_de(url, params={"country": "ES"}, etiqueta=f"{FUENTE} {nombre}", reintentos=4)
    if not isinstance(datos, dict) or "data" not in datos:
        cache = leer_cache_json(ruta)
        if cache is not None:
            return cache
        raise ErrorFuente(f"{FUENTE}: respuesta inesperada para {nombre}")
    guardar_cache_json(ruta, datos["data"])
    registrar(FUENTE, f"Listado {nombre} España", url, ruta, ruta.stat().st_size / 1024)
    return datos["data"]


def centros_de_datos() -> pd.DataFrame:
    """Centros de datos (PeeringDB 'fac') de España con su provincia.

    Returns:
        DataFrame: id, nombre, ciudad, lat, lon, provincia (código o None), redes, ixp.
    """
    return _leer_fac(_descargar(URL_FAC, "fac"))


def _leer_fac(registros: list[dict[str, Any]]) -> pd.DataFrame:
    filas = []
    for fila in registros:
        lat, lon = fila.get("latitude"), fila.get("longitude")
        filas.append(
            {
                "id": fila.get("id"),
                "nombre": fila.get("name"),
                "ciudad": fila.get("city"),
                "lat": lat,
                "lon": lon,
                "redes": fila.get("net_count"),
                "ixp": fila.get("ix_count"),
            }
        )
    return pd.DataFrame(filas, columns=["id", "nombre", "ciudad", "lat", "lon", "redes", "ixp"])


def asignar_fac(tabla: pd.DataFrame, poligonos: dict[str, BaseGeometry]) -> pd.DataFrame:
    """Añade la columna codigo_provincia a los centros de datos (por coordenadas, o por ciudad)."""
    tabla = tabla.copy()
    codigos = []
    for _, fila in tabla.iterrows():
        codigo = None
        if pd.notna(fila["lat"]) and pd.notna(fila["lon"]):
            codigo = provincia_de_punto(float(fila["lat"]), float(fila["lon"]), poligonos)
        if codigo is None:
            codigo = provincia_de_ciudad(fila["ciudad"])
        codigos.append(codigo)
    tabla["codigo_provincia"] = codigos
    return tabla


def ixp() -> pd.DataFrame:
    """IXP de España con su provincia (por ciudad) y coordenadas de la ciudad cuando se conocen."""
    registros = _descargar(URL_IX, "ix")
    filas = []
    for fila in registros:
        ciudad = fila.get("city")
        codigo = provincia_de_ciudad(ciudad)
        filas.append({"id": fila.get("id"), "nombre": fila.get("name"), "ciudad": ciudad, "codigo_provincia": codigo})
    return pd.DataFrame(filas, columns=["id", "nombre", "ciudad", "codigo_provincia"])


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia de gran círculo (km) entre dos puntos WGS84 (fórmula de haversine)."""
    radio_tierra = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radio_tierra * math.asin(math.sqrt(a))


def resumen_por_provincia(fac: pd.DataFrame, ixps: pd.DataFrame) -> pd.DataFrame:
    """Una fila por provincia: nº de centros de datos, nº de IXP y distancia al IXP más cercano.

    La distancia se mide desde el punto representativo de la provincia (capital) hasta la
    capital de la provincia donde está cada IXP (aproximación: PeeringDB no da coordenadas del IXP).
    """
    puntos_ixp = {}
    for codigo in ixps["codigo_provincia"].dropna().unique():
        puntos_ixp[codigo] = (ficha(codigo).lat, ficha(codigo).lon)
    filas = []
    for provincia in PROVINCIAS:
        codigo = provincia.codigo
        n_fac = int((fac["codigo_provincia"] == codigo).sum()) if not fac.empty else 0
        n_ixp = int((ixps["codigo_provincia"] == codigo).sum()) if not ixps.empty else 0
        distancias = [
            distancia_km(provincia.lat, provincia.lon, lat, lon)
            for cod, (lat, lon) in puntos_ixp.items()
        ]
        filas.append(
            {
                "codigo_provincia": codigo,
                "n_centros_datos": n_fac,
                "n_ixp": n_ixp,
                "distancia_ixp_km": round(min(distancias), 1) if distancias else None,
            }
        )
    return pd.DataFrame(filas)
