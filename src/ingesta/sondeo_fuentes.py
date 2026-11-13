"""
Sondeo de fuentes: ¿qué datos se pueden recopilar AHORA, sin problemas, y cómo de frescos son?

Hace una petición pequeña a cada fuente (no descarga los datos completos) y comprueba:
  - si responde (código HTTP y tiempo de respuesta),
  - si pide clave o token,
  - la fecha del dato más reciente que publica (frescura).

Escribe el resumen en docs/datos/sondeo_fuentes.csv. Se puede repetir cuando se quiera
(por ejemplo, antes de lanzar una ingesta) para detectar fuentes caídas o desactualizadas.

Uso:  python src/ingesta/sondeo_fuentes.py
"""
import csv
import datetime as dt
import re
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "docs" / "datos" / "sondeo_fuentes.csv"
CABECERAS = {"User-Agent": "P3-CPD/1.0 (proyecto academico)"}
AHORA = dt.datetime.now().astimezone()          # hora local con zona (España)
HOY = AHORA.date()
REDATA = "https://apidatos.ree.es/es/datos"


# --------------------------------------------------------------------------- utilidades
def pedir(url, metodo="GET", timeout=30, **kw):
    """Hace la petición y devuelve (respuesta | None, milisegundos, error | None)."""
    t0 = time.perf_counter()
    try:
        r = requests.request(metodo, url, headers={**CABECERAS, **kw.pop("headers", {})},
                             timeout=timeout, **kw)
        return r, round((time.perf_counter() - t0) * 1000), None
    except requests.exceptions.SSLError:
        return None, round((time.perf_counter() - t0) * 1000), "Certificado SSL no válido"
    except requests.RequestException as e:
        return None, round((time.perf_counter() - t0) * 1000), type(e).__name__


def fecha(texto):
    """Convierte fechas ISO o RFC 1123 (cabeceras HTTP, RSS) en datetime con zona."""
    if not texto:
        return None
    try:
        d = dt.datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            d = parsedate_to_datetime(texto)
        except (TypeError, ValueError):
            return None
    return d if d.tzinfo else d.astimezone()


def edad_horas(d):
    """Horas entre el dato más reciente y ahora (negativo = dato de futuro, p. ej. previsión)."""
    return None if d is None else round((AHORA - d).total_seconds() / 3600, 1)


def resultado(estado, r=None, ms=None, ultimo=None, detalle=""):
    return {"estado": estado, "http": getattr(r, "status_code", ""), "ms": ms,
            "ultimo_dato": ultimo.isoformat(timespec="minutes") if ultimo else "",
            "edad_h": edad_horas(ultimo) if ultimo else "", "detalle": detalle}


def por_clave(r, ms, que_pide):
    """Respuesta típica de una API con clave cuando se llama sin ella.

    Ojo: algunas APIs responden 200 sin clave pero con el cuerpo vacío (AEMET) o con un JSON
    de error; eso también cuenta como "requiere clave".
    """
    if r is None:
        return resultado("Error", detalle="Sin respuesta")
    cuerpo = r.text.strip()
    pide_clave = r.status_code in (401, 403) or not cuerpo or '"estado" : 401' in cuerpo or '"estado":401' in cuerpo
    if pide_clave:
        return resultado("Requiere clave", r, ms, detalle=f"Sin {que_pide} no devuelve datos (HTTP {r.status_code}); {que_pide} gratuito")
    if r.ok:
        return resultado("OK", r, ms, detalle="Devuelve datos sin clave")
    return resultado("Error", r, ms, detalle=f"HTTP {r.status_code}")


def ultima_modificacion(url):
    """Usa la cabecera Last-Modified de un fichero publicado (sin descargarlo)."""
    r, ms, err = pedir(url, "HEAD", allow_redirects=True)
    if err or r is None:
        return resultado("Error", r, ms, detalle=err or "sin respuesta")
    if not r.ok:
        return resultado("Error", r, ms, detalle=f"HTTP {r.status_code}")
    tam = r.headers.get("Content-Length")
    det = f"{int(tam) / 1e6:.1f} MB" if tam and tam.isdigit() else ""
    return resultado("OK", r, ms, fecha(r.headers.get("Last-Modified")), det)


