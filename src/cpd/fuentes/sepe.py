"""SEPE: paro registrado por municipio (datos abiertos mensuales), agregado a provincia.

Fichero anual: https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_{AÑO}_csv.csv
Formato: latin-1, separador ';', una línea de título antes de la cabecera, valores "<5"
cuando el dato está sujeto a secreto estadístico (solo en los desgloses; el total de paro
del municipio no se suprime).

Salida: paro registrado total por provincia y mes (suma de municipios). El año en curso
se vuelve a descargar; los años cerrados se cachean.
"""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, descargar_archivo
from cpd.fuentes.provincias import ficha

URL_PLANTILLA: str = (
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_{anio}_csv.csv"
)
FUENTE: str = "SEPE"
CARPETA: Path = RUTA_API / "sepe"
COLUMNA_MES: str = "Código mes"
COLUMNA_PROVINCIA: str = "Codigo Provincia"
COLUMNA_TOTAL: str = "total Paro Registrado"


def leer_csv_sepe(contenido: bytes) -> pd.DataFrame:
    """Lee el CSV del SEPE (latin-1, ';', título en la primera línea) y lo devuelve como texto.

    Raises:
        ErrorFuente: si no aparecen las columnas esperadas.
    """
    texto = contenido.decode("latin-1")
    cabecera_real = texto.split("\n", 1)[1] if texto.startswith(";;;;") or "PARO REGISTRADO" in texto[:200] else texto
    tabla = pd.read_csv(io.StringIO(cabecera_real), sep=";", dtype=str, keep_default_na=False)
    tabla.columns = [c.strip() for c in tabla.columns]
    faltan = [c for c in (COLUMNA_MES, COLUMNA_PROVINCIA, COLUMNA_TOTAL) if c not in tabla.columns]
    if faltan:
        raise ErrorFuente(f"{FUENTE}: faltan columnas {faltan}; encontradas {list(tabla.columns)[:8]}")
    return tabla


def agregar_provincias(tabla: pd.DataFrame) -> pd.DataFrame:
    """Suma el paro de los municipios por provincia y mes.

    Returns:
        DataFrame: codigo_provincia, mes (inicio de mes), paro_registrado, municipios.
    """
    datos = tabla[[COLUMNA_MES, COLUMNA_PROVINCIA, COLUMNA_TOTAL]].copy()
    datos["codigo_provincia"] = datos[COLUMNA_PROVINCIA].str.strip().str.zfill(2)
    datos["mes"] = pd.to_datetime(datos[COLUMNA_MES].str.strip(), format="%Y%m")
    datos["paro"] = pd.to_numeric(datos[COLUMNA_TOTAL].str.replace(".", "", regex=False).str.strip(), errors="coerce")
    agregado = (
        datos.dropna(subset=["paro"])
        .groupby(["codigo_provincia", "mes"])
        .agg(paro_registrado=("paro", "sum"), municipios=("paro", "size"))
        .reset_index()
    )
    agregado["paro_registrado"] = agregado["paro_registrado"].astype(int)
    return agregado


def paro_provincias_mensual(anio_inicio: int = 2015, anio_fin: int | None = None) -> pd.DataFrame:
    """Paro registrado mensual por provincia entre dos años (incluidos).

    Los años que aún no se han publicado se omiten sin error (el SEPE publica mes a mes).
    """
    anio_fin = anio_fin or dt.date.today().year
    partes = []
    for anio in range(anio_inicio, anio_fin + 1):
        destino = CARPETA / f"Paro_por_municipios_{anio}_csv.csv"
        url = URL_PLANTILLA.format(anio=anio)
        cerrado = anio < dt.date.today().year
        if not destino.exists() or not cerrado:
            try:
                descargar_archivo(url, destino, FUENTE, f"Paro registrado por municipio {anio}", forzar=not cerrado)
            except ErrorFuente:
                if anio == dt.date.today().year:
                    continue  # año en curso aún sin publicar
                raise
        partes.append(agregar_provincias(leer_csv_sepe(destino.read_bytes())))
    if not partes:
        return pd.DataFrame(columns=["codigo_provincia", "mes", "paro_registrado", "municipios"])
    tabla = pd.concat(partes, ignore_index=True)
    return tabla.sort_values(["codigo_provincia", "mes"]).reset_index(drop=True)


def nombre_provincia(codigo: str) -> str:
    """Nombre oficial de la provincia (solo para mensajes)."""
    return ficha(codigo).nombre
