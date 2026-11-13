"""Las 52 provincias españolas (INE 01-52): nombres, CCAA, puntos y polígonos.

Los polígonos provinciales se obtienen disolviendo los polígonos municipales de
Eurostat GISCO (LAU 2024) por los dos primeros dígitos del código INE del municipio
(``GISCO_ID`` = "ES_" + código INE de 5 dígitos). El resultado se cachea en
``data/raw/api/provincias/poligonos_provincias.geojson``.

Los puntos representativos son la capital de provincia (coordenadas aproximadas,
suficientes para clima y distancias a escala provincial).
"""

from __future__ import annotations

import io
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import shapefile
from shapely.geometry import Point, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from cpd.config import RUTA_RAW
from cpd.fuentes.http import RUTA_API, ErrorFuente, descargar_archivo

FUENTE_GISCO: str = "Eurostat GISCO"
URL_GISCO_LAU: str = "https://gisco-services.ec.europa.eu/distribution/v2/lau/shp/LAU_RG_01M_2024_4326.shp.zip"
RUTA_ZIP_GISCO: Path = RUTA_RAW / "municipios" / "gisco_lau_2024_4326.shp.zip"
RUTA_POLIGONOS: Path = RUTA_API / "provincias" / "poligonos_provincias.geojson"
TOLERANCIA_SIMPLIFICACION_GRADOS: float = 0.002  # ~200 m: suficiente para asignar puntos


@dataclass(frozen=True)
class Provincia:
    """Ficha de una provincia."""

    codigo: str  # INE de dos dígitos, "01".."52"
    nombre: str
    nombre_ine: str  # nombre tal como aparece en las tablas del INE (para emparejar)
    ccaa_codigo: str  # INE de dos dígitos de la comunidad autónoma
    ccaa: str
    ree_geo_id: int  # identificador de la CCAA en la API de REData
    lat: float  # punto representativo (capital)
    lon: float


CCAA_INE: dict[str, str] = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Illes Balears", "05": "Canarias",
    "06": "Cantabria", "07": "Castilla y León", "08": "Castilla-La Mancha", "09": "Cataluña",
    "10": "Comunitat Valenciana", "11": "Extremadura", "12": "Galicia", "13": "Madrid",
    "14": "Región de Murcia", "15": "Comunidad Foral de Navarra", "16": "País Vasco", "17": "La Rioja",
    "18": "Ceuta", "19": "Melilla",
}

# Identificadores de comunidad en la API de REData (geo_ids de geo_limit=ccaa)
REE_GEO_ID_CCAA: dict[str, int] = {
    "01": 4, "02": 5, "03": 11, "04": 8743, "05": 8742, "06": 6, "07": 8, "08": 7, "09": 9,
    "10": 15, "11": 16, "12": 17, "13": 13, "14": 21, "15": 14, "16": 10, "17": 20, "18": 8744, "19": 8745,
}

