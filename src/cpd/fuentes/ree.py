"""Red Eléctrica de España (REData, API pública sin clave): demanda, generación, CO2, precios y tiempo real.

Base: https://apidatos.ree.es/es/datos/
Notas de comportamiento observadas (13/11/2026):
- La API responde 400/502 "Error Interno" de forma intermitente: se reintenta.
- Los precios con ``time_trunc=day`` fallan; con ``time_trunc=hour`` funcionan por meses.
- Las emisiones de CO2 no admiten desglose por CCAA: se usa el total nacional.
- Un año es el máximo práctico por petición en la demanda y generación por CCAA.

Caché: data/raw/api/ree/... (un JSON por petición). Los periodos cerrados no se repiten.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, json_de, leer_cache_json, registrar
from cpd.fuentes.provincias import REE_GEO_ID_CCAA

URL_BASE: str = "https://apidatos.ree.es/es/datos/"
ETIQUETA: str = "REData"
CARPETA: Path = RUTA_API / "ree"
ANIO_INICIO_HISTORIA: int = 2015
NOMBRE_SERIE_SPOT: str = "Precio mercado spot"
NOMBRE_SERIE_PVPC: str = "PVPC"


def _hora_local(texto: str) -> pd.Timestamp:
    """Convierte una marca de REData (con desfase horario) a hora de Madrid sin zona."""
    return pd.Timestamp(texto).tz_convert("Europe/Madrid").tz_localize(None)


def _url(endpoint: str) -> str:
    return URL_BASE + endpoint


def _pedir(endpoint: str, params: dict[str, Any], ruta: Path | None, cerrado: bool) -> dict:
    """Pide un endpoint de REData con caché opcional en `ruta` (solo si el periodo está cerrado)."""
    if ruta is not None and cerrado:
        cache = leer_cache_json(ruta)
        if cache is not None:
            return cache
    datos = json_de(_url(endpoint), params=params, etiqueta=f"{ETIQUETA} {endpoint}")
    if isinstance(datos, dict) and "errors" in datos:
        raise ErrorFuente(f"{ETIQUETA} {endpoint}: {datos['errors'][0].get('detail', 'error')}")
    if ruta is not None:
        guardar_cache_json(ruta, datos)
        registrar("Red Eléctrica (REData API)", f"{endpoint} {params}", _url(endpoint), ruta, ruta.stat().st_size / 1024)
    return datos


def _serie(datos: dict, nombre: str) -> list[dict]:
    """Valores de la serie cuyo título coincide con `nombre` (REData anida las series en included[])."""
    for bloque in datos.get("included", []):
        atributos = bloque.get("attributes", {})
        if atributos.get("title") == nombre or bloque.get("type") == nombre:
            return [v for v in atributos.get("values", []) if v.get("value") is not None]
    return []


def _periodo(anio: int, mes: int | None = None) -> tuple[str, str]:
    """Fechas inicio/fin en el formato de REData para un año o un mes."""
    if mes is None:
        return f"{anio}-01-01T00:00", f"{anio}-12-31T23:59"
    ultimo = (dt.date(anio + (mes // 12), mes % 12 + 1, 1) - dt.timedelta(days=1)).day
    return f"{anio}-{mes:02d}-01T00:00", f"{anio}-{mes:02d}-{ultimo:02d}T23:59"


def _cerrado(anio: int, mes: int | None = None) -> bool:
    """True si el periodo ya ha terminado (sus datos no cambian)."""
    hoy = dt.date.today()
    if mes is None:
        return anio < hoy.year
    return (anio, mes) < (hoy.year, hoy.month)


def demanda_ccaa_mensual(anio_inicio: int = ANIO_INICIO_HISTORIA, anio_fin: int | None = None) -> pd.DataFrame:
    """Demanda eléctrica mensual (MWh) por comunidad autónoma.

    Returns:
        DataFrame: codigo_ccaa (INE), ccaa, ree_geo_id, fecha (inicio de mes), demanda_mwh.
    """
    anio_fin = anio_fin or dt.date.today().year
    filas = []
    for codigo_ccaa, geo_id in _ccaa_ree().items():
        for anio in range(anio_inicio, anio_fin + 1):
            params = {
                "start_date": _periodo(anio)[0],
                "end_date": _periodo(anio)[1],
                "time_trunc": "month",
                "geo_trunc": "electric_system",
                "geo_limit": "ccaa",
                "geo_ids": str(geo_id),
            }
            ruta = CARPETA / "demanda_ccaa" / f"{geo_id}_{anio}.json"
            datos = _pedir("demanda/evolucion", params, ruta, _cerrado(anio))
            for punto in _serie(datos, "Demanda en b.c.") or _valores_primer_bloque(datos):
                filas.append(
                    {
                        "codigo_ccaa": codigo_ccaa,
                        "ree_geo_id": geo_id,
                        "fecha": _hora_local(punto["datetime"]).to_period("M").to_timestamp(),
                        "demanda_mwh": float(punto["value"]),
                    }
                )
    return _con_nombre_ccaa(pd.DataFrame(filas, columns=["codigo_ccaa", "ree_geo_id", "fecha", "demanda_mwh"]))


def _valores_primer_bloque(datos: dict) -> list[dict]:
    """Respaldo: valores del primer bloque 'included' (REData lo usa cuando el título no coincide)."""
    try:
        return [v for v in datos["included"][0]["attributes"]["values"] if v.get("value") is not None]
    except (KeyError, IndexError, TypeError):
        return []


def _ccaa_ree() -> dict[str, int]:
    """Mapa código INE de CCAA -> geo_id de REData (sin repetir)."""
    from cpd.fuentes.provincias import PROVINCIAS

    mapa: dict[str, int] = {}
    for provincia in PROVINCIAS:
        mapa.setdefault(provincia.ccaa_codigo, provincia.ree_geo_id)
    return mapa


def _con_nombre_ccaa(tabla: pd.DataFrame) -> pd.DataFrame:
    from cpd.fuentes.provincias import CCAA_INE

    tabla = tabla.copy()
    tabla["ccaa"] = tabla["codigo_ccaa"].map(CCAA_INE)
    return tabla


def generacion_desde_respuesta(datos: dict, codigo_ccaa: str) -> list[dict]:
    """Filas mensuales (tecnología, tipo y MWh) de una respuesta de estructura de generación."""
    filas = []
    for bloque in datos.get("included", []):
        atributos = bloque.get("attributes", {})
        tipo = atributos.get("type")
        if tipo in (None, "total") or atributos.get("title") == "Generación total":
            tipo = "total"
        for punto in atributos.get("values", []):
            if punto.get("value") is None:
                continue
            filas.append(
                {
                    "codigo_ccaa": codigo_ccaa,
                    "fecha": _hora_local(punto["datetime"]).to_period("M").to_timestamp(),
                    "tecnologia": atributos.get("title", bloque.get("type")),
                    "tipo": tipo,
                    "generacion_mwh": float(punto["value"]),
                }
            )
    return filas


def generacion_ccaa_mensual(anio_inicio: int = ANIO_INICIO_HISTORIA, anio_fin: int | None = None) -> pd.DataFrame:
    """Generación mensual (MWh) por comunidad y tecnología, con clasificación renovable/no renovable.

    Returns:
        DataFrame: codigo_ccaa, ccaa, fecha, tecnologia, tipo ('Renovable' | 'No-Renovable' | ...), generacion_mwh.
    """
    anio_fin = anio_fin or dt.date.today().year
    filas = []
    for codigo_ccaa, geo_id in _ccaa_ree().items():
        for anio in range(anio_inicio, anio_fin + 1):
            params = {
                "start_date": _periodo(anio)[0],
                "end_date": _periodo(anio)[1],
                "time_trunc": "month",
                "geo_trunc": "electric_system",
                "geo_limit": "ccaa",
                "geo_ids": str(geo_id),
            }
            ruta = CARPETA / "generacion_ccaa" / f"{geo_id}_{anio}.json"
            datos = _pedir("generacion/estructura-generacion", params, ruta, _cerrado(anio))
            filas.extend(generacion_desde_respuesta(datos, codigo_ccaa))
    return _con_nombre_ccaa(pd.DataFrame(filas, columns=["codigo_ccaa", "fecha", "tecnologia", "tipo", "generacion_mwh"]))


def resumen_renovable(generacion: pd.DataFrame) -> pd.DataFrame:
    """Por CCAA y mes: generación total, renovable, no renovable y % renovable (sin contar 'total')."""
    if generacion.empty:
        return pd.DataFrame(columns=["codigo_ccaa", "fecha", "generacion_total_mwh", "generacion_renovable_mwh", "pct_renovable"])
    tecnologias = generacion[generacion["tipo"] != "total"]
    totales = generacion[generacion["tipo"] == "total"].groupby(["codigo_ccaa", "fecha"])["generacion_mwh"].sum()
    renovable = tecnologias[tecnologias["tipo"] == "Renovable"].groupby(["codigo_ccaa", "fecha"])["generacion_mwh"].sum()
    resumen = pd.DataFrame({"generacion_total_mwh": totales}).join(renovable.rename("generacion_renovable_mwh"), how="left")
    resumen["generacion_renovable_mwh"] = resumen["generacion_renovable_mwh"].fillna(0.0)
    resumen["pct_renovable"] = (100 * resumen["generacion_renovable_mwh"] / resumen["generacion_total_mwh"]).round(2)
    return resumen.reset_index()


def co2_nacional_mensual(anio_inicio: int = ANIO_INICIO_HISTORIA, anio_fin: int | None = None) -> pd.DataFrame:
    """Emisiones de CO2 del sistema eléctrico (tCO2 eq.), total nacional mensual."""
    anio_fin = anio_fin or dt.date.today().year
    filas = []
    for anio in range(anio_inicio, anio_fin + 1):
        params = {"start_date": _periodo(anio)[0], "end_date": _periodo(anio)[1], "time_trunc": "month"}
        ruta = CARPETA / "co2" / f"{anio}.json"
        datos = _pedir("generacion/no-renovables-detalle-emisiones-CO2", params, ruta, _cerrado(anio))
        for punto in _serie(datos, "Total tCO2 eq.") or _serie(datos, "Total tCO2 eq"):
            filas.append(
                {
                    "fecha": _hora_local(punto["datetime"]).to_period("M").to_timestamp(),
                    "emisiones_co2_tco2eq": float(punto["value"]),
                }
            )
    return pd.DataFrame(filas, columns=["fecha", "emisiones_co2_tco2eq"])


def precios_diarios_historicos(anio_inicio: int = ANIO_INICIO_HISTORIA, anio_fin: int | None = None) -> pd.DataFrame:
    """Precios por día (media del mercado spot y del PVPC, €/MWh) desde REData, mes a mes.

    La API solo funciona con ``time_trunc=hour``: se pide cada mes y se agrega a días.

    Returns:
        DataFrame: fecha (día), precio_spot_eur_mwh, precio_pvpc_eur_mwh.
    """
    anio_fin = anio_fin or dt.date.today().year
    hoy = dt.date.today()
    partes = []
    for anio in range(anio_inicio, anio_fin + 1):
        for mes in range(1, 13):
            if dt.date(anio, mes, 1) > hoy:
                break
            inicio, fin = _periodo(anio, mes)
            params = {"start_date": inicio, "end_date": fin, "time_trunc": "hour"}
            ruta = CARPETA / "precios" / f"{anio}{mes:02d}.json"
            datos = _pedir("mercados/precios-mercados-tiempo-real", params, ruta, _cerrado(anio, mes))
            partes.append(_precios_diarios(datos))
    if not partes:
        return pd.DataFrame(columns=["fecha", "precio_spot_eur_mwh", "precio_pvpc_eur_mwh"])
    return pd.concat(partes, ignore_index=True).sort_values("fecha").reset_index(drop=True)


def _precios_diarios(datos: dict) -> pd.DataFrame:
    """Convierte la respuesta mensual de precios en medias diarias."""
    filas = []
    for nombre, columna in ((NOMBRE_SERIE_SPOT, "precio_spot_eur_mwh"), (NOMBRE_SERIE_PVPC, "precio_pvpc_eur_mwh")):
        for punto in _serie(datos, nombre):
            filas.append(
                {
                    "fecha": _hora_local(punto["datetime"]).normalize(),
                    columna: float(punto["value"]),
                }
            )
    if not filas:
        return pd.DataFrame(columns=["fecha", "precio_spot_eur_mwh", "precio_pvpc_eur_mwh"])
    crudo = pd.DataFrame(filas)
    diario = crudo.groupby("fecha").mean(numeric_only=True).reset_index()
    for columna in ("precio_spot_eur_mwh", "precio_pvpc_eur_mwh"):
        if columna not in diario:
            diario[columna] = pd.NA
    return diario[["fecha", "precio_spot_eur_mwh", "precio_pvpc_eur_mwh"]]


def precios_recientes() -> pd.DataFrame:
    """Precios spot de los últimos 3 días y de mañana (si ya se han publicado), sin caché.

    Returns:
        DataFrame: momento (timestamp con zona), precio_spot_eur_mwh, precio_pvpc_eur_mwh.
    """
    hoy = dt.date.today()
    params = {
        "start_date": (hoy - dt.timedelta(days=2)).isoformat() + "T00:00",
        "end_date": (hoy + dt.timedelta(days=1)).isoformat() + "T23:59",
        "time_trunc": "hour",
    }
    datos = _pedir("mercados/precios-mercados-tiempo-real", params, None, cerrado=False)
    filas = []
    for punto in _serie(datos, NOMBRE_SERIE_SPOT):
        filas.append({"momento": punto["datetime"], "precio_spot_eur_mwh": float(punto["value"])})
    tabla = pd.DataFrame(filas, columns=["momento", "precio_spot_eur_mwh"])
    if not tabla.empty:
        tabla["momento"] = tabla["momento"].map(_hora_local)
    return tabla


def demanda_tiempo_real() -> dict[str, Any]:
    """Última demanda real publicada (MW, sistema peninsular, cada 5 minutos). Sin caché.

    Returns:
        Diccionario con momento y demanda_mw; valores None si no hay dato.
    """
    hoy = dt.date.today()
    # Con time_trunc=hour la API sigue devolviendo los valores cada 5 minutos y evita los 400 intermitentes.
    params = {
        "start_date": (hoy - dt.timedelta(days=1)).isoformat() + "T00:00",
        "end_date": hoy.isoformat() + "T23:59",
        "time_trunc": "hour",
    }
    datos = _pedir("demanda/demanda-tiempo-real", params, None, cerrado=False)
    reales = _serie(datos, "Real")
    if not reales:
        return {"momento": None, "demanda_mw": None}
    ultimo = reales[-1]
    return {"momento": ultimo["datetime"], "demanda_mw": float(ultimo["value"])}
