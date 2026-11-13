"""OMIE: precio marginal del mercado diario (España) desde los ficheros públicos marginalpdbc.

Fichero: https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_YYYYMMDD.1
Formato: cabecera "MARGINALPDBC;" y líneas ``año;mes;día;periodo;precio_ES;precio_PT;``.
Hay 96 periodos de 15 minutos (desde oct-2025) o 24 horarios en los años anteriores.

Se usa para los precios de mañana (el día siguiente se publica tras el cierre de la
subasta) y como respaldo de REData. Sin caché: el fichero del día siguiente cambia
hasta su publicación definitiva.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from cpd.fuentes.http import ErrorFuente, pedir

URL_BASE: str = "https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_{fecha}.1"
ETIQUETA: str = "OMIE"


def interpretar_marginalpdbc(texto: str, fecha: dt.date) -> pd.DataFrame:
    """Convierte el texto de un marginalpdbc en tabla (momento, precio_es_eur_mwh).

    Args:
        texto: contenido del fichero.
        fecha: día al que corresponde (para construir el momento de cada periodo).

    Returns:
        DataFrame con una fila por periodo: momento (inicio del periodo, sin zona), precio_es_eur_mwh.

    Raises:
        ErrorFuente: si el formato no es el esperado.
    """
    filas = []
    duracion_periodo = pd.Timedelta(minutes=1440 // _periodos_del_dia(texto))
    for linea in texto.splitlines():
        partes = [p.strip() for p in linea.split(";") if p.strip() != ""]
        if len(partes) < 5 or not partes[0].isdigit():
            continue  # cabecera u otras líneas
        try:
            periodo = int(partes[3])
            precio = float(partes[4].replace(",", "."))
        except ValueError as error:
            raise ErrorFuente(f"{ETIQUETA}: línea con formato inesperado: {linea!r}") from error
        duracion = duracion_periodo
        filas.append({"momento": pd.Timestamp(fecha) + duracion * (periodo - 1), "precio_es_eur_mwh": precio})
    if not filas:
        raise ErrorFuente(f"{ETIQUETA}: el fichero del {fecha:%d/%m/%Y} no contiene precios")
    return pd.DataFrame(filas)


def _periodos_del_dia(texto: str) -> int:
    """Número de periodos del fichero (96 para cuartos de hora, 24 para horas)."""
    maximo = 0
    for linea in texto.splitlines():
        partes = [p.strip() for p in linea.split(";") if p.strip() != ""]
        if len(partes) >= 5 and partes[0].isdigit():
            try:
                maximo = max(maximo, int(partes[3]))
            except ValueError:
                continue
    return 96 if maximo > 24 else 24


def precios_del_dia(fecha: dt.date) -> pd.DataFrame | None:
    """Precios de un día concreto del mercado diario. Devuelve None si el fichero aún no existe."""
    url = URL_BASE.format(fecha=fecha.strftime("%Y%m%d"))
    try:
        respuesta = pedir(url, reintentos=2, etiqueta=f"{ETIQUETA} {fecha:%d/%m/%Y}")
    except ErrorFuente:
        return None
    texto = respuesta.content.decode("latin-1", errors="replace")
    if "MARGINALPDBC" not in texto.upper():
        return None
    return interpretar_marginalpdbc(texto, fecha)


def precios_hoy_y_manana() -> dict[str, pd.DataFrame | None]:
    """Precios de hoy y de mañana. El de mañana es None mientras OMIE no lo haya publicado."""
    hoy = dt.date.today()
    return {"hoy": precios_del_dia(hoy), "manana": precios_del_dia(hoy + dt.timedelta(days=1))}