PROVINCIAS: tuple[Provincia, ...] = (
    Provincia("01", "Araba/Álava", "Araba/Álava", "16", CCAA_INE["16"], REE_GEO_ID_CCAA["16"], 42.85, -2.67),
    Provincia("02", "Albacete", "Albacete", "08", CCAA_INE["08"], REE_GEO_ID_CCAA["08"], 39.00, -1.86),
    Provincia("03", "Alicante/Alacant", "Alicante/Alacant", "10", CCAA_INE["10"], REE_GEO_ID_CCAA["10"], 38.35, -0.48),
    Provincia("04", "Almería", "Almería", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 36.84, -2.46),
    Provincia("05", "Ávila", "Ávila", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 40.66, -4.70),
    Provincia("06", "Badajoz", "Badajoz", "11", CCAA_INE["11"], REE_GEO_ID_CCAA["11"], 38.88, -6.97),
    Provincia("07", "Balears, Illes", "Balears, Illes", "04", CCAA_INE["04"], REE_GEO_ID_CCAA["04"], 39.57, 2.65),
    Provincia("08", "Barcelona", "Barcelona", "09", CCAA_INE["09"], REE_GEO_ID_CCAA["09"], 41.39, 2.17),
    Provincia("09", "Burgos", "Burgos", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 42.34, -3.70),
    Provincia("10", "Cáceres", "Cáceres", "11", CCAA_INE["11"], REE_GEO_ID_CCAA["11"], 39.47, -6.37),
    Provincia("11", "Cádiz", "Cádiz", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 36.53, -6.29),
    Provincia("12", "Castellón/Castelló", "Castellón/Castelló", "10", CCAA_INE["10"], REE_GEO_ID_CCAA["10"], 39.99, -0.05),
    Provincia("13", "Ciudad Real", "Ciudad Real", "08", CCAA_INE["08"], REE_GEO_ID_CCAA["08"], 38.99, -3.93),
    Provincia("14", "Córdoba", "Córdoba", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 37.89, -4.78),
    Provincia("15", "Coruña, A", "Coruña, A", "12", CCAA_INE["12"], REE_GEO_ID_CCAA["12"], 43.37, -8.40),
    Provincia("16", "Cuenca", "Cuenca", "08", CCAA_INE["08"], REE_GEO_ID_CCAA["08"], 40.07, -2.13),
    Provincia("17", "Girona", "Girona", "09", CCAA_INE["09"], REE_GEO_ID_CCAA["09"], 41.98, 2.82),
    Provincia("18", "Granada", "Granada", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 37.18, -3.60),
    Provincia("19", "Guadalajara", "Guadalajara", "08", CCAA_INE["08"], REE_GEO_ID_CCAA["08"], 40.63, -3.17),
    Provincia("20", "Gipuzkoa", "Gipuzkoa", "16", CCAA_INE["16"], REE_GEO_ID_CCAA["16"], 43.31, -1.98),
    Provincia("21", "Huelva", "Huelva", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 37.26, -6.95),
    Provincia("22", "Huesca", "Huesca", "02", CCAA_INE["02"], REE_GEO_ID_CCAA["02"], 42.14, -0.41),
    Provincia("23", "Jaén", "Jaén", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 37.78, -3.78),
    Provincia("24", "León", "León", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 42.60, -5.57),
    Provincia("25", "Lleida", "Lleida", "09", CCAA_INE["09"], REE_GEO_ID_CCAA["09"], 41.62, 0.62),
    Provincia("26", "Rioja, La", "Rioja, La", "17", CCAA_INE["17"], REE_GEO_ID_CCAA["17"], 42.47, -2.45),
    Provincia("27", "Lugo", "Lugo", "12", CCAA_INE["12"], REE_GEO_ID_CCAA["12"], 43.01, -7.56),
    Provincia("28", "Madrid", "Madrid", "13", CCAA_INE["13"], REE_GEO_ID_CCAA["13"], 40.42, -3.70),
    Provincia("29", "Málaga", "Málaga", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 36.72, -4.42),
    Provincia("30", "Murcia", "Murcia", "14", CCAA_INE["14"], REE_GEO_ID_CCAA["14"], 37.98, -1.13),
    Provincia("31", "Navarra", "Navarra", "15", CCAA_INE["15"], REE_GEO_ID_CCAA["15"], 42.82, -1.64),
    Provincia("32", "Ourense", "Ourense", "12", CCAA_INE["12"], REE_GEO_ID_CCAA["12"], 42.34, -7.86),
    Provincia("33", "Asturias", "Asturias", "03", CCAA_INE["03"], REE_GEO_ID_CCAA["03"], 43.36, -5.85),
    Provincia("34", "Palencia", "Palencia", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 42.01, -4.53),
    Provincia("35", "Palmas, Las", "Palmas, Las", "05", CCAA_INE["05"], REE_GEO_ID_CCAA["05"], 28.10, -15.41),
    Provincia("36", "Pontevedra", "Pontevedra", "12", CCAA_INE["12"], REE_GEO_ID_CCAA["12"], 42.43, -8.65),
    Provincia("37", "Salamanca", "Salamanca", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 40.97, -5.66),
    Provincia("38", "Santa Cruz de Tenerife", "Santa Cruz de Tenerife", "05", CCAA_INE["05"], REE_GEO_ID_CCAA["05"], 28.47, -16.25),
    Provincia("39", "Cantabria", "Cantabria", "06", CCAA_INE["06"], REE_GEO_ID_CCAA["06"], 43.46, -3.80),
    Provincia("40", "Segovia", "Segovia", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 40.95, -4.12),
    Provincia("41", "Sevilla", "Sevilla", "01", CCAA_INE["01"], REE_GEO_ID_CCAA["01"], 37.39, -5.98),
    Provincia("42", "Soria", "Soria", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 41.76, -2.47),
    Provincia("43", "Tarragona", "Tarragona", "09", CCAA_INE["09"], REE_GEO_ID_CCAA["09"], 41.12, 1.25),
    Provincia("44", "Teruel", "Teruel", "02", CCAA_INE["02"], REE_GEO_ID_CCAA["02"], 40.35, -1.11),
    Provincia("45", "Toledo", "Toledo", "08", CCAA_INE["08"], REE_GEO_ID_CCAA["08"], 39.86, -4.02),
    Provincia("46", "Valencia/València", "Valencia/València", "10", CCAA_INE["10"], REE_GEO_ID_CCAA["10"], 39.47, -0.38),
    Provincia("47", "Valladolid", "Valladolid", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 41.65, -4.72),
    Provincia("48", "Bizkaia", "Bizkaia", "16", CCAA_INE["16"], REE_GEO_ID_CCAA["16"], 43.26, -2.93),
    Provincia("49", "Zamora", "Zamora", "07", CCAA_INE["07"], REE_GEO_ID_CCAA["07"], 41.50, -5.75),
    Provincia("50", "Zaragoza", "Zaragoza", "02", CCAA_INE["02"], REE_GEO_ID_CCAA["02"], 41.65, -0.89),
    Provincia("51", "Ceuta", "Ceuta", "18", CCAA_INE["18"], REE_GEO_ID_CCAA["18"], 35.89, -5.32),
    Provincia("52", "Melilla", "Melilla", "19", CCAA_INE["19"], REE_GEO_ID_CCAA["19"], 35.29, -2.94),
)

