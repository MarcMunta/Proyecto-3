"""
Utilidades comunes para la fase de INGESTA (la "E" de ETL: Extract).

Idea clave: aquí solo DESCARGAMOS los datos tal cual vienen de la fuente
y los guardamos en data/raw/ (la capa "raw" o "bronze" del Data Lake).
No se limpia ni se transforma nada: eso se hace después, en otra fase.

Cada descarga queda anotada en data/raw/_registro_descargas.csv
(fuente, URL, fecha, tamaño). Ese registro sirve luego para el
"Informe de origen de datos" que pide el enunciado.
"""
import csv
import datetime as dt
from pathlib import Path

import requests

# Carpeta raíz del proyecto (dos niveles por encima de este archivo)
RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
REGISTRO = RAW / "_registro_descargas.csv"

# Algunas webs públicas rechazan peticiones sin un User-Agent de navegador
CABECERAS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) P3-CPD/1.0"}


def descargar(url: str, destino: Path, fuente: str, descripcion: str, forzar: bool = False) -> Path:
    """Descarga `url` en `destino` y lo apunta en el registro.

    Si el archivo ya existe no se vuelve a descargar (salvo forzar=True).
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and not forzar:
        print(f"[ya existe] {destino.relative_to(RAIZ)}")
        return destino

    print(f"[descargando] {url}")
    with requests.get(url, headers=CABECERAS, stream=True, timeout=120) as r:
        r.raise_for_status()
        # Se escribe en un .part y se renombra al final: si la descarga se corta,
        # no queda un archivo incompleto con el nombre bueno.
        tmp = destino.with_name(destino.name + ".part")
        with open(tmp, "wb") as f:
            for trozo in r.iter_content(chunk_size=1 << 20):
                f.write(trozo)
        tmp.replace(destino)

    tam_kb = destino.stat().st_size / 1024
    print(f"[ok] {destino.relative_to(RAIZ)} ({tam_kb:,.0f} KB)")
    _anotar(fuente, descripcion, url, destino, tam_kb)
    return destino


def _anotar(fuente, descripcion, url, destino, tam_kb):
    nuevo = not REGISTRO.exists()
    with open(REGISTRO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha_descarga", "fuente", "descripcion", "url", "archivo", "tam_kb"])
        w.writerow([
            dt.datetime.now().isoformat(timespec="seconds"),
            fuente, descripcion, url,
            destino.relative_to(RAIZ).as_posix(), round(tam_kb),
        ])


def descargar_filtrado(url: str, destino: Path, fuente: str, descripcion: str,
                       quedarse_con, forzar: bool = False) -> Path:
    """Como descargar(), pero va leyendo línea a línea y solo guarda las que
    cumplen `quedarse_con(linea)` (más la cabecera).

    Se usa con ficheros enormes de los que solo necesitamos una parte
    (p. ej. el Atlas de Renta del INE, que trae cada sección censal de España
    y a nosotros solo nos interesa el nivel municipio).
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not forzar:
        print(f"[ya existe] {destino.relative_to(RAIZ)}")
        return destino

    print(f"[descargando y filtrando] {url}")
    leidas = guardadas = 0
    with requests.get(url, headers=CABECERAS, stream=True, timeout=300) as r:
        r.raise_for_status()
        # Se escribe en un .part y se renombra al final: si la descarga se corta,
        # no queda un archivo incompleto con el nombre bueno.
        tmp = destino.with_name(destino.name + ".part")
        with open(tmp, "wb") as f:
            for i, linea in enumerate(r.iter_lines(chunk_size=1 << 20)):
                leidas += 1
                if i == 0 or quedarse_con(linea.decode("utf-8-sig", errors="replace")):
                    f.write(linea + b"\n")
                    guardadas += 1
        tmp.replace(destino)

    tam_kb = destino.stat().st_size / 1024
    print(f"[ok] {destino.relative_to(RAIZ)} ({tam_kb:,.0f} KB, {guardadas:,} de {leidas:,} líneas)")
    _anotar(fuente, descripcion + " [filtrado a nivel municipio]", url, destino, tam_kb)
    return destino
