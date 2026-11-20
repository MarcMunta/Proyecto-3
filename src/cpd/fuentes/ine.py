"""INE: población y renta por provincia desde la API Tempus3 (JSON, sin clave).

Base: https://servicios.ine.es/wstempus/js/ES/
- DATOS_TABLA/2852: población residente por provincias y sexo (anual, series "Provincia. Sexo. ...").
- DATOS_TABLA/53689: renta neta media por persona y hogar y mediana de la renta por unidad de consumo,
  por total nacional, CCAA y provincia (ADRH, serie 2015-2024). Nombres "Territorio. Dato base. Métrica."
- DATOS_TABLA/53447: agua de la red de abastecimiento público por comunidad (suministrada, registrada y distribuida,
  pérdidas), bienal, en miles de m³. Nombres "Comunidad, Indicador".

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


TABLA_AGUA: int = 53447
CCAA_AGUA: dict[str, str] = {
    "Andalucía": "01", "Aragón": "02", "Asturias": "03", "Balears": "04", "Canarias": "05", "Cantabria": "06",
    "Castilla y León": "07", "Castilla-La Mancha": "08", "Cataluña": "09", "Comunitat Valenciana": "10", "Extremadura": "11",
    "Galicia": "12", "Madrid": "13", "Murcia": "14", "Navarra": "15", "País Vasco": "16", "Rioja": "17", "Ceuta y Melilla": "18-19",
}
INDICADORES_AGUA: dict[str, str] = {
    "Volumen de agua suministrada a la red de abastecimiento público": "agua_suministrada_miles_m3",
    "1. Volumen total de agua registrada y distribuida por tipo de usuario": "agua_registrada_miles_m3",
    "2. Volumen de agua no registrada": "agua_no_registrada_miles_m3",
    "- Pérdidas reales": "perdidas_reales_miles_m3",
}


TABLA_PIB: int = 82284
# Nombres de la tabla de PIB que son solo comunidad (las uniprovinciales aparecen una vez y sí se usan).
SOLO_CCAA: frozenset[str] = frozenset(
    {"Total Nacional", "Andalucía", "Aragón", "Canarias", "Castilla y León", "Castilla - La Mancha", "Castilla-La Mancha",
     "Cataluña", "Comunitat Valenciana", "Extremadura", "Galicia", "País Vasco", "Extra-Regio"}
)


def pib_provincias(nult: int = 4) -> pd.DataFrame:
    """PIB a precios de mercado por provincia, precios corrientes (miles de €), Contabilidad Regional del INE
    (tabla 82284). Las comunidades uniprovinciales se toman de su fila de comunidad.

    Returns:
        DataFrame: codigo_provincia, anio, pib_miles_eur.
    """
    return pib_desde_series(_tabla(TABLA_PIB, nult))


def pib_desde_series(series: list[dict]) -> pd.DataFrame:
    """Interpreta las series «Territorio. Dato base. Producto interior bruto…» de la tabla 82284."""
    filas = []
    for serie in series:
        territorio, separador, _ = serie.get("Nombre", "").partition(". Dato base.")
        territorio = territorio.strip()
        if not separador or territorio in SOLO_CCAA:
            continue
        codigo = emparejar_nombre_ine(territorio) or emparejar_nombre_ine(territorio.split(",")[0])
        if codigo is None:
            continue
        for observacion in serie.get("Data", []):
            if observacion.get("Valor") is None or observacion.get("Secreto"):
                continue
            anio = int(observacion.get("Anyo") or str(observacion.get("NombrePeriodo", ""))[:4])
            filas.append({"codigo_provincia": codigo, "anio": anio, "pib_miles_eur": float(observacion["Valor"])})
    tabla = pd.DataFrame(filas, columns=["codigo_provincia", "anio", "pib_miles_eur"])
    return tabla.drop_duplicates(["codigo_provincia", "anio"]).sort_values(["codigo_provincia", "anio"]).reset_index(drop=True)


TABLA_SOCIEDADES: int = 6295


def sociedades_provincias(nult: int = 400) -> pd.DataFrame:
    """Sociedades mercantiles constituidas por provincia y mes (número), Estadística de Sociedades Mercantiles del INE
    (tabla 6295). Sirve para la atracción empresarial (E42).

    Returns:
        DataFrame: codigo_provincia, mes (primer día), sociedades_creadas.
    """
    return sociedades_desde_series(_tabla(TABLA_SOCIEDADES, nult))


def sociedades_desde_series(series: list[dict]) -> pd.DataFrame:
    """Interpreta las series «Provincia. Sociedades Constituídas. Mercantiles. Número de Sociedades.» de la tabla 6295."""
    filas = []
    for serie in series:
        partes = _partes(serie.get("Nombre", ""))
        if len(partes) < 4 or partes[1:4] != ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"]:
            continue
        codigo = None if partes[0] in SOLO_CCAA else emparejar_nombre_ine(partes[0])
        if codigo is None:
            continue
        for observacion in serie.get("Data", []):
            mes = observacion.get("FK_Periodo")
            if observacion.get("Valor") is None or observacion.get("Secreto") or not isinstance(mes, int) or not 1 <= mes <= 12:
                continue
            filas.append({"codigo_provincia": codigo, "mes": pd.Timestamp(int(observacion["Anyo"]), mes, 1), "sociedades_creadas": float(observacion["Valor"])})
    tabla = pd.DataFrame(filas, columns=["codigo_provincia", "mes", "sociedades_creadas"])
    return tabla.drop_duplicates(["codigo_provincia", "mes"]).sort_values(["codigo_provincia", "mes"]).reset_index(drop=True)


def agua_ccaa(nult: int = 6) -> pd.DataFrame:
    """Agua de la red de abastecimiento público por comunidad (miles de m³/año), «Estadística sobre el suministro y
    saneamiento del agua» del INE (tabla 53447, bienal). Ceuta y Melilla se publican juntas (código «18-19»).

    Returns:
        DataFrame: codigo_ccaa, ccaa, anio, agua_suministrada_miles_m3, agua_registrada_miles_m3,
        agua_no_registrada_miles_m3, perdidas_reales_miles_m3.
    """
    return agua_desde_series(_tabla(TABLA_AGUA, nult))


def agua_desde_series(series: list[dict]) -> pd.DataFrame:
    """Interpreta las series «Comunidad, Indicador» de la tabla 53447 (el año viene en `Anyo` o en `NombrePeriodo`)."""
    registros: dict[tuple[str, int], dict] = {}
    for serie in series:
        nombre = serie.get("Nombre", "").strip()
        # El territorio puede llevar coma («Asturias, Principado de»): el indicador se busca por el final del nombre.
        indicador = next((i for i in INDICADORES_AGUA if nombre.endswith(", " + i)), None)
        if indicador is None:
            continue  # indicador no usado
        territorio = nombre[: -len(indicador) - 2].split(",")[0].strip()
        codigo, columna = CCAA_AGUA.get(territorio), INDICADORES_AGUA[indicador]
        if codigo is None:
            continue  # total nacional
        for observacion in serie.get("Data", []):
            if observacion.get("Valor") is None or observacion.get("Secreto"):
                continue
            anio = int(observacion.get("Anyo") or str(observacion.get("NombrePeriodo", ""))[:4])
            fila = registros.setdefault((codigo, anio), {"codigo_ccaa": codigo, "ccaa": territorio.strip(), "anio": anio})
            fila[columna] = float(observacion["Valor"])
    columnas = ["codigo_ccaa", "ccaa", "anio", *INDICADORES_AGUA.values()]
    tabla = pd.DataFrame(list(registros.values()), columns=columnas)
    return tabla.sort_values(["codigo_ccaa", "anio"]).reset_index(drop=True)


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
