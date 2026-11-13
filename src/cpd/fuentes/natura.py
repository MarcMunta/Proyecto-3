"""Red Natura 2000: superficie de cada provincia incluida en espacios protegidos (EEA, ArcGIS REST).

Servicio: https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer/0
Estrategia (viable porque el servicio admite consultas por envolvente):
1. Para cada provincia se pide, con su caja envolvente, los espacios que la intersecan
   (geometría simplificada en servidor y paginada).
2. Se recorta cada espacio con el polígono provincial y se suma la superficie unida.
3. El porcentaje se calcula en un plano aproximado de igual área (x escalada por cos(latitud)).

Resultado cacheado por provincia en data/raw/api/natura/ (la red cambia muy poco).
Un espacio Natura 2000 puede ser SCI, ZEC o ZEPA: se cuentan todos (criterio de la fuente).
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from shapely import affinity
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, leer_cache_json, registrar
from cpd.fuentes.provincias import PROVINCIAS

FUENTE: str = "EEA Natura 2000"
URL_CONSULTA: str = (
    "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer/0/query"
)
CARPETA: Path = RUTA_API / "natura"
TAMANO_PAGINA: int = 500
TOLERANCIA_GRADOS: float = 0.0005  # simplificación en servidor (~50 m)


def _parametros(envolvente: tuple[float, float, float, float], extra: dict | None = None) -> dict:
    xmin, ymin, xmax, ymax = envolvente
    parametros = {
        "where": "1=1",
        "geometry": f"{xmin},{ymin},{xmax},{ymax}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "SITECODE",
        "returnGeometry": "true",
        "maxAllowableOffset": TOLERANCIA_GRADOS,
        "f": "json",
    }
    parametros.update(extra or {})
    return parametros


def _anillos_a_geometria(anillos: list[list[list[float]]]) -> BaseGeometry | None:
    """Convierte los anillos de un polígono ESRI en geometría shapely (los agujeros se restan por paridad)."""
    if not anillos:
        return None
    poligonos = []
    for anillo in anillos:
        if len(anillo) >= 4:
            poligonos.append(Polygon(anillo))
    if not poligonos:
        return None
    return unary_union([p.buffer(0) for p in poligonos])


def _espacios_intersecados(envolvente: tuple[float, float, float, float]) -> list[BaseGeometry]:
    """Geometrías de los espacios Natura 2000 que intersecan una envolvente (paginado)."""
    total = json_de(URL_CONSULTA, params=_parametros(envolvente, {"returnCountOnly": "true"}), etiqueta=FUENTE)
    if "error" in total:
        raise ErrorFuente(f"{FUENTE}: {total['error'].get('message', 'error')}")
    geometrias: list[BaseGeometry] = []
    desplazamiento = 0
    while True:
        datos = json_de(
            URL_CONSULTA,
            params=_parametros(envolvente, {"resultOffset": desplazamiento, "resultRecordCount": TAMANO_PAGINA}),
            etiqueta=FUENTE,
        )
        if "error" in datos:
            raise ErrorFuente(f"{FUENTE}: {datos['error'].get('message', 'error')}")
        for entidad in datos.get("features", []):
            geometria = _anillos_a_geometria(entidad.get("geometry", {}).get("rings", []))
            if geometria is not None and not geometria.is_empty:
                geometrias.append(geometria)
        desplazamiento += len(datos.get("features", []))
        if not datos.get("exceededTransferLimit") or not datos.get("features"):
            break
    return geometrias


def _escala_area(geometria: BaseGeometry, latitud: float) -> float:
    """Área aproximada en km² con x escalada por cos(latitud): suficiente para proporciones."""
    factor = math.cos(math.radians(latitud))

    return affinity.scale(geometria, xfact=factor, yfact=1.0, origin=(0, 0)).area * 111.32 * 110.57


def superficie_natura_por_provincia(poligonos: dict[str, BaseGeometry]) -> pd.DataFrame:
    """Porcentaje de la superficie provincial que es Red Natura 2000.

    Returns:
        DataFrame: codigo_provincia, pct_superficie_natura2000, espacios_natura_2000.
    """
    filas = []
    for provincia in PROVINCIAS:
        ruta = CARPETA / f"{provincia.codigo}.json"
        cache = leer_cache_json(ruta)
        if cache is None:
            poligono = poligonos.get(provincia.codigo)
            if poligono is None:
                raise ErrorFuente(f"{FUENTE}: falta el polígono de la provincia {provincia.codigo}")
            geometrias = _espacios_intersecados(tuple(poligono.bounds))
            if geometrias:
                unido = unary_union(geometrias).buffer(0)
                recorte = unido.intersection(poligono)
            else:
                recorte = Polygon()
            lat_media = (poligono.bounds[1] + poligono.bounds[3]) / 2
            area_prov = _escala_area(poligono, lat_media)
            area_natura = _escala_area(recorte, lat_media) if not recorte.is_empty else 0.0
            cache = {
                "codigo_provincia": provincia.codigo,
                "pct_superficie_natura2000": round(100 * area_natura / area_prov, 2) if area_prov else None,
                "espacios_natura_2000": sum(1 for g in geometrias if g.intersects(poligono)),
            }
            guardar_cache_json(ruta, cache)
            registrar(FUENTE, f"Espacios Natura 2000 intersecados con {provincia.nombre}", URL_CONSULTA, ruta, 1)
        filas.append(cache)
    return pd.DataFrame(filas, columns=["codigo_provincia", "pct_superficie_natura2000", "espacios_natura_2000"])


