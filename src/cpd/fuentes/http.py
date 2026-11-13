"""Cliente HTTP común para todas las fuentes de la capa de datos por API.

Responsabilidades:
- Identificarse con un User-Agent del proyecto y usar siempre verificación TLS.
- Reintentar con espera creciente ante timeouts, errores de red, 429 y 5xx.
- Ser "amable" con los servidores: pausa mínima entre peticiones.
- Registrar cada descarga de fichero en data/raw/_registro_descargas.csv.

Nunca se desactiva la verificación SSL (algunos organismos tienen certificados rotos:
en ese caso la fuente se marca como fallida, no se fuerza la conexión).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any

import requests

from cpd.config import RUTA_RAW

USER_AGENT: str = "P3-CPD/1.0 (proyecto academico)"
TIMEOUT_SEGUNDOS: float = 90.0
REINTENTOS: int = 3
PAUSA_MINIMA_SEGUNDOS: float = 0.4
RUTA_API: Path = RUTA_RAW / "api"
REGISTRO: Path = RUTA_RAW / "_registro_descargas.csv"
COLUMNAS_REGISTRO: tuple[str, ...] = ("fecha_descarga", "fuente", "descripcion", "url", "archivo", "tam_kb")

_CABECERAS: dict[str, str] = {"User-Agent": USER_AGENT, "Accept": "application/json, text/csv, */*"}
_ultima_peticion: list[float] = [0.0]
_sesion: requests.Session | None = None


class ErrorFuente(RuntimeError):
    """Fallo al obtener o interpretar datos de una fuente externa."""


def _sesion_http() -> requests.Session:
    """Sesión HTTP reutilizable (conexiones persistentes y cabeceras comunes)."""
    global _sesion
    if _sesion is None:
        _sesion = requests.Session()
        _sesion.headers.update(_CABECERAS)
    return _sesion


def _esperar_turno() -> None:
    """Respeta una pausa mínima entre dos peticiones consecutivas."""
    transcurrido = time.monotonic() - _ultima_peticion[0]
    if transcurrido < PAUSA_MINIMA_SEGUNDOS:
        time.sleep(PAUSA_MINIMA_SEGUNDOS - transcurrido)
    _ultima_peticion[0] = time.monotonic()


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
        espera = 2.0 * intento
        try:
            if metodo == "POST":
                respuesta = _sesion_http().post(url, data=datos, timeout=timeout)
            else:
                respuesta = _sesion_http().get(url, params=params, timeout=timeout)
            if respuesta.status_code < 300:
                return respuesta
            ultimo_error = f"HTTP {respuesta.status_code}: {respuesta.text[:150]!r}"
            if respuesta.status_code == 429:
                espera = 65.0  # límite por minuto: Open-Meteo y otros piden esperar un minuto
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


def leer_cache_json(ruta: Path) -> Any | None:
    """Lee un JSON de la caché local o devuelve None si no existe."""
    if not ruta.exists():
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