CODIGOS: tuple[str, ...] = tuple(p.codigo for p in PROVINCIAS)
_POR_CODIGO: dict[str, Provincia] = {p.codigo: p for p in PROVINCIAS}


def ficha(codigo: str) -> Provincia:
    """Devuelve la ficha de una provincia por su código INE de dos dígitos."""
    if codigo not in _POR_CODIGO:
        raise KeyError(f"Código de provincia desconocido: {codigo!r}")
    return _POR_CODIGO[codigo]


def tabla_provincias() -> pd.DataFrame:
    """Tabla maestra de provincias (una fila por provincia)."""
    return pd.DataFrame(
        [
            {
                "codigo_provincia": p.codigo,
                "provincia": p.nombre,
                "codigo_ccaa": p.ccaa_codigo,
                "ccaa": p.ccaa,
                "ree_geo_id": p.ree_geo_id,
                "lat_punto": p.lat,
                "lon_punto": p.lon,
            }
            for p in PROVINCIAS
        ]
    )


def codigo_ccaa_de_provincia(codigo: str) -> str:
    """Código INE de la comunidad a la que pertenece una provincia."""
    return ficha(codigo).ccaa_codigo


def emparejar_nombre_ine(nombre_tabla: str) -> str | None:
    """Encuentra el código de provincia para un nombre de tabla INE (tolerante a caracteres rotos).

    Algunas tablas del INE traen tildes rotas (p. ej. "Almer\\ufffda"). Se compara
    quitando todo lo que no sea letra ASCII y se acepta la coincidencia más parecida.
    """
    import difflib
    import unicodedata

    def normalizar(texto: str) -> str:
        sin_tildes = unicodedata.normalize("NFKD", texto.replace("�", "?"))
        solo_ascii = sin_tildes.encode("ascii", "ignore").decode("ascii")
        return "".join(ch for ch in solo_ascii.lower() if ch.isalpha())

    objetivo = normalizar(nombre_tabla)
    candidatos = {normalizar(p.nombre_ine): p.codigo for p in PROVINCIAS}
    for nombre_normalizado, codigo in candidatos.items():
        if nombre_normalizado == objetivo:
            return codigo
    mejor = difflib.get_close_matches(objetivo, list(candidatos), n=1, cutoff=0.8)
    return candidatos[mejor[0]] if mejor else None


