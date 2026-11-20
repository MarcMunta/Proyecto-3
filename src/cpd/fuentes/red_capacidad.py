"""Red Eléctrica: capacidad de acceso a la red de transporte (nudos) para DEMANDA, por comunidad autónoma.

Fuente: página de REE "Conoce la capacidad de acceso" (https://www.ree.es/es/clientes/consumidor/acceso-conexion/conoce-la-capacidad-de-acceso).
Se descarga el CSV mensual más reciente (``*_GRT_demanda.csv``). No tiene coordenadas: el
dato es por nudo (subestación) y se agrega a comunidad autónoma. Las provincias heredan el
valor de su comunidad (nivel ``ccaa``).

Columnas usadas (MW, red de transporte, demanda):
- "disponible para solicitudes, criterio general": lo que queda libre para nueva demanda.
- "otorgada demanda RdT": lo que REE ya ha concedido a nuevos consumos (centros de datos, industria, hidrógeno).
- "solicitada en curso y pendiente resolver demanda RdT": lo que se ha pedido y está en trámite.
Las dos últimas son la huella real de dónde se están instalando los grandes consumos.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, descargar_archivo, pedir
from cpd.fuentes.provincias import CCAA_INE

FUENTE: str = "Red Eléctrica (capacidad de acceso)"
PAGINA: str = "https://www.ree.es/es/clientes/consumidor/acceso-conexion/conoce-la-capacidad-de-acceso"
CARPETA: Path = RUTA_API / "ree_capacidad"
PATRON_ENLACE: str = r'/sites/default/files/[^"\s]+_GRT_demanda\.csv'
NOMBRES_CCAA_REE: dict[str, str] = {
    "Andalucía": "01", "Aragón": "02", "Principado de Asturias": "03", "Islas Baleares": "04", "Illes Balears": "04",
    "Canarias": "05", "Cantabria": "06", "Castilla y León": "07", "Castilla-La Mancha": "08", "Cataluña": "09",
    "Comunitat Valenciana": "10", "Comunidad Valenciana": "10", "Extremadura": "11", "Galicia": "12",
    "Comunidad de Madrid": "13", "Región de Murcia": "14", "Comunidad Foral de Navarra": "15", "País Vasco": "16",
    "La Rioja": "17", "Ceuta": "18", "Melilla": "19",
}


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.replace("�", "?"))
    return "".join(ch for ch in sin_tildes.encode("ascii", "ignore").decode("ascii").lower() if ch.isalpha())


def codigo_ccaa_de_texto(texto: str) -> str | None:
    """Código INE de comunidad a partir del nombre que usa REE (tolerante a caracteres rotos)."""
    if not isinstance(texto, str) or not texto.strip():
        return None
    if texto.strip() in NOMBRES_CCAA_REE:
        return NOMBRES_CCAA_REE[texto.strip()]
    objetivo = _normalizar(texto)
    candidatos = {_normalizar(nombre): codigo for nombre, codigo in NOMBRES_CCAA_REE.items()}
    if objetivo in candidatos:
        return candidatos[objetivo]
    mejor = difflib.get_close_matches(objetivo, list(candidatos), n=1, cutoff=0.8)
    return candidatos[mejor[0]] if mejor else None


def ultimo_enlace_csv() -> str:
    """URL del CSV de demanda más reciente publicado por REE (busca en la página de capacidad de acceso)."""
    html = pedir(PAGINA, etiqueta=FUENTE).text
    enlaces = sorted(set(re.findall(PATRON_ENLACE, html)))
    if not enlaces:
        raise ErrorFuente(f"{FUENTE}: no se encuentra ningún CSV '*_GRT_demanda.csv' en la página de REE")
    return "https://www.ree.es" + enlaces[-1]


def descargar_ultimo() -> Path:
    """Descarga (si no está ya) el CSV de capacidad de acceso más reciente y devuelve su ruta."""
    url = ultimo_enlace_csv()
    destino = CARPETA / url.rsplit("/", 1)[-1]
    return descargar_archivo(url, destino, FUENTE, "Capacidad de acceso de demanda por nudo (GRT)")


def _columna_demanda_rdt(cabecera_grupo: list[str], subcabecera: list[str]) -> int:
    """Índice de la columna 'DEMANDA' bajo el grupo 'DISPONIBLE ... CRITERIO GENERAL RDT'."""
    grupo_actual = ""
    for indice, (grupo, sub) in enumerate(zip(cabecera_grupo, subcabecera)):
        if grupo:
            grupo_actual = grupo
        texto = grupo_actual.upper()
        if "DISPONIBLE" in texto and "GENERAL" in texto and "RDT" in texto and "RDD" not in texto:
            if sub.strip().upper() == "DEMANDA":
                return indice
    raise ErrorFuente(f"{FUENTE}: no se encuentra la columna de capacidad disponible para demanda en RdT")


# Subcabeceras (texto exacto de REE) de la capacidad para DEMANDA en la red de transporte ya otorgada y la solicitada
# que aún está en trámite.
SUBCABECERA_OTORGADA: str = "Capacidad de acceso otorgada demanda RdT"
SUBCABECERA_PENDIENTE: str = "Capacidad de acceso solicitada en curso y pendiente resolver demanda RdT"


def _columna_por_subcabecera(subcabecera: list[str], texto: str) -> int | None:
    """Índice de la columna cuya subcabecera es `texto` (sin distinguir espacios ni mayúsculas), o None."""
    objetivo = " ".join(texto.lower().split())
    for indice, sub in enumerate(subcabecera):
        if " ".join(str(sub).lower().split()) == objetivo:
            return indice
    return None


def leer_capacidad(ruta: Path) -> pd.DataFrame:
    """Lee el CSV de REE y devuelve, por comunidad, nº de nudos y capacidad para demanda en la red de transporte (MW):
    disponible para nuevas solicitudes, ya otorgada y solicitada en trámite.

    Si una versión del CSV no trae las columnas de otorgada o pendiente, quedan en NaN (no se inventan).

    Returns:
        DataFrame: codigo_ccaa, ccaa, nudos, capacidad_demanda_rdt_disponible_mw, capacidad_demanda_rdt_otorgada_mw,
        capacidad_demanda_rdt_pendiente_mw.
    """
    contenido = ruta.read_bytes()
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    import io

    crudo = pd.read_csv(io.StringIO(texto), sep=";", header=None, dtype=str, keep_default_na=False)
    grupos = crudo.iloc[0].tolist()
    subcabeceras = crudo.iloc[1].tolist()
    columna = _columna_demanda_rdt(grupos, subcabeceras)
    datos = crudo.iloc[2:].copy()
    datos = datos[datos.iloc[:, 0].str.strip() != ""]
    numero = lambda indice: pd.to_numeric(datos.iloc[:, indice].str.replace(",", ".", regex=False), errors="coerce")  # noqa: E731
    datos["codigo_ccaa"] = datos.iloc[:, 2].map(codigo_ccaa_de_texto)
    datos["valor"] = numero(columna)
    for nombre, subcabecera in (("otorgada", SUBCABECERA_OTORGADA), ("pendiente", SUBCABECERA_PENDIENTE)):
        indice = _columna_por_subcabecera(subcabeceras, subcabecera)
        datos[nombre] = numero(indice) if indice is not None else float("nan")
    datos = datos.dropna(subset=["codigo_ccaa"])
    agregado = (
        datos.groupby("codigo_ccaa")
        .agg(
            nudos=(datos.columns[0], "size"),
            capacidad_demanda_rdt_disponible_mw=("valor", "sum"),
            capacidad_demanda_rdt_otorgada_mw=("otorgada", lambda s: s.sum(min_count=1)),
            capacidad_demanda_rdt_pendiente_mw=("pendiente", lambda s: s.sum(min_count=1)),
        )
        .reset_index()
    )
    agregado["ccaa"] = agregado["codigo_ccaa"].map(CCAA_INE)
    columnas = ["capacidad_demanda_rdt_disponible_mw", "capacidad_demanda_rdt_otorgada_mw", "capacidad_demanda_rdt_pendiente_mw"]
    agregado[columnas] = agregado[columnas].round(1)
    return agregado[["codigo_ccaa", "ccaa", "nudos", *columnas]]
