"""Indicadores de agua por provincia: estrés hídrico de referencia (WRI), balance y sequía climáticos.

- ``estres_hidrico_wri``: línea base de estrés hídrico (WRI Aqueduct 4.0, indicador "bws", escala 0-5)
  a nivel de comunidad autónoma, reescalada a 0-1 y asignada a sus provincias. Es una foto estática
  (no tiene serie temporal). El fichero se lee directamente desde el zip, sin extraerlo a disco.
- ``indice_sequia_12m``: índice tipo SPI simplificado. Se calcula la precipitación acumulada en los
  últimos 12 meses y se normaliza con la media y la desviación típica de ese mismo acumulado en el
  mismo mes del calendario. Valores < -1 indican sequía moderada; < -2, severa. Con pocos años de
  historia (2015-) la referencia es corta y el índice es orientativo.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from cpd.config import RUTA_RAW

RUTA_WRI_ZIP: Path = RUTA_RAW / "agua" / "wri_aqueduct40_rankings_pais_provincia.zip"
NOMBRE_HOJA_WRI: str = "province_baseline"
INDICADOR_WRI: str = "bws"  # Baseline water stress
PONDERACION_WRI: str = "Tot"  # esquema de ponderación de la demanda total (el resto: Irr, Ind, Dom, Liv, One)
ESCALA_WRI_MAXIMA: float = 5.0


def _arreglar_texto(texto: str) -> str:
    """Corrige el mojibake de la hoja WRI (UTF-8 leído como cp1252: 'AndalucÃ­a' -> 'Andalucía')."""
    try:
        return str(texto).encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return str(texto)
VENTANA_SEQUIA_MESES: int = 12
MINIMO_ANIOS_REFERENCIA: int = 3

# Nombre de comunidad en la hoja WRI -> código INE de comunidad autónoma (Ceuta y Melilla juntas).
CCAA_WRI_A_CODIGO: dict[str, tuple[str, ...]] = {
    "Andalucía": ("01",), "Aragón": ("02",), "Principado de Asturias": ("03",), "Islas Baleares": ("04",),
    "Islas Canarias": ("05",), "Cantabria": ("06",), "Castilla y León": ("07",), "Castilla-La Mancha": ("08",),
    "Cataluña": ("09",), "Comunidad Valenciana": ("10",), "Extremadura": ("11",), "Galicia": ("12",),
    "Comunidad de Madrid": ("13",), "Región de Murcia": ("14",), "Comunidad Foral de Navarra": ("15",),
    "País Vasco": ("16",), "La Rioja": ("17",), "Ceuta y Melilla": ("18", "19"),
}


def estres_hidrico_wri(ruta_zip: Path = RUTA_WRI_ZIP) -> pd.DataFrame:
    """Estrés hídrico de referencia por provincia (0-1), a partir de la hoja de provincias del WRI.

    Returns:
        DataFrame: codigo_provincia, estres_hidrico_wri_0_1, comunidad_wri (nombre de la fuente).
    """
    from cpd.fuentes.provincias import PROVINCIAS

    with zipfile.ZipFile(ruta_zip) as zf:
        ruta_xlsx = next(n for n in zf.namelist() if n.lower().endswith(".xlsx"))
        datos = pd.read_excel(io.BytesIO(zf.read(ruta_xlsx)), sheet_name=NOMBRE_HOJA_WRI)
    espana = datos[(datos["name_0"] == "Spain") & (datos["indicator_name"] == INDICADOR_WRI)
                   & (datos["weight"] == PONDERACION_WRI)]
    por_ccaa = {_arreglar_texto(fila["name_1"]): float(fila["score"]) for _, fila in espana.iterrows()}
    filas = []
    for provincia in PROVINCIAS:
        ccaa = next((nombre for nombre, codigos in CCAA_WRI_A_CODIGO.items() if provincia.ccaa_codigo in codigos), None)
        valor = por_ccaa.get(ccaa) if ccaa else None
        filas.append({
            "codigo_provincia": provincia.codigo,
            "estres_hidrico_wri_0_1": round(min(max(valor / ESCALA_WRI_MAXIMA, 0.0), 1.0), 3) if valor is not None else None,
            "comunidad_wri": ccaa,
        })
    return pd.DataFrame(filas)


def precipitacion_12_meses(mensual: pd.DataFrame) -> pd.DataFrame:
    """Acumulado móvil de 12 meses de la precipitación, por provincia (sin huecos internos).

    Args:
        mensual: columnas mes, codigo_provincia, precipitacion_mes_mm.

    Returns:
        DataFrame: mes, codigo_provincia, precipitacion_12m_mm (NaN si faltan meses en la ventana).
    """
    datos = mensual[["mes", "codigo_provincia", "precipitacion_mes_mm"]].copy()
    datos["mes"] = pd.to_datetime(datos["mes"]).dt.to_period("M").dt.to_timestamp()
    datos = datos.sort_values(["codigo_provincia", "mes"])
    datos["precipitacion_12m_mm"] = datos.groupby("codigo_provincia")["precipitacion_mes_mm"].transform(
        lambda s: s.rolling(VENTANA_SEQUIA_MESES, min_periods=VENTANA_SEQUIA_MESES).sum())
    return datos[["mes", "codigo_provincia", "precipitacion_12m_mm"]]


def indice_sequia_12m(mensual: pd.DataFrame) -> pd.DataFrame:
    """Índice de sequía a 12 meses (z-score del acumulado frente a su mismo mes del calendario).

    Returns:
        DataFrame: mes, codigo_provincia, precipitacion_12m_mm, indice_sequia_12m.
        El índice es NaN si hay menos de MINIMO_ANIOS_REFERENCIA años de referencia para ese mes.
    """
    datos = precipitacion_12_meses(mensual)
    datos["calendario"] = datos["mes"].dt.month
    grupos = datos.groupby(["codigo_provincia", "calendario"])["precipitacion_12m_mm"]
    media = grupos.transform("mean")
    desviacion = grupos.transform("std")
    numero = grupos.transform("count")
    z = (datos["precipitacion_12m_mm"] - media) / desviacion.where(desviacion > 0)
    datos["indice_sequia_12m"] = z.where(numero >= MINIMO_ANIOS_REFERENCIA).round(2)
    return datos.drop(columns="calendario")


def balance_hidrico_mm(precipitacion_mm: pd.Series, evapotranspiracion_mm: pd.Series) -> pd.Series:
    """Balance hídrico climático simple: precipitación − evapotranspiración de referencia (mm).

    Valores negativos indican que la evaporación potencial supera a la lluvia del periodo.
    NaN si falta cualquiera de los dos términos (no se rellena).
    """
    return (precipitacion_mm - evapotranspiracion_mm).round(1)
