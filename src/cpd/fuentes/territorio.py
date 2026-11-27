"""Contexto territorial municipal a partir de fuentes oficiales locales.

La tabla municipal se une exclusivamente por código INE de cinco dígitos. La
capacidad de REE se conserva a nivel de nudo y comunidad autónoma: este módulo
no la reparte entre municipios ni infiere proximidad o viabilidad técnica.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from cpd.fuentes import red_capacidad


FUENTE_GISCO = "Eurostat GISCO · LAU 2024"
FUENTE_INE_DICCIONARIO = "INE · Relación de municipios 2026"
FUENTE_INE_PADRON = "INE · Padrón municipal, tabla 29005"
FUENTE_REE = "Red Eléctrica · Capacidad de acceso de demanda"


def _numero_ine(serie: pd.Series) -> pd.Series:
    """Convierte números oficiales españoles a número, preservando ausencias."""
    texto = serie.astype("string").str.strip()
    return pd.to_numeric(texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


def leer_diccionario_municipios(ruta: Path) -> pd.DataFrame:
    """Lee el diccionario INE y devuelve una fila única por municipio vigente en 2026.

    Args:
        ruta: XLSX oficial de la relación de municipios del INE.

    Returns:
        DataFrame con ``codigo_municipio`` (texto, 5 dígitos), provincia, CCAA y nombre.
    """
    crudo = pd.read_excel(ruta, skiprows=1, dtype=str)
    requeridas = {"CODAUTO", "CPRO", "CMUN", "DC", "NOMBRE"}
    faltan = requeridas - set(crudo.columns)
    if faltan:
        raise ValueError(f"Diccionario INE sin columnas requeridas: {sorted(faltan)}")
    tabla = pd.DataFrame({
        "codigo_ccaa": crudo["CODAUTO"].astype("string").str.zfill(2),
        "codigo_provincia": crudo["CPRO"].astype("string").str.zfill(2),
        "codigo_municipio": crudo["CPRO"].astype("string").str.zfill(2) + crudo["CMUN"].astype("string").str.zfill(3),
        "digito_control_ine": crudo["DC"].astype("string"),
        "nombre_municipio": crudo["NOMBRE"].astype("string").str.strip(),
    })
    if tabla["codigo_municipio"].duplicated().any():
        raise ValueError("El diccionario INE contiene códigos municipales duplicados")
    return tabla.sort_values("codigo_municipio", ignore_index=True)


def leer_superficie_gisco(ruta: Path) -> pd.DataFrame:
    """Lee la superficie municipal GISCO España (km²), sin usar su población nula.

    Args:
        ruta: CSV de atributos LAU 2024 de GISCO.

    Returns:
        DataFrame único por ``codigo_municipio`` con superficie y año de la fuente.
    """
    crudo = pd.read_csv(ruta, dtype=str, encoding="utf-8", encoding_errors="replace")
    requeridas = {"GISCO_ID", "CNTR_CODE", "AREA_KM2", "YEAR"}
    faltan = requeridas - set(crudo.columns)
    if faltan:
        raise ValueError(f"GISCO sin columnas requeridas: {sorted(faltan)}")
    espana = crudo.loc[crudo["CNTR_CODE"].eq("ES")].copy()
    espana["codigo_municipio"] = espana["GISCO_ID"].str.extract(r"^ES_(\d{5})$", expand=False)
    tabla = pd.DataFrame({
        "codigo_municipio": espana["codigo_municipio"].astype("string"),
        # GISCO usa punto decimal, a diferencia de los CSV españoles del INE.
        "superficie_km2": pd.to_numeric(espana["AREA_KM2"], errors="coerce"),
        "anio_superficie": pd.to_numeric(espana["YEAR"], errors="coerce").astype("Int64"),
    }).dropna(subset=["codigo_municipio"])
    if tabla["codigo_municipio"].duplicated().any():
        raise ValueError("GISCO contiene más de una fila española para un municipio")
    return tabla.sort_values("codigo_municipio", ignore_index=True)


def leer_padron_municipal(ruta: Path, anio: int | None = None) -> pd.DataFrame:
    """Lee población total del padrón INE por municipio para un año disponible.

    Args:
        ruta: CSV oficial de INE tabla 29005, separado por punto y coma.
        anio: año de padrón solicitado; si es ``None``, se toma el último año disponible.

    Returns:
        DataFrame único por código municipal con población (habitantes) y año de fuente.
    """
    crudo = pd.read_csv(ruta, sep=";", dtype=str, encoding="utf-8", encoding_errors="replace")
    requeridas = {"Municipios", "Sexo", "Periodo", "Total"}
    faltan = requeridas - set(crudo.columns)
    if faltan:
        raise ValueError(f"Padrón INE sin columnas requeridas: {sorted(faltan)}")
    total = crudo.loc[crudo["Sexo"].astype("string").str.strip().str.casefold().eq("total")].copy()
    total["codigo_municipio"] = total["Municipios"].astype("string").str.extract(r"^(\d{5})\s", expand=False)
    total["anio_poblacion"] = pd.to_numeric(total["Periodo"], errors="coerce").astype("Int64")
    total["poblacion_habitantes"] = _numero_ine(total["Total"])
    if anio is None:
        disponibles = total["anio_poblacion"].dropna()
        if disponibles.empty:
            raise ValueError("El padrón INE no contiene ningún año válido")
        anio = int(disponibles.max())
    tabla = total.loc[total["anio_poblacion"].eq(anio), ["codigo_municipio", "poblacion_habitantes", "anio_poblacion"]].dropna(subset=["codigo_municipio"])
    if tabla.empty:
        raise ValueError(f"El padrón INE no contiene datos para el año {anio}")
    if tabla["codigo_municipio"].duplicated().any():
        raise ValueError(f"El padrón INE contiene municipios duplicados para {anio}")
    return tabla.sort_values("codigo_municipio", ignore_index=True)


def construir_contexto_municipal(
    ruta_diccionario: Path,
    ruta_gisco: Path,
    ruta_padron: Path,
    anio_padron: int | None = None,
) -> pd.DataFrame:
    """Construye contexto municipal trazable con población, superficie y densidad.

    La fila es un municipio vigente en el diccionario INE 2026. La densidad se
    calcula como habitantes/km² solo cuando existen ambas fuentes; no se imputan
    poblaciones GISCO ni se realizan uniones geográficas.
    """
    municipios = leer_diccionario_municipios(ruta_diccionario)
    superficie = leer_superficie_gisco(ruta_gisco)
    poblacion = leer_padron_municipal(ruta_padron, anio=anio_padron)
    tabla = municipios.merge(superficie, on="codigo_municipio", how="left", validate="one_to_one")
    tabla = tabla.merge(poblacion, on="codigo_municipio", how="left", validate="one_to_one")
    tabla["densidad_hab_km2"] = tabla["poblacion_habitantes"] / tabla["superficie_km2"]
    tabla.loc[tabla["superficie_km2"].le(0), "densidad_hab_km2"] = pd.NA
    tabla["fuente_superficie"] = FUENTE_GISCO
    tabla["fuente_poblacion"] = FUENTE_INE_PADRON
    tabla["fuente_identidad"] = FUENTE_INE_DICCIONARIO
    return tabla.sort_values("codigo_municipio", ignore_index=True)


def leer_nudos_ree_por_ccaa(ruta: Path) -> pd.DataFrame:
    """Lee registros REE por nudo y CCAA, sin vincularlos a ningún municipio.

    Args:
        ruta: CSV de capacidad de acceso REE para demanda de la red de transporte.

    Returns:
        DataFrame por nudo con capacidades REE en MW y metadatos de procedencia.
    """
    contenido = ruta.read_bytes()
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    crudo = pd.read_csv(io.StringIO(texto), sep=";", header=None, dtype=str, keep_default_na=False)
    if len(crudo) < 3:
        raise ValueError("CSV REE sin cabeceras y registros suficientes")
    grupos = crudo.iloc[0].tolist()
    subcabeceras = crudo.iloc[1].tolist()
    columna_disponible = red_capacidad._columna_demanda_rdt(grupos, subcabeceras)
    datos = crudo.iloc[2:].copy()
    datos = datos.loc[datos.iloc[:, 0].astype("string").str.strip().ne("")].copy()
    datos["codigo_ccaa"] = datos.iloc[:, 2].map(red_capacidad.codigo_ccaa_de_texto)
    datos = datos.dropna(subset=["codigo_ccaa"])

    def capacidad(indice: int | None) -> pd.Series:
        if indice is None:
            return pd.Series(float("nan"), index=datos.index, dtype=float)
        return pd.to_numeric(datos.iloc[:, indice].astype("string").str.replace(",", ".", regex=False), errors="coerce")

    otorgada = red_capacidad._columna_por_subcabecera(subcabeceras, red_capacidad.SUBCABECERA_OTORGADA)
    pendiente = red_capacidad._columna_por_subcabecera(subcabeceras, red_capacidad.SUBCABECERA_PENDIENTE)
    tabla = pd.DataFrame({
        "nudo_ree": datos.iloc[:, 0].astype("string").str.strip(),
        "codigo_subestacion_ree": datos.iloc[:, 1].astype("string").str.strip(),
        "ccaa_ree": datos.iloc[:, 2].astype("string").str.strip(),
        "codigo_ccaa": datos["codigo_ccaa"].astype("string"),
        "capacidad_demanda_rdt_disponible_mw": capacidad(columna_disponible),
        "capacidad_demanda_rdt_otorgada_mw": capacidad(otorgada),
        "capacidad_demanda_rdt_pendiente_mw": capacidad(pendiente),
        "fuente_ree": FUENTE_REE,
        "archivo_origen": ruta.name,
    })
    return tabla.sort_values(["codigo_ccaa", "nudo_ree"], ignore_index=True)
