"""Extractor de demanda eléctrica mensual de España desde REData (Red Eléctrica de España).

API pública, sin clave: https://apidatos.ree.es/es/datos/
Endpoint: demanda/evolucion (parámetros start_date, end_date en formato YYYY-MM-DDTHH:MM,
time_trunc=month). La respuesta trae included[0].attributes.values[] con value (MWh en
truncado mensual) y datetime (con zona horaria).

Uso desde terminal (desde la raíz del proyecto, con el venv activado):
    python -m cpd.etl.ree --inicio 2015 --fin 2025

Salidas:
- data/raw/ree/<YYYYMMDD>/demanda_<anio>.json  (respuesta original, una por año)
- data/clean/ree_demanda_mensual.csv           (columnas fecha, demanda_mwh)

Los errores de red, timeouts, respuestas HTTP de error o JSON inesperado se lanzan como
ErrorREE con un mensaje claro: no se generan datos falsos ni se ignoran fallos.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from cpd.config import RUTA_DEMANDA_LIMPIA, RUTA_RAW

URL_BASE: str = "https://apidatos.ree.es/es/datos/"
ENDPOINT_DEMANDA: str = "demanda/evolucion"
TIMEOUT_SEGUNDOS: float = 60.0
MESES_ESPERADOS_ANIO: int = 12


class ErrorREE(RuntimeError):
    """Error al descargar o interpretar datos de REData."""


def _ruta_raw_hoy() -> Path:
    """Carpeta data/raw/ree/<YYYYMMDD> para la descarga de hoy."""
    return RUTA_RAW / "ree" / date.today().strftime("%Y%m%d")


def descargar_anio(anio: int, sesion: requests.Session | None = None) -> dict:
    """Descarga la demanda mensual de un año natural.

    Args:
        anio: año a descargar (por ejemplo 2015).
        sesion: sesión HTTP opcional (para reutilizar conexiones o simular en tests).

    Returns:
        JSON de la respuesta como diccionario.

    Raises:
        ErrorREE: si hay error de red, timeout, código HTTP de error o respuesta no JSON.
    """
    parametros = {
        "start_date": f"{anio}-01-01T00:00",
        "end_date": f"{anio}-12-31T23:59",
        "time_trunc": "month",
    }
    cliente = sesion or requests
    try:
        respuesta = cliente.get(URL_BASE + ENDPOINT_DEMANDA, params=parametros, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
    except requests.Timeout as error:
        raise ErrorREE(f"Tiempo de espera agotado ({TIMEOUT_SEGUNDOS}s) al pedir el año {anio}: {error}") from error
    except requests.HTTPError as error:
        raise ErrorREE(f"REData respondió con error HTTP al pedir el año {anio}: {error}") from error
    except requests.RequestException as error:
        raise ErrorREE(f"Error de red al pedir el año {anio}: {error}") from error

    try:
        return respuesta.json()
    except ValueError as error:
        raise ErrorREE(f"La respuesta de REData para {anio} no es JSON válido") from error


def extraer_valores(datos: dict, anio: int) -> pd.DataFrame:
    """Convierte la respuesta JSON de REData en una tabla tidy (fecha, demanda_mwh).

    Args:
        datos: JSON devuelto por descargar_anio().
        anio: año esperado (para validar las fechas).

    Returns:
        DataFrame con fecha (inicio de mes, sin zona horaria) y demanda_mwh (float).

    Raises:
        ErrorREE: si la estructura del JSON no coincide con la esperada o faltan meses.
    """
    try:
        valores = datos["included"][0]["attributes"]["values"]
    except (KeyError, IndexError, TypeError) as error:
        raise ErrorREE(f"Estructura JSON inesperada en la respuesta del año {anio}") from error

    filas = []
    for punto in valores:
        if punto.get("value") is None:
            continue
        fecha = pd.to_datetime(punto["datetime"]).tz_localize(None).to_period("M").to_timestamp()
        filas.append({"fecha": fecha, "demanda_mwh": float(punto["value"])})

    tabla = pd.DataFrame(filas, columns=["fecha", "demanda_mwh"])
    if len(tabla) != MESES_ESPERADOS_ANIO:
        raise ErrorREE(f"El año {anio} trae {len(tabla)} meses con dato; se esperaban {MESES_ESPERADOS_ANIO}")
    return tabla


def descargar_demanda_mensual(
    anio_inicio: int,
    anio_fin: int,
    ruta_salida: Path | None = None,
    carpeta_raw: Path | None = None,
    sesion: requests.Session | None = None,
) -> pd.DataFrame:
    """Descarga la demanda mensual año a año, guarda JSON crudo y CSV limpio.

    Args:
        anio_inicio: primer año (incluido).
        anio_fin: último año (incluido).
        ruta_salida: CSV de salida (por defecto data/clean/ree_demanda_mensual.csv).
        carpeta_raw: carpeta base para los JSON (por defecto data/raw/ree/<fecha de hoy>).
        sesion: sesión HTTP opcional.

    Returns:
        DataFrame tidy con columnas fecha y demanda_mwh, ordenado por fecha.

    Raises:
        ValueError: si anio_inicio > anio_fin.
        ErrorREE: ante cualquier fallo de descarga o de interpretación.
    """
    if anio_inicio > anio_fin:
        raise ValueError("anio_inicio no puede ser mayor que anio_fin")

    carpeta = carpeta_raw or _ruta_raw_hoy()
    carpeta.mkdir(parents=True, exist_ok=True)
    tablas = []
    for anio in range(anio_inicio, anio_fin + 1):
        print(f"Descargando demanda REData {anio}...", file=sys.stderr)
        datos = descargar_anio(anio, sesion=sesion)
        (carpeta / f"demanda_{anio}.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        tablas.append(extraer_valores(datos, anio))

    tabla = pd.concat(tablas, ignore_index=True).drop_duplicates("fecha").sort_values("fecha")
    tabla = tabla.reset_index(drop=True)

    destino = ruta_salida or RUTA_DEMANDA_LIMPIA
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(destino, index=False, encoding="utf-8")
    return tabla


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada CLI. Devuelve 0 si todo va bien, 1 si hay error."""
    parser = argparse.ArgumentParser(description="Descarga demanda eléctrica mensual de REData.")
    parser.add_argument("--inicio", type=int, default=2015, help="Año inicial (por defecto 2015)")
    parser.add_argument("--fin", type=int, default=2025, help="Año final (por defecto 2025)")
    args = parser.parse_args(argumentos)
    try:
        tabla = descargar_demanda_mensual(args.inicio, args.fin)
    except (ErrorREE, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"OK: {len(tabla)} filas, de {tabla['fecha'].min():%Y-%m} a {tabla['fecha'].max():%Y-%m}. "
        f"CSV: {RUTA_DEMANDA_LIMPIA}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
