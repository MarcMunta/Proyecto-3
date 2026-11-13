"""INE: población y renta por provincia desde la API Tempus3 (JSON, sin clave).

Base: https://servicios.ine.es/wstempus/js/ES/
- DATOS_TABLA/2852: población residente por provincias y sexo (anual, series "Provincia. Sexo. ...").
- DATOS_TABLA/53689: renta neta media por persona y hogar y mediana de la renta por unidad de consumo,
  por total nacional, CCAA y provincia (ADRH, serie 2015-2024). Nombres "Territorio. Dato base. Métrica."

Los nombres vienen con caracteres rotos en algunas tablas; se emparejan con
``provincias.emparejar_nombre_ine``. Las series que no corresponden a una provincia se descartan.
"""

from __future__ import annotations

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, registrar
from cpd.fuentes.provincias import emparejar_nombre_ine

URL_BASE: str = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/"
ETIQUETA: str = "INE"
TABLA_POBLACION: int = 2852
TABLA_RENTA: int = 53689
METRICAS_RENTA: dict[str, str] = {
    "Renta neta media por persona": "renta_neta_media_persona_eur",
    "Renta neta media por hogar": "renta_neta_media_hogar_eur",
    "Mediana de la renta por unidad de consumo": "mediana_renta_unidad_consumo_eur",
}


def _partes(nombre: str) -> list[str]:
    """Trocea un nombre de serie INE 'Territorio. Atributo. Métrica. Unidad.' en sus partes."""
    return [p.strip() for p in nombre.split(".") if p.strip() != ""]


def _tabla(numero: int, nult: int) -> list[dict]:
    """Descarga las últimas `nult` observaciones de todas las series de una tabla."""
    datos = json_de(f"{URL_BASE}{numero}", params={"nult": nult, "det": 0}, etiqueta=f"{ETIQUETA} tabla {numero}")
    if not isinstance(datos, list) or not datos:
        raise ErrorFuente(f"{ETIQUETA}: la tabla {numero} no devuelve series")
    guardar_cache_json(RUTA_API / "ine" / f"tabla_{numero}.json", datos)
    registrar("INE (Tempus3 API)", f"Tabla {numero}", f"{URL_BASE}{numero}", RUTA_API / "ine" / f"tabla_{numero}.json",
              (RUTA_API / "ine" / f"tabla_{numero}.json").stat().st_size / 1024)
    return datos


def poblacion_provincias(nult: int = 40) -> pd.DataFrame:
    """Población residente a 1 de enero por provincia (total de sexos), anual.

    Returns:
        DataFrame: codigo_provincia, anio, poblacion.
    """
    return poblacion_desde_series(_tabla(TABLA_POBLACION, nult))


def poblacion_desde_series(series: list[dict]) -> pd.DataFrame:
    """Interpreta las series de la tabla 2852 (población por provincia y sexo)."""
    filas = []
    for serie in series:
        partes = _partes(serie["Nombre"])
        if len(partes) < 2 or partes[1] != "Total":
            continue
        codigo = emparejar_nombre_ine(partes[0])
        if codigo is None:
            continue  # total nacional o comunidad
        for observacion in serie.get("Data", []):
            if observacion.get("Valor") is None or observacion.get("Secreto"):
                continue
            filas.append({"codigo_provincia": codigo, "anio": int(observacion["Anyo"]), "poblacion": float(observacion["Valor"])})
    tabla = pd.DataFrame(filas, columns=["codigo_provincia", "anio", "poblacion"])
    return tabla.drop_duplicates(["codigo_provincia", "anio"]).sort_values(["codigo_provincia", "anio"]).reset_index(drop=True)


def renta_provincias(nult: int = 40) -> pd.DataFrame:
    """Renta anual por provincia (€): renta neta media por persona y por hogar, mediana por unidad de consumo.

    Returns:
        DataFrame: codigo_provincia, anio, renta_neta_media_persona_eur,
        renta_neta_media_hogar_eur, mediana_renta_unidad_consumo_eur.
    """
    return renta_desde_series(_tabla(TABLA_RENTA, nult))


def renta_desde_series(series: list[dict]) -> pd.DataFrame:
    """Interpreta las series de la tabla 53689 (renta por territorio y métrica) y se queda con las provincias."""
    registros: dict[tuple[str, int], dict] = {}
    for serie in series:
        partes = _partes(serie["Nombre"])
        if len(partes) < 3 or partes[1] != "Dato base" or partes[2] not in METRICAS_RENTA:
            continue
        codigo = emparejar_nombre_ine(partes[0])
        if codigo is None:
            continue
        columna = METRICAS_RENTA[partes[2]]
        for observacion in serie.get("Data", []):
            if observacion.get("Valor") is None or observacion.get("Secreto"):
                continue
            clave = (codigo, int(observacion["Anyo"]))
            registros.setdefault(clave, {"codigo_provincia": codigo, "anio": clave[1]})[columna] = float(observacion["Valor"])
    columnas = ["codigo_provincia", "anio", *METRICAS_RENTA.values()]
    tabla = pd.DataFrame(list(registros.values()), columns=columnas)
    return tabla.sort_values(["codigo_provincia", "anio"]).reset_index(drop=True)
