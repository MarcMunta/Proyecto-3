"""Reservas hídricas: embalses semanales del MITECO por ámbito hidrográfico.

Fuente: base de datos histórica de embalses del Boletín Hidrológico (MITECO), en un zip con un
fichero Microsoft Access (.mdb). Tabla ``T_Datos Embalses 1988-2026``: FECHA (semanal, desde 1988),
AMBITO_NOMBRE, EMBALSE_NOMBRE, AGUA_TOTAL (capacidad, hm³) y AGUA_ACTUAL (volumen embalsado, hm³).
Se lee con ``access-parser`` (Python puro, sin driver ODBC). Se actualiza los martes.

Agregación:
- Semanal por ámbito: reserva % = Σ volumen actual / Σ capacidad, usando solo los embalses que
  informan en esa fecha (así un embalse sin dato no hunde el porcentaje).
- Mensual por ámbito: media de las semanas del mes (``semanas_con_dato`` indica cuántas hay).

Asignación a provincias: AMBITO_POR_PROVINCIA (tabla estática, ver docstring de esa constante).
Las provincias sin embalses en la base (Baleares, Canarias, Ceuta, Melilla) quedan sin ámbito.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from cpd.config import RUTA_RAW
from cpd.fuentes.http import RUTA_API, ErrorFuente, descargar_archivo

FUENTE: str = "MITECO embalses"
URL_ZIP: str = (
    "https://www.miteco.gob.es/content/dam/miteco/es/agua/temas/evaluacion-de-los-recursos-hidricos/"
    "boletin-hidrologico/Historico-de-embalses/BD-Embalses.zip"
)
CARPETA: Path = RUTA_API / "miteco"
RUTA_ZIP: Path = CARPETA / "BD-Embalses.zip"
RUTA_ZIP_RESPALDO: Path = RUTA_RAW / "agua" / "miteco_bd_embalses_1988_hoy.zip"  # copia previa del proyecto
CARPETA_MDB: Path = CARPETA / "mdb"
RUTA_SEMANAL: Path = CARPETA / "embalses_ambito_semanal.csv"
RUTA_MENSUAL: Path = CARPETA / "embalses_ambito_mensual.csv"
NOMBRE_TABLA: str = "T_Datos Embalses"
DIAS_MAXIMOS_ZIP: int = 6  # se descarga de nuevo si el zip tiene más días que este (se publica los martes)

# Ámbitos hidrográficos de la base del MITECO (nombre canónico).
AMBITOS: tuple[str, ...] = (
    "Ebro", "Guadalquivir", "Tajo", "Guadiana", "Duero", "Miño-Sil", "Júcar", "Segura", "Galicia Costa",
    "Cuenca Mediterránea Andaluza", "Cantábrico Occidental", "Cuencas Internas de Cataluña",
    "Guadalete-Barbate", "Tinto, Odiel y Piedras", "Cantábrico Oriental", "Cuencas Internas del País Vasco",
)

# Provincia (código INE) -> ámbito hidrográfico dominante, o None si la base no tiene embalses.
# AVISO: asignación ESTÁTICA y aproximada (cuenca que cubre la mayor parte del territorio provincial,
# con criterio propio). Las provincias compartidas entre dos cuencas (p. ej. Burgos, Teruel, Huelva,
# Alicante, Cáceres, Gipuzkoa, Bizkaia) se asignan a la cuenca dominante y pueden revisarse con los
# polígonos oficiales de las demarcaciones hidrográficas (EEA WISE) si hiciera falta.
AMBITO_POR_PROVINCIA: dict[str, str | None] = {
    "01": "Ebro", "02": "Júcar", "03": "Júcar", "04": "Cuenca Mediterránea Andaluza", "05": "Duero",
    "06": "Guadiana", "07": None, "08": "Cuencas Internas de Cataluña", "09": "Duero", "10": "Tajo",
    "11": "Guadalete-Barbate", "12": "Júcar", "13": "Guadiana", "14": "Guadalquivir", "15": "Galicia Costa",
    "16": "Tajo", "17": "Cuencas Internas de Cataluña", "18": "Guadalquivir", "19": "Tajo",
    "20": "Cantábrico Oriental", "21": "Tinto, Odiel y Piedras", "22": "Ebro", "23": "Guadalquivir",
    "24": "Duero", "25": "Ebro", "26": "Ebro", "27": "Miño-Sil", "28": "Tajo", "29": "Cuenca Mediterránea Andaluza",
    "30": "Segura", "31": "Ebro", "32": "Miño-Sil", "33": "Cantábrico Occidental", "34": "Duero",
    "35": None, "36": "Galicia Costa", "37": "Duero", "38": None, "39": "Cantábrico Occidental",
    "40": "Duero", "41": "Guadalquivir", "42": "Duero", "43": "Ebro", "44": "Ebro", "45": "Tajo",
    "46": "Júcar", "47": "Duero", "48": "Cuencas Internas del País Vasco", "49": "Duero", "50": "Ebro",
    "51": None, "52": None,
}


def _clave(nombre: Any) -> str:
    """Clave comparable de un nombre de ámbito: sin caracteres no ASCII ni signos.

    La base de datos llega con caracteres dañados ("Mi�o - Sil", "J�car"); al quitar lo no ASCII,
    el nombre dañado y el canónico ("Miño-Sil", "Júcar") coinciden.
    """
    sin_no_ascii = re.sub(r"[^\x00-\x7f]", "", str(nombre))
    return re.sub(r"[^a-z]", "", sin_no_ascii.lower())


_CANONICOS: dict[str, str] = {_clave(nombre): nombre for nombre in AMBITOS}


def ambito_canonico(nombre: Any) -> str | None:
    """Nombre canónico del ámbito (o None si el nombre es vacío). Desconocidos: el nombre limpio."""
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)):
        return None
    return _CANONICOS.get(_clave(nombre), str(nombre).strip())


def _numero(valor: Any) -> float:
    """Convierte un valor de Access (texto con coma decimal "91,00" o número) en float."""
    if valor is None:
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return float(str(valor).strip().replace(".", "").replace(",", ".")) if "," in str(valor) else float(valor)
    except ValueError:
        return float("nan")


def tabla_access_a_dataframe(tabla: dict[str, list[Any]]) -> pd.DataFrame:
    """Convierte la tabla de access-parser (dict columna -> lista) en el formato del proyecto.

    Args:
        tabla: diccionario con las claves FECHA, AMBITO_NOMBRE, EMBALSE_NOMBRE, AGUA_TOTAL, AGUA_ACTUAL.

    Returns:
        DataFrame con fecha (Timestamp), ambito (canónico), embalse, capacidad_hm3, volumen_hm3.
    """
    requeridas = ("FECHA", "AMBITO_NOMBRE", "EMBALSE_NOMBRE", "AGUA_TOTAL", "AGUA_ACTUAL")
    faltan = [c for c in requeridas if c not in tabla]
    if faltan:
        raise ErrorFuente(f"{FUENTE}: faltan columnas en la base de datos: {faltan}")
    filas = len(tabla["FECHA"])
    return pd.DataFrame({
        "fecha": pd.to_datetime(pd.Series(tabla["FECHA"]), errors="coerce").dt.normalize(),
        "ambito": [ambito_canonico(a) for a in tabla["AMBITO_NOMBRE"]],
        "embalse": [str(e).strip() if e is not None else None for e in tabla["EMBALSE_NOMBRE"]],
        "capacidad_hm3": [_numero(v) for v in tabla["AGUA_TOTAL"]],
        "volumen_hm3": [_numero(v) for v in tabla["AGUA_ACTUAL"]],
    }).head(filas)


def reservas_semanales(tabla: pd.DataFrame) -> pd.DataFrame:
    """Reserva semanal por ámbito usando solo los embalses con capacidad conocida en cada fecha.

    Returns:
        DataFrame: fecha, ambito, reserva_pct, volumen_hm3, capacidad_hm3, embalses.
    """
    datos = tabla.dropna(subset=["fecha", "ambito", "capacidad_hm3", "volumen_hm3"])
    datos = datos[datos["capacidad_hm3"] > 0]
    agregado = datos.groupby(["fecha", "ambito"]).agg(
        volumen_hm3=("volumen_hm3", "sum"),
        capacidad_hm3=("capacidad_hm3", "sum"),
        embalses=("embalse", "nunique"),
    ).reset_index()
    agregado["reserva_pct"] = (100 * agregado["volumen_hm3"] / agregado["capacidad_hm3"]).round(2)
    return agregado[["fecha", "ambito", "reserva_pct", "volumen_hm3", "capacidad_hm3", "embalses"]].sort_values(
        ["ambito", "fecha"]).reset_index(drop=True)


def reservas_mensuales(semanal: pd.DataFrame) -> pd.DataFrame:
    """Media mensual de las reservas semanales por ámbito.

    Returns:
        DataFrame: mes (inicio de mes), ambito, reserva_pct_media_mes, volumen_hm3_media_mes,
        capacidad_hm3_media_mes, semanas_con_dato.
    """
    datos = semanal.copy()
    datos["mes"] = pd.to_datetime(datos["fecha"]).dt.to_period("M").dt.to_timestamp()
    tabla = datos.groupby(["mes", "ambito"]).agg(
        reserva_pct_media_mes=("reserva_pct", "mean"),
        volumen_hm3_media_mes=("volumen_hm3", "mean"),
        capacidad_hm3_media_mes=("capacidad_hm3", "mean"),
        semanas_con_dato=("fecha", "count"),
    ).reset_index()
    tabla[["reserva_pct_media_mes", "volumen_hm3_media_mes", "capacidad_hm3_media_mes"]] = (
        tabla[["reserva_pct_media_mes", "volumen_hm3_media_mes", "capacidad_hm3_media_mes"]].round(2))
    return tabla.sort_values(["ambito", "mes"]).reset_index(drop=True)


def asegurar_zip(forzar: bool = False) -> Path:
    """Descarga el zip del MITECO si no existe o tiene más de DIAS_MAXIMOS_ZIP días.

    Si la descarga falla se usa la copia local anterior (con aviso en el registro) y, si tampoco
    existe, se lanza ErrorFuente. Nunca se desactiva la verificación TLS.
    """
    edad = (dt.datetime.now() - dt.datetime.fromtimestamp(RUTA_ZIP.stat().st_mtime)).days if RUTA_ZIP.exists() else None
    if RUTA_ZIP.exists() and edad is not None and edad <= DIAS_MAXIMOS_ZIP and not forzar:
        return RUTA_ZIP
    try:
        return descargar_archivo(URL_ZIP, RUTA_ZIP, FUENTE, "BD de embalses semanal (zip)", forzar=RUTA_ZIP.exists())
    except ErrorFuente as error:
        if RUTA_ZIP.exists():
            return RUTA_ZIP
        if RUTA_ZIP_RESPALDO.exists():
            print(f"Aviso: {error}. Se usa la copia local {RUTA_ZIP_RESPALDO.name}")
            return RUTA_ZIP_RESPALDO
        raise


def extraer_mdb(zip_path: Path) -> Path:
    """Extrae el .mdb del zip a una carpeta propia y vacía (sin rutas del zip: evita 'zip slip')."""
    shutil.rmtree(CARPETA_MDB, ignore_errors=True)
    CARPETA_MDB.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        miembros = [m for m in zf.namelist() if m.lower().endswith(".mdb")]
        if not miembros:
            raise ErrorFuente(f"{FUENTE}: el zip no contiene ningún .mdb")
        destino = CARPETA_MDB / Path(miembros[0]).name
        with zf.open(miembros[0]) as origen, destino.open("wb") as salida:
            shutil.copyfileobj(origen, salida)
    return destino


def leer_mdb(ruta_mdb: Path) -> pd.DataFrame:
    """Lee la tabla de embalses del .mdb con access-parser (Python puro)."""
    from access_parser import AccessParser

    base = AccessParser(str(ruta_mdb))
    nombres = [n for n in base.catalog if str(n).startswith(NOMBRE_TABLA)]
    if not nombres:
        raise ErrorFuente(f"{FUENTE}: no se encuentra la tabla {NOMBRE_TABLA}* en el .mdb")
    return tabla_access_a_dataframe(base.parse_table(nombres[0]))


def reservas_mensuales_desde_zip(forzar: bool = False) -> pd.DataFrame:
    """Refresca el zip, lee la base y devuelve las reservas mensuales por ámbito.

    La lectura del .mdb tarda unos minutos: si el zip no ha cambiado desde la última lectura se
    reutiliza la agregación guardada (RUTA_SEMANAL / RUTA_MENSUAL).
    """
    zip_path = asegurar_zip(forzar=forzar)
    if RUTA_MENSUAL.exists() and RUTA_SEMANAL.exists() and RUTA_SEMANAL.stat().st_mtime > zip_path.stat().st_mtime:
        return pd.read_csv(RUTA_MENSUAL, parse_dates=["mes"])
    semanal = reservas_semanales(leer_mdb(extraer_mdb(zip_path)))
    mensual = reservas_mensuales(semanal)
    CARPETA.mkdir(parents=True, exist_ok=True)
    semanal.to_csv(RUTA_SEMANAL, index=False, encoding="utf-8")
    mensual.to_csv(RUTA_MENSUAL, index=False, encoding="utf-8")
    shutil.rmtree(CARPETA_MDB, ignore_errors=True)  # el .mdb (200 MB) no hace falta después
    return mensual