def construir_poligonos(ruta_zip: Path = RUTA_ZIP_GISCO) -> dict[str, BaseGeometry]:
    """Disuelve los municipios de GISCO por provincia. Devuelve {codigo: geometría WGS84}.

    Raises:
        ErrorFuente: si el zip no existe y no se puede descargar, o no contiene España.
    """
    if not ruta_zip.exists():
        descargar_archivo(URL_GISCO_LAU, ruta_zip, FUENTE_GISCO, "Límites municipales LAU 2024 (polígonos)")
    with zipfile.ZipFile(ruta_zip) as zf:
        base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
        lector = shapefile.Reader(
            shp=io.BytesIO(zf.read(base + ".shp")),
            dbf=io.BytesIO(zf.read(base + ".dbf")),
            encoding="utf-8",
        )
        grupos: dict[str, list[BaseGeometry]] = defaultdict(list)
        for registro, forma in zip(lector.iterRecords(), lector.iterShapes()):
            identificador = registro["GISCO_ID"]
            if not identificador.startswith("ES_"):
                continue
            codigo_municipio = identificador[3:]
            grupos[codigo_municipio[:2]].append(shape(forma.__geo_interface__))
    if not grupos:
        raise ErrorFuente("GISCO: no se han encontrado municipios españoles (GISCO_ID 'ES_...')")
    poligonos = {}
    for codigo, geometrias in grupos.items():
        disuelto = unary_union(geometrias).buffer(0)
        poligonos[codigo] = disuelto.simplify(TOLERANCIA_SIMPLIFICACION_GRADOS, preserve_topology=True)
    return poligonos


def guardar_poligonos(poligonos: dict[str, BaseGeometry], ruta: Path = RUTA_POLIGONOS) -> None:
    """Escribe los polígonos provinciales como GeoJSON (una Feature por provincia)."""
    import json

    ruta.parent.mkdir(parents=True, exist_ok=True)
    elementos = []
    for codigo in sorted(poligonos):
        elementos.append(
            {
                "type": "Feature",
                "properties": {"codigo_provincia": codigo, "provincia": ficha(codigo).nombre},
                "geometry": mapping(poligonos[codigo]),
            }
        )
    ruta.write_text(json.dumps({"type": "FeatureCollection", "features": elementos}), encoding="utf-8")


def cargar_poligonos(ruta: Path = RUTA_POLIGONOS) -> dict[str, BaseGeometry]:
    """Lee los polígonos provinciales del GeoJSON cacheado; si no existe, los construye y guarda."""
    import json

    if not ruta.exists():
        poligonos = construir_poligonos()
        guardar_poligonos(poligonos, ruta)
        return poligonos
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {f["properties"]["codigo_provincia"]: shape(f["geometry"]) for f in datos["features"]}


def provincia_de_punto(lat: float, lon: float, poligonos: dict[str, BaseGeometry]) -> str | None:
    """Código de la provincia que contiene el punto, o None si cae fuera de España (mar, Portugal...)."""
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return None
    punto = Point(float(lon), float(lat))
    for codigo, geometria in poligonos.items():
        if geometria.contains(punto):
            return codigo
    return None


def asignar_provincias(puntos: Iterable[tuple[float, float]], poligonos: dict[str, BaseGeometry]) -> list[str | None]:
    """Asigna a cada par (lat, lon) su provincia (o None)."""
    return [provincia_de_punto(lat, lon, poligonos) for lat, lon in puntos]