# --------------------------------------------------------------------------- Red Eléctrica (REData)
def redata(ruta, dias, trunc, preferir="real"):
    """Pide los últimos `dias` días de un indicador de REData y devuelve el dato más reciente."""
    ini = (HOY - dt.timedelta(days=dias)).isoformat()
    url = (f"{REDATA}/{ruta}?start_date={ini}T00:00&end_date={HOY.isoformat()}T23:59"
           f"&time_trunc={trunc}")
    r, ms, err = pedir(url)
    if err or r is None:
        return resultado("Error", r, ms, detalle=err)
    if not r.ok:
        return resultado("Error", r, ms, detalle=f"HTTP {r.status_code}")
    series = r.json().get("included", [])
    # Algunos indicadores (p. ej. el balance) agrupan las series dentro de "content"
    series = [sub for s in series for sub in (s.get("attributes", {}).get("content") or [s])]
    ultimos = {}
    for s in series:
        valores = s.get("attributes", {}).get("values", [])
        if valores:
            ultimos[s["attributes"]["title"]] = max(fecha(v["datetime"]) for v in valores)
    if not ultimos:
        return resultado("Sin datos", r, ms, detalle="Respuesta vacía")
    elegido = next((t for t in ultimos if preferir.lower() in t.lower()), None)
    ultimo = ultimos[elegido] if elegido else max(ultimos.values())
    det = f"{len(ultimos)} series; " + ", ".join(list(ultimos)[:4])
    return resultado("OK", r, ms, ultimo, det)


# --------------------------------------------------------------------------- resto de fuentes
def omie():
    """Precio del mercado diario: el de mañana se publica hacia las 13:00 de hoy."""
    base = "https://www.omie.es/es/file-download?parents%5B0%5D=marginalpdbc&filename=marginalpdbc_{}.1"
    for dia in (HOY + dt.timedelta(days=1), HOY):
        r, ms, err = pedir(base.format(dia.strftime("%Y%m%d")))
        if r is not None and r.ok and r.text.startswith("MARGINALPDBC"):
            periodos = sum(1 for ln in r.text.splitlines() if re.match(r"^\d{4};", ln))
            ultimo = dt.datetime.combine(dia, dt.time(23, 59)).astimezone()
            return resultado("OK", r, ms, ultimo, f"Fichero del {dia:%d/%m}: {periodos} periodos de precio")
    return resultado("Error", r, ms, detalle=err or "No se encontró el fichero de hoy ni de mañana")


def open_meteo_actual():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=40.42,41.39,37.39&longitude=-3.70,2.17,-5.98"
           "&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Europe%2FMadrid")
    r, ms, err = pedir(url)
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    datos = r.json()
    lugares = datos if isinstance(datos, list) else [datos]
    t = fecha(lugares[0]["current"]["time"])
    temps = ", ".join(f"{l['current']['temperature_2m']} °C" for l in lugares)
    return resultado("OK", r, ms, t, f"{len(lugares)} puntos en 1 petición (Madrid, Barcelona, Sevilla): {temps}")


def open_meteo_historico():
    fin = HOY - dt.timedelta(days=1)
    url = (f"https://archive-api.open-meteo.com/v1/archive?latitude=40.42&longitude=-3.70"
           f"&start_date={(fin - dt.timedelta(days=10)).isoformat()}&end_date={fin.isoformat()}"
           f"&hourly=temperature_2m&timezone=Europe%2FMadrid")
    r, ms, err = pedir(url)
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    h = r.json()["hourly"]
    con_dato = [t for t, v in zip(h["time"], h["temperature_2m"]) if v is not None]
    ultimo = fecha(con_dato[-1]) if con_dato else None
    return resultado("OK", r, ms, ultimo, "Temperatura horaria ERA5 (reanálisis): sirve para horas de free cooling")


def peeringdb(objeto, texto):
    r, ms, err = pedir(f"https://www.peeringdb.com/api/{objeto}?country=ES")
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    filas = r.json().get("data", [])
    ultimo = max((fecha(f.get("updated")) for f in filas if f.get("updated")), default=None)
    return resultado("OK", r, ms, ultimo, f"{len(filas)} {texto} en España")


def overpass():
    """Cuenta subestaciones de 220/400 kV. Prueba varias instancias públicas (suelen saturarse)."""
    q = ('[out:json][timeout:90];area["ISO3166-1"="ES"][admin_level=2]->.es;'
         'nwr["power"="substation"]["voltage"~"(^|;)(400000|220000)(;|$)"](area.es);out count;')
    fallos = []
    for base in ("https://overpass-api.de/api/interpreter",
                 "https://overpass.kumi.systems/api/interpreter",
                 "https://maps.mail.ru/osm/tools/overpass/api/interpreter"):
        r, ms, err = pedir(base, "POST", timeout=120, data={"data": q})
        if r is not None and r.ok:
            j = r.json()
            total = j["elements"][0]["tags"]["total"] if j.get("elements") else "?"
            return resultado("OK", r, ms, fecha(j.get("osm3s", {}).get("timestamp_osm_base")),
                             f"{total} subestaciones de 220/400 kV en España ({base.split('/')[2]})")
        fallos.append(f"{base.split('/')[2]}: {err or r.status_code}")
    return resultado("Error", r, ms, detalle="Todas las instancias fallan ahora: " + "; ".join(fallos))


