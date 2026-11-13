"""Subestaciones eléctricas de alta tensión (220 y 400 kV) desde OpenStreetMap (Overpass API).

Overpass es intermitente (502/504 y tiempos de espera largos): se prueban varios servidores
espejo, cada respuesta se cachea en data/raw/api/overpass/ y, si todos fallan, la función
lanza ErrorFuente (el resto de fuentes sigue). Los datos de OSM son colaborativos: el
recuento es una aproximación por lo mapeado, no un inventario oficial de REE.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, guardar_cache_json, leer_cache_json, pedir, registrar
from cpd.fuentes.provincias import PROVINCIAS, provincia_de_punto

FUENTE: str = "OpenStreetMap (Overpass)"
CARPETA: Path = RUTA_API / "overpass"
SERVIDORES: tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)
# Cajas (sur, oeste, norte, este) que cubren la España peninsular y Baleares, y Canarias.
CAJAS: dict[str, tuple[float, float, float, float]] = {
    "peninsula_baleares": (35.0, -9.6, 44.0, 4.6),
    "canarias": (27.5, -18.3, 29.5, -13.3),
}
TIMEOUT_CONSULTA_S: int = 180


def consulta_overpass(caja: tuple[float, float, float, float]) -> str:
    """Consulta Overpass QL: subestaciones con voltaje 220 o 400 kV dentro de la caja."""
    sur, oeste, norte, este = caja
    return (
        f"[out:json][timeout:{TIMEOUT_CONSULTA_S}];"
        f"(nwr[\"power\"=\"substation\"][\"voltage\"~\"(^|;)(220000|400000)(;|$)\"]({sur},{oeste},{norte},{este}););"
        "out center tags;"
    )


def _pedir_caja(nombre: str, caja: tuple[float, float, float, float]) -> dict:
    """Respuesta Overpass para una caja, de caché o de un servidor espejo."""
    ruta = CARPETA / f"{nombre}.json"
    cache = leer_cache_json(ruta)
    if cache is not None:
        return cache
    consulta = consulta_overpass(caja)
    ultimo_error = "sin respuesta"
    for servidor in SERVIDORES:
        try:
            respuesta = pedir(
                servidor,
                metodo="POST",
                datos={"data": consulta},
                reintentos=1,
                timeout=TIMEOUT_CONSULTA_S + 30,
                etiqueta=f"{FUENTE} {servidor}",
            )
            datos = json.loads(respuesta.text)
            if "elements" in datos:
                guardar_cache_json(ruta, datos)
                registrar(FUENTE, f"Subestaciones 220/400 kV ({nombre})", servidor, ruta, ruta.stat().st_size / 1024)
                return datos
            ultimo_error = "respuesta sin 'elements'"
        except (ErrorFuente, ValueError) as error:
            ultimo_error = str(error)
    raise ErrorFuente(f"{FUENTE}: ningún servidor respondió para {nombre}: {ultimo_error}")


def subestaciones_por_provincia(poligonos: dict) -> pd.DataFrame:
    """Nº de subestaciones 220 kV y 400 kV (mapeadas en OSM) por provincia.

    Returns:
        DataFrame: codigo_provincia, subestaciones_220_400kv, subestaciones_400kv.
    """
    elementos: dict[str, dict] = {}
    for nombre, caja in CAJAS.items():
        for elemento in _pedir_caja(nombre, caja).get("elements", []):
            elementos[f"{elemento.get('type')}/{elemento.get('id')}"] = elemento
    return contar_por_provincia(list(elementos.values()), poligonos)


def contar_por_provincia(elementos: list[dict], poligonos: dict) -> pd.DataFrame:
    """Cuenta elementos de Overpass por provincia según su centro geográfico y su voltaje."""
    conteos = {p.codigo: {"total": 0, "400": 0} for p in PROVINCIAS}
    for elemento in elementos:
        lat = elemento.get("lat", (elemento.get("center") or {}).get("lat"))
        lon = elemento.get("lon", (elemento.get("center") or {}).get("lon"))
        codigo = provincia_de_punto(lat, lon, poligonos)
        if codigo is None:
            continue
        voltajes = str(elemento.get("tags", {}).get("voltage", ""))
        conteos[codigo]["total"] += 1
        if "400000" in voltajes:
            conteos[codigo]["400"] += 1
    return pd.DataFrame(
        [
            {
                "codigo_provincia": codigo,
                "subestaciones_220_400kv": valor["total"],
                "subestaciones_400kv": valor["400"],
            }
            for codigo, valor in conteos.items()
        ]
    )
