"""
03 - Energía.

Variables del enunciado que cubre:
  producción eléctrica disponible, consumo (demanda), % renovables,
  capacidad de la red (capacidad de acceso para nueva demanda por nudo).

Fuentes:
  - Red Eléctrica (REE), API REData (apidatos.ree.es):
      demanda eléctrica mensual por comunidad autónoma (2015-hoy)
      estructura de generación mensual por comunidad (por tecnología)
    La API solo deja pedir un año cada vez, así que se guarda un JSON
    por comunidad y año (tal cual llega = capa raw).
  - REE: capacidad de acceso de DEMANDA en los nudos de la red de transporte
    (publicada mensualmente desde feb-2026). Es exactamente la pregunta
    "¿hay potencia disponible para conectar un CPD aquí?".

Limitación conocida: no hay datos abiertos de consumo eléctrico POR MUNICIPIO
para toda España (solo Cataluña y algunas ciudades). Se trabajará a nivel
comunidad autónoma y se repartirá por municipio en la fase de transformación.
"""
import datetime as dt
import json
import sys
import time

import requests

from utils import CABECERAS, RAW, _anotar, descargar

DESTINO = RAW / "energia"
API = "https://apidatos.ree.es/es/datos"

# Identificadores de comunidad autónoma en la API de REE
CCAA_REE = {
    4: "Andalucía", 5: "Aragón", 6: "Cantabria", 7: "Castilla-La Mancha",
    8: "Castilla y León", 9: "Cataluña", 10: "País Vasco", 11: "Asturias",
    13: "Madrid", 14: "Navarra", 15: "Comunitat Valenciana", 16: "Extremadura",
    17: "Galicia", 20: "La Rioja", 21: "Murcia", 8742: "Canarias",
    8743: "Illes Balears", 8744: "Ceuta", 8745: "Melilla",
}
INDICADORES = {
    "demanda": "demanda/evolucion",
    "generacion": "generacion/estructura-generacion",
}
ANIO_INICIO = 2015


def _pedir(indicador, geo_id, anio, hoy):
    """Descarga un año de una comunidad. Devuelve un aviso si falla."""
    destino = DESTINO / "ree" / indicador / f"{geo_id}_{anio}.json"
    # El año en curso se vuelve a pedir siempre (va creciendo)
    if destino.exists() and anio < hoy.year:
        return None
    url = (f"{API}/{INDICADORES[indicador]}?start_date={anio}-01-01T00:00&end_date={anio}-12-31T23:59"
           f"&time_trunc=month&geo_trunc=electric_system&geo_limit=ccaa&geo_ids={geo_id}")
    for intento in range(3):
        try:
            r = requests.get(url, headers=CABECERAS, timeout=60)
            if r.ok and "errors" not in r.json():
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(r.text, encoding="utf-8")
                return None
        except requests.RequestException:
            pass
        time.sleep(2 * (intento + 1))
    return f"[aviso] sin datos: {indicador} {CCAA_REE[geo_id]} {anio}"


def bajar_ree(indicador: str):
    """Pide todas las combinaciones comunidad x año, 6 peticiones a la vez."""
    from concurrent.futures import ThreadPoolExecutor
    hoy = dt.date.today()
    tareas = [(indicador, g, a, hoy) for g in CCAA_REE for a in range(ANIO_INICIO, hoy.year + 1)]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for aviso in ex.map(lambda t: _pedir(*t), tareas):
            if aviso:
                print(aviso)
    n = len(list((DESTINO / "ree" / indicador).glob("*.json")))
    print(f"[ok] {indicador}: {n} ficheros")
    _anotar("Red Eléctrica (REData API)", f"{indicador} mensual por CCAA {ANIO_INICIO}-hoy (1 JSON por CCAA y año)",
            f"{API}/{INDICADORES[indicador]}", DESTINO / "ree" / indicador, 0)


if __name__ == "__main__":
    # Se puede lanzar por partes: python 03_energia.py demanda | generacion | capacidad
    partes = sys.argv[1:] or ["capacidad", "demanda", "generacion"]

    if "capacidad" in partes:
        # El nombre del fichero lleva la fecha de publicación; se busca el último en la web de REE
        import re
        web = "https://www.ree.es/es/clientes/consumidor/acceso-conexion/conoce-la-capacidad-de-acceso"
        html = requests.get(web, headers=CABECERAS, timeout=60).text
        rutas = sorted(set(re.findall(r'/sites/default/files/[^"]+_GRT_demanda\.csv', html)))
        url = "https://www.ree.es" + rutas[-1]
        descargar(url, DESTINO / ("ree_capacidad_acceso_demanda_" + url.split("/")[-1]),
                  "Red Eléctrica", "Capacidad de acceso de demanda por nudo de la red de transporte")

    for ind in ("demanda", "generacion"):
        if ind in partes:
            bajar_ree(ind)