def sepe():
    url = ("https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/"
           f"Paro_por_municipios_{HOY.year}_csv.csv")
    r, ms, err = pedir(url, stream=True, timeout=60)
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    meses = set()
    for linea in r.iter_lines():
        m = re.match(rb"^(\d{6});", linea)
        if m:
            meses.add(m.group(1).decode())
    ultimo_mes = max(meses)
    ultimo = dt.datetime(int(ultimo_mes[:4]), int(ultimo_mes[4:]), 1).astimezone()
    return resultado("OK", r, ms, ultimo, f"Último mes publicado: {ultimo_mes[4:]}/{ultimo_mes[:4]} ({len(meses)} meses en el fichero del año)")


def ree_capacidad():
    web = "https://www.ree.es/es/clientes/consumidor/acceso-conexion/conoce-la-capacidad-de-acceso"
    r, ms, err = pedir(web)
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    fechas = sorted(set(re.findall(r"(\d{4})_(\d{2})_(\d{2})_GRT_demanda\.csv", r.text)))
    if not fechas:
        return resultado("Sin datos", r, ms, detalle="No aparece ningún fichero *_GRT_demanda.csv en la web")
    a, m, d = fechas[-1]
    return resultado("OK", r, ms, dt.datetime(int(a), int(m), int(d)).astimezone(),
                     f"Última publicación: {d}/{m}/{a} (en el repo: 03/11/2026)")


def ign_terremotos():
    r, ms, err = pedir("https://www.ign.es/ign/RssTools/sismologia.xml")
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    # La fecha va en el título: "-Info.terremoto: 13/11/2026 7:30:35"
    fechas = [dt.datetime.strptime(f, "%d/%m/%Y %H:%M:%S").astimezone()
              for f in re.findall(r"Info\.terremoto:\s*(\d{2}/\d{2}/\d{4} \d{1,2}:\d{2}:\d{2})", r.text)]
    n = len(re.findall(r"<item>", r.text))
    return resultado("OK", r, ms, max(fechas) if fechas else None,
                     f"{n} terremotos recientes (incluye zonas cercanas fuera de España)")


def snczi():
    url = "https://wms.mapama.gob.es/sig/Agua/ZI_LaminasQ100/wms.aspx?service=WMS&request=GetCapabilities"
    r, ms, err = pedir(url)
    if err:
        return resultado("Error", None, ms, detalle=err + ": usar la descarga de capas del MITECO o datos.gob.es")
    return resultado("OK" if r.ok else "Error", r, ms, detalle="WMS de zonas inundables T=100 años")


def natura2000():
    url = "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer?f=json"
    r, ms, err = pedir(url)
    if err or r is None or not r.ok:
        return resultado("Error", r, ms, detalle=err or f"HTTP {r.status_code}")
    capas = [c.get("name") for c in r.json().get("layers", [])]
    return resultado("OK", r, ms, detalle=f"Servicio ArcGIS de la Agencia Europea de Medio Ambiente; capas: {', '.join(capas[:3])}")


