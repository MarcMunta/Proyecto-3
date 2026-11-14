"""Población por provincia desde el padrón municipal del INE (tabla 29005), para completar 2022-2025.

Fuente: https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/29005.csv (CSV con ';', una fila por
municipio, sexo y año). La columna Municipios trae "CCCCC Nombre" (código INE de 5 dígitos y nombre);
el código de provincia son sus dos primeros dígitos. Los miles llevan punto ("2.239").

Reglas:
- Solo se suman filas de sexo "Total".
- Un municipio sin dato en un año en el que tenía dato el anterior se considera desaparecido por
  fusión (su población pasa al municipio nuevo, con otro código). Se suma lo disponible y se
  informa en municipios_sin_dato. No se estima ningún hueco.
- Para años con la tabla Tempus3 (2852, hasta 2021) se prefiere esa serie; el padrón aporta los años
  posteriores. En los años solapados se informa la diferencia relativa como control.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, descargar_archivo

FUENTE: str = "INE padrón municipal (29005)"
URL: str = "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/29005.csv"
RUTA: Path = RUTA_API / "ine" / "padron_municipios_29005.csv"
DIAS_MAXIMOS_FICHERO: int = 30  # el padrón se publica cada año; se vuelve a bajar si el fichero tiene más días


def asegurar_fichero(forzar: bool = False) -> Path:
    """Descarga el CSV del padrón si no existe o está desactualizado (más de DIAS_MAXIMOS_FICHERO días)."""
    import datetime as dt

    if RUTA.exists() and not forzar:
        edad = (dt.datetime.now() - dt.datetime.fromtimestamp(RUTA.stat().st_mtime)).days
        if edad <= DIAS_MAXIMOS_FICHERO:
            return RUTA
    return descargar_archivo(URL, RUTA, FUENTE, "Padrón municipal, todos los municipios (CSV)", forzar=RUTA.exists())


def leer_padron(ruta: Path) -> pd.DataFrame:
    """Población total por provincia y año, con control de municipios sin dato.

    Returns:
        DataFrame: codigo_provincia, anio, poblacion_padron (NaN si hay municipios sin dato),
        municipios, municipios_sin_dato.
    """
    datos = pd.read_csv(ruta, sep=";", dtype=str, encoding="utf-8-sig")
    columnas = {"Municipios", "Sexo", "Periodo", "Total"}
    if not columnas.issubset(datos.columns):
        raise ErrorFuente(f"{FUENTE}: columnas inesperadas {list(datos.columns)}")
    datos = datos[datos["Sexo"] == "Total"].copy()
    datos["codigo_municipio"] = datos["Municipios"].str.slice(0, 5)
    datos["codigo_provincia"] = datos["codigo_municipio"].str.slice(0, 2)
    datos["anio"] = pd.to_numeric(datos["Periodo"], errors="coerce").astype("Int64")
    datos["poblacion"] = pd.to_numeric(datos["Total"].str.replace(".", "", regex=False), errors="coerce")
    datos = datos.dropna(subset=["anio", "codigo_municipio"]).sort_values(["codigo_municipio", "anio"])
    # Municipio "desaparecido" = tenía dato el año anterior y no lo tiene este: en el padrón
    # aparece fusionado con otro código (p. ej. Cerdedo + Cotobade -> Cerdedo-Cotobade, 2023).
    anterior = datos.groupby("codigo_municipio")["poblacion"].shift(1)
    datos["desaparecido"] = datos["poblacion"].isna() & anterior.notna()
    grupos = datos.groupby(["codigo_provincia", "anio"])
    tabla = grupos.agg(
        poblacion_padron=("poblacion", "sum"),
        municipios=("codigo_municipio", "nunique"),
        municipios_sin_dato=("desaparecido", "sum"),
    ).reset_index()
    tabla["poblacion_padron"] = tabla["poblacion_padron"].round(0)
    tabla["municipios_sin_dato"] = tabla["municipios_sin_dato"].astype(int)
    return tabla[["codigo_provincia", "anio", "poblacion_padron", "municipios", "municipios_sin_dato"]]


def combinar_poblacion(tempus: pd.DataFrame, padron: pd.DataFrame) -> pd.DataFrame:
    """Serie provincial única: Tempus3 (2852) cuando existe el año; si no, el padrón.

    Args:
        tempus: codigo_provincia, anio, poblacion (puede estar vacía).
        padron: salida de leer_padron (puede estar vacía).

    Returns:
        DataFrame: codigo_provincia, anio, poblacion, fuente_poblacion, y diferencia_relativa_pct
        (diferencia padrón frente a Tempus en los años solapados, para control).
    """
    columnas = ["codigo_provincia", "anio", "poblacion", "fuente_poblacion", "diferencia_padron_vs_tempus_pct"]
    t = tempus.rename(columns={"poblacion": "poblacion_tempus"})[["codigo_provincia", "anio", "poblacion_tempus"]] \
        if not tempus.empty else pd.DataFrame(columns=["codigo_provincia", "anio", "poblacion_tempus"])
    p = padron.rename(columns={"poblacion_padron": "poblacion_pad"})[["codigo_provincia", "anio", "poblacion_pad"]] \
        if not padron.empty else pd.DataFrame(columns=["codigo_provincia", "anio", "poblacion_pad"])
    cruce = t.merge(p, on=["codigo_provincia", "anio"], how="outer")
    cruce["diferencia_padron_vs_tempus_pct"] = (
        100 * (cruce["poblacion_pad"] - cruce["poblacion_tempus"]) / cruce["poblacion_tempus"]).round(2)
    usa_tempus = cruce["poblacion_tempus"].notna()
    cruce["poblacion"] = cruce["poblacion_tempus"].where(usa_tempus, cruce["poblacion_pad"])
    cruce["fuente_poblacion"] = usa_tempus.map({True: "INE Tempus3 (2852)", False: "INE padrón (29005)"})
    cruce.loc[cruce["poblacion"].isna(), "fuente_poblacion"] = None
    if cruce.empty:
        return pd.DataFrame(columns=columnas)
    return cruce[columnas].sort_values(["codigo_provincia", "anio"]).reset_index(drop=True)
