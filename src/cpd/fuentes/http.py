"""Cliente HTTP común para todas las fuentes de la capa de datos por API.

Responsabilidades:
- Identificarse con un User-Agent del proyecto y usar siempre verificación TLS.
- Reintentar con backoff exponencial y jitter (espera = base · 2^n + azar) ante timeouts, errores de red,
  429 y 5xx, respetando la cabecera Retry-After si el servidor la envía (clase 27/11, Retries).
- Ser "amable" con los servidores: pausa mínima entre peticiones, también con varios hilos (rate limiting).
- Caché local con TTL: lo estático se reutiliza siempre y lo semiestático solo mientras no caduque.
- Paralelizar peticiones independientes con un número máximo de hilos (`en_paralelo`).
- Registrar cada descarga de fichero en data/raw/_registro_descargas.csv (trazabilidad).

Nunca se desactiva la verificación SSL (algunos organismos tienen certificados rotos:
en ese caso la fuente se marca como fallida, no se fuerza la conexión).
"""

from __future__ import annotations

import csv
import datetime as dt
import email.utils
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

import requests

from cpd.config import RUTA_RAW

USER_AGENT: str = "P3-CPD/1.0 (proyecto academico)"
TIMEOUT_SEGUNDOS: float = 90.0
REINTENTOS: int = 3
PAUSA_MINIMA_SEGUNDOS: float = 0.4
BACKOFF_BASE_SEGUNDOS: float = 2.0
BACKOFF_MAXIMO_SEGUNDOS: float = 60.0
JITTER: float = 0.25  # hasta un 25 % extra al azar para que los clientes no reintenten a la vez
ESPERA_429_SEGUNDOS: float = 65.0  # sin Retry-After: Open-Meteo y otros limitan por minuto
HILOS_MAXIMOS: int = 4
RUTA_API: Path = RUTA_RAW / "api"
REGISTRO: Path = RUTA_RAW / "_registro_descargas.csv"
COLUMNAS_REGISTRO: tuple[str, ...] = ("fecha_descarga", "fuente", "descripcion", "url", "archivo", "tam_kb")

_CABECERAS: dict[str, str] = {"User-Agent": USER_AGENT, "Accept": "application/json, text/csv, */*"}
_ultima_peticion: list[float] = [0.0]
_cerrojo_turno = threading.Lock()
_local = threading.local()  # una sesión por hilo: requests.Session no es segura entre hilos
T = TypeVar("T")
R = TypeVar("R")


class ErrorFuente(RuntimeError):
    """Fallo al obtener o interpretar datos de una fuente externa."""


def _sesion_http() -> requests.Session:
    """Sesión HTTP reutilizable del hilo actual (conexiones persistentes y cabeceras comunes)."""
    sesion = getattr(_local, "sesion", None)
    if sesion is None:
        sesion = requests.Session()
        sesion.headers.update(_CABECERAS)
        _local.sesion = sesion
    return sesion


def _esperar_turno() -> None:
    """Respeta una pausa mínima entre dos peticiones consecutivas, aunque vengan de hilos distintos."""
    with _cerrojo_turno:
        transcurrido = time.monotonic() - _ultima_peticion[0]
        if transcurrido < PAUSA_MINIMA_SEGUNDOS:
            time.sleep(PAUSA_MINIMA_SEGUNDOS - transcurrido)
        _ultima_peticion[0] = time.monotonic()


def espera_backoff(intento: int, base: float = BACKOFF_BASE_SEGUNDOS, maximo: float = BACKOFF_MAXIMO_SEGUNDOS,
                   jitter: float = JITTER, azar: Callable[[], float] = random.random) -> float:
    """Segundos de espera antes del reintento `intento` (1, 2, 3…): base · 2^(intento-1), con tope y jitter.

    Con base 2 s: 2, 4, 8, 16… s, más hasta un `jitter` (fracción) al azar, sin pasar de `maximo`.
    """
    espera = min(maximo, base * 2 ** (intento - 1))
    return min(maximo, espera * (1 + jitter * azar()))


def espera_retry_after(respuesta: requests.Response) -> float | None:
    """Segundos que pide el servidor en la cabecera Retry-After (número o fecha HTTP), o None."""
    valor = (getattr(respuesta, "headers", None) or {}).get("Retry-After")
    if not valor:
        return None
    try:
        return max(0.0, float(valor))
    except ValueError:
        pass
    try:
        fecha = email.utils.parsedate_to_datetime(valor)
    except (TypeError, ValueError):
        return None
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=dt.timezone.utc)
    return max(0.0, (fecha - dt.datetime.now(dt.timezone.utc)).total_seconds())


def en_paralelo(funcion: Callable[[T], R], elementos: Iterable[T], hilos: int = HILOS_MAXIMOS) -> list[R]:
    """Aplica `funcion` a cada elemento con varios hilos y devuelve los resultados en el mismo orden.

    Sirve para peticiones independientes (trabajo de E/S: casi todo el tiempo se espera a la red). El número de
    hilos es el límite de peticiones simultáneas; la pausa mínima de `_esperar_turno` se sigue respetando.
    Si un elemento falla, se lanza su excepción (las fuentes la aíslan en `actualizar._paso`).
    """
    lista = list(elementos)
    if hilos <= 1 or len(lista) <= 1:
        return [funcion(x) for x in lista]
    with ThreadPoolExecutor(max_workers=min(hilos, len(lista)), thread_name_prefix="p3-http") as grupo:
        return list(grupo.map(funcion, lista))