# --------------------------------------------------------------------------- catálogo
# (id, fuente, datos, frecuencia de actualización, acceso, función de sondeo)
FUENTES = [
    ("ree_demanda_tr", "Red Eléctrica · REData", "Demanda peninsular real, prevista y programada",
     "Cada 5 min (288 valores al día)", "API sin clave", lambda: redata("demanda/demanda-tiempo-real", 1, "hour")),
    ("ree_generacion_dia", "Red Eléctrica · REData", "Generación por tecnología",
     "Diaria (día anterior)", "API sin clave", lambda: redata("generacion/estructura-generacion", 7, "day")),
    ("ree_renovable", "Red Eléctrica · REData", "Generación renovable / no renovable",
     "Diaria", "API sin clave", lambda: redata("generacion/evolucion-renovable-no-renovable", 7, "day")),
    ("ree_co2", "Red Eléctrica · REData", "Emisiones CO2 de la generación",
     "Diaria", "API sin clave", lambda: redata("generacion/no-renovables-detalle-emisiones-CO2", 7, "day")),
    ("ree_precios_tr", "Red Eléctrica · REData", "Precio horario PVPC y mercado spot",
     "Spot cada 15 min (incluye mañana); PVPC horario", "API sin clave",
     lambda: redata("mercados/precios-mercados-tiempo-real", 1, "hour", "spot")),
    ("ree_balance", "Red Eléctrica · REData", "Balance eléctrico nacional",
     "Diaria", "API sin clave", lambda: redata("balance/balance-electrico", 7, "day")),
    ("esios", "Red Eléctrica · ESIOS", "Más de 1.900 indicadores (demanda, precios, generación)",
     "Tiempo real (minutos)", "Token gratuito por correo",
     lambda: por_clave(*pedir(f"https://api.esios.ree.es/indicators/1293?start_date={HOY}T00:00&end_date={HOY}T23:59",
                              headers={"Accept": "application/json"})[:2], "token")),
    ("omie", "OMIE", "Precio marginal del mercado diario",
     "Diaria (~13:00 para el día siguiente)", "Ficheros públicos", omie),
    ("ree_capacidad", "Red Eléctrica", "Capacidad de acceso de demanda por nudo",
     "Mensual", "CSV público", ree_capacidad),
    ("aemet", "AEMET OpenData", "Observación de estaciones (temperatura, humedad, viento)",
     "Horaria", "Clave gratuita por correo",
     lambda: por_clave(*pedir("https://opendata.aemet.es/opendata/api/observacion/convencional/todas")[:2], "api_key")),
    ("open_meteo", "Open-Meteo", "Tiempo actual y previsión por coordenadas",
     "Cada 15 min (modelos meteorológicos)", "API sin clave (uso no comercial)", open_meteo_actual),
    ("open_meteo_hist", "Open-Meteo (ERA5)", "Temperatura horaria histórica",
     "Diaria (hasta ayer)", "API sin clave (uso no comercial)", open_meteo_historico),
    ("miteco_embalses", "MITECO · Boletín Hidrológico", "Reserva de embalses",
     "Semanal (martes)", "Fichero público",
     lambda: ultima_modificacion("https://www.miteco.gob.es/content/dam/miteco/es/agua/temas/evaluacion-de-los-recursos-hidricos/boletin-hidrologico/Historico-de-embalses/BD-Embalses.zip")),
    ("ign_terremotos", "IGN · Sismología", "Últimos terremotos (fecha, magnitud, lugar)",
     "Continua (minutos)", "RSS público", ign_terremotos),
    ("sepe", "SEPE", "Paro registrado por municipio",
     "Mensual (primeros días del mes)", "CSV público", sepe),
    ("peeringdb_fac", "PeeringDB", "Centros de datos existentes (para la etiqueta del ML)",
     "Continua", "API sin clave (límite por minuto)", lambda: peeringdb("fac", "centros de datos")),
    ("peeringdb_ix", "PeeringDB", "Puntos neutros de Internet (IXP)",
     "Continua", "API sin clave (límite por minuto)", lambda: peeringdb("ix", "puntos neutros")),
    ("osm", "OpenStreetMap · Overpass", "Subestaciones de 220/400 kV",
     "Continua (minutos)", "API sin clave (uso moderado)", overpass),
    ("osm_geofabrik", "OpenStreetMap · Geofabrik", "Extracto completo de España (.osm.pbf)",
     "Diaria", "Fichero público",
     lambda: ultima_modificacion("https://download.geofabrik.de/europe/spain-latest.osm.pbf")),
    ("ine_padron", "INE", "Padrón municipal (CSV de la tabla 29005)",
     "Anual", "CSV público", lambda: ultima_modificacion("https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/29005.csv")),
    ("ine_renta", "INE", "Atlas de Distribución de Renta (tabla 30824)",
     "Anual", "CSV público", lambda: ultima_modificacion("https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/30824.csv")),
    ("gisco", "Eurostat GISCO", "Límites municipales LAU",
     "Anual", "Fichero público", lambda: ultima_modificacion("https://gisco-services.ec.europa.eu/distribution/v2/lau/csv/LAU_RG_01M_2024_4326.csv")),
    ("snczi", "MITECO · SNCZI", "Zonas inundables (WMS)",
     "Irregular", "Servicio público", snczi),
    ("natura2000", "EEA · Natura 2000", "Espacios protegidos (servicio de mapas)",
     "Anual", "Servicio público", natura2000),
]


def main():
    filas = []
    for ident, fuente, datos, frecuencia, acceso, sondeo in FUENTES:
        try:
            res = sondeo()
        except Exception as e:  # una fuente rota no debe parar el sondeo del resto
            res = resultado("Error", detalle=f"{type(e).__name__}: {e}")
        fila = {"id": ident, "fuente": fuente, "datos": datos, "frecuencia": frecuencia,
                "acceso": acceso, **res}
        filas.append(fila)
        print(f"[{fila['estado']:<14}] {ident:<18} {str(fila['ms']):>6} ms  "
              f"último: {fila['ultimo_dato'] or '-':<22} {fila['detalle']}")
        time.sleep(0.5)  # cortesía con los servidores públicos

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]) + ["sondeo"])
        w.writeheader()
        for fila in filas:
            w.writerow({**fila, "sondeo": AHORA.isoformat(timespec="minutes")})
    ok = sum(f["estado"] == "OK" for f in filas)
    print(f"\n{ok}/{len(filas)} fuentes accesibles ahora mismo. Resumen en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