def pedir(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    datos: dict[str, Any] | None = None,
    metodo: str = "GET",
    reintentos: int = REINTENTOS,
    timeout: float = TIMEOUT_SEGUNDOS,
    etiqueta: str = "",
) -> requests.Response:
    """Hace una petición con reintentos. Lanza ErrorFuente si no se consigue respuesta válida.

    Args:
        url: dirección a consultar.
        params: parámetros de la query string.
        datos: cuerpo del formulario (para POST, por ejemplo Overpass).
        metodo: "GET" o "POST".
        reintentos: número total de intentos.
        timeout: segundos de espera máxima por intento.
        etiqueta: texto corto para los mensajes de error (nombre de la fuente).

    Returns:
        La respuesta HTTP con código 2xx.
    """
    ultimo_error = "sin respuesta"
    for intento in range(1, reintentos + 1):
        _esperar_turno()
        espera = espera_backoff(intento)
        try:
            if metodo == "POST":
                respuesta = _sesion_http().post(url, data=datos, timeout=timeout)
            else:
                respuesta = _sesion_http().get(url, params=params, timeout=timeout)
            if respuesta.status_code < 300:
                return respuesta
            ultimo_error = f"HTTP {respuesta.status_code}: {respuesta.text[:150]!r}"
            pedida = espera_retry_after(respuesta)
            if respuesta.status_code == 429:
                espera = pedida if pedida is not None else ESPERA_429_SEGUNDOS
            elif pedida is not None and respuesta.status_code == 503:
                espera = pedida
            elif respuesta.status_code not in (400, 408) and respuesta.status_code < 500:
                break  # error definitivo (404, 403...): no tiene sentido reintentar
        except requests.Timeout:
            ultimo_error = f"tiempo de espera agotado ({timeout:.0f} s)"
        except requests.RequestException as error:
            ultimo_error = f"error de red: {error}"
        if intento < reintentos:
            time.sleep(espera)
    raise ErrorFuente(f"{etiqueta or url}: {ultimo_error}")


def json_de(url: str, *, params: dict[str, Any] | None = None, etiqueta: str = "", **kwargs: Any) -> Any:
    """Pide una URL y devuelve su JSON. Lanza ErrorFuente si la respuesta no es JSON."""
    respuesta = pedir(url, params=params, etiqueta=etiqueta, **kwargs)
    try:
        return respuesta.json()
    except ValueError as error:
        raise ErrorFuente(f"{etiqueta or url}: la respuesta no es JSON válido") from error


def cache_vigente(ruta: Path, ttl_horas: float | None = None) -> bool:
    """True si el fichero de caché existe y, con `ttl_horas`, no ha caducado (None = no caduca nunca)."""
    if not ruta.exists():
        return False
    if ttl_horas is None:
        return True
    return (time.time() - ruta.stat().st_mtime) < ttl_horas * 3600


def leer_cache_json(ruta: Path, ttl_horas: float | None = None) -> Any | None:
    """Lee un JSON de la caché local o devuelve None si no existe o si ha caducado (`ttl_horas`)."""
    if not cache_vigente(ruta, ttl_horas):
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_cache_json(ruta: Path, datos: Any) -> None:
    """Escribe un JSON en la caché local creando las carpetas necesarias."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def registrar(fuente: str, descripcion: str, url: str, destino: Path, tam_kb: float) -> None:
    """Añade una línea al registro de descargas (formato del proyecto)."""
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not REGISTRO.exists()
    with REGISTRO.open("a", newline="", encoding="utf-8") as fichero:
        escritor = csv.writer(fichero)
        if nuevo:
            escritor.writerow(COLUMNAS_REGISTRO)
        try:
            archivo = destino.relative_to(RUTA_RAW.parent.parent).as_posix()
        except ValueError:
            archivo = str(destino)
        escritor.writerow(
            [dt.datetime.now().isoformat(timespec="seconds"), fuente, descripcion, url, archivo, round(tam_kb)]
        )


def descargar_archivo(url: str, destino: Path, fuente: str, descripcion: str, forzar: bool = False) -> Path:
    """Descarga un fichero en streaming a `destino` (vía .part) si no existe ya, y lo registra."""
    if destino.exists() and not forzar:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    _esperar_turno()
    tmp = destino.with_name(destino.name + ".part")
    try:
        with _sesion_http().get(url, stream=True, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            respuesta.raise_for_status()
            with tmp.open("wb") as fichero:
                for trozo in respuesta.iter_content(chunk_size=1 << 20):
                    fichero.write(trozo)
    except requests.RequestException as error:
        tmp.unlink(missing_ok=True)
        raise ErrorFuente(f"{fuente}: no se pudo descargar {url}: {error}") from error
    tmp.replace(destino)
    registrar(fuente, descripcion, url, destino, destino.stat().st_size / 1024)
    return destino
