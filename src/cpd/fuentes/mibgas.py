"""MIBGAS (mercado ibérico del gas): precio del gas en España, diario y a plazo (futuros).

Fuente: ficheros anuales públicos `MIBGAS_Data_<año>.xlsx` de https://www.mibgas.es (sin clave).
Licencia (hoja «Disclaimer» del propio fichero): la información pública y gratuita «puede ser utilizada libremente,
siempre que se respete íntegramente su contenido original». Se cita la fuente y no se modifica el raw (R-2, R-12).

Por qué: el gas marca el precio de la electricidad en muchas horas (ciclos combinados). Los futuros del gas
(mes, trimestre y año siguientes) son la mejor información disponible sobre el precio de la luz del año siguiente.

Tablas:
- `gas_diario`: fecha, gas_mibgas_es_eur_mwh (índice MIBGAS-ES, entrega en el PVB).
- `gas_futuros`: fecha (día de negociación), producto (M+1, Q+1, Y+1), inicio_entrega, fin_entrega, precio_eur_mwh
  (precio de referencia de la sesión).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from cpd.fuentes.http import RUTA_API, ErrorFuente, descargar_archivo

ETIQUETA: str = "MIBGAS"
CARPETA: Path = RUTA_API / "mibgas"
ANIO_INICIO: int = 2016  # primer año completo del mercado
URL: str = "https://www.mibgas.es/es/file-access/MIBGAS_Data_{anio}.xlsx?path=AGNO_{anio}/XLS"
# GMAES = mes siguiente (month ahead); GQES_Q+1 = trimestre siguiente; GYES_Y+1 = año natural siguiente.
PRODUCTOS_FUTUROS: dict[str, str] = {"GMAES": "M+1", "GMES_M+1": "M+1", "GQES_Q+1": "Q+1", "GYES_Y+1": "Y+1"}


def fichero_anio(anio: int, hoy: dt.date | None = None) -> Path:
    """Descarga (o lee de la caché) el fichero de un año. El año en curso y el anterior se vuelven a pedir una vez
    al día, porque MIBGAS los sigue completando."""
    hoy = hoy or dt.date.today()
    destino = CARPETA / f"MIBGAS_Data_{anio}.xlsx"
    forzar = anio >= hoy.year - 1 and (not destino.exists() or dt.date.fromtimestamp(destino.stat().st_mtime) < hoy)
    return descargar_archivo(URL.format(anio=anio), destino, ETIQUETA, f"MIBGAS datos {anio}", forzar=forzar)


def _hoja(ruta: Path, candidatas: tuple[str, ...]) -> pd.DataFrame:
    """Primera hoja que exista de `candidatas` (los nombres cambian entre años: «Indices» en 2016, «MIBGAS Indexes»
    después; «Trading Data» en 2016, «Trading Data PVB&VTP» después)."""
    disponibles = pd.ExcelFile(ruta).sheet_names
    for nombre in candidatas:
        if nombre in disponibles:
            return pd.read_excel(ruta, sheet_name=nombre)
    raise ErrorFuente(f"{ETIQUETA}: {ruta.name} no tiene ninguna de las hojas {candidatas}")


def _columna(hoja: pd.DataFrame, *prefijos: str) -> str:
    """Columna cuyo nombre (sin saltos de línea) empieza por alguno de los prefijos, en ese orden de preferencia."""
    nombres = {str(c).replace("\n", " "): c for c in hoja.columns}
    for prefijo in prefijos:
        for limpio, original in nombres.items():
            if limpio.startswith(prefijo):
                return original
    raise ErrorFuente(f"{ETIQUETA}: no se encuentra la columna {prefijos}")


def _leer_indices(ruta: Path) -> pd.DataFrame:
    hoja = _hoja(ruta, ("MIBGAS Indexes", "Indices", "Indexes"))
    if "Area" in hoja.columns:
        hoja = hoja[hoja["Area"] == "ES"]
    fecha = _columna(hoja, "Delivery day")
    indice = _columna(hoja, "MIBGAS-ES Index", "MIBGAS Index")
    salida = hoja[[fecha, indice]].rename(columns={fecha: "fecha", indice: "gas_mibgas_es_eur_mwh"})
    salida["fecha"] = pd.to_datetime(salida["fecha"], errors="coerce").dt.normalize()
    salida["gas_mibgas_es_eur_mwh"] = pd.to_numeric(salida["gas_mibgas_es_eur_mwh"], errors="coerce")
    return salida.dropna()


def _leer_futuros(ruta: Path) -> pd.DataFrame:
    hoja = _hoja(ruta, ("Trading Data PVB&VTP", "Trading Data PVB", "Trading Data"))
    columnas = {
        _columna(hoja, "Trading day"): "fecha",
        _columna(hoja, "Product"): "producto",
        _columna(hoja, "Area"): "area",
        _columna(hoja, "First Day Delivery"): "inicio_entrega",
        _columna(hoja, "Last Day Delivery"): "fin_entrega",
        _columna(hoja, "Reference Price", "Daily Reference Price"): "precio_eur_mwh",
    }
    hoja = hoja[list(columnas)].rename(columns=columnas)
    hoja = hoja[(hoja["area"] == "ES") & hoja["producto"].isin(PRODUCTOS_FUTUROS)]
    hoja = hoja.assign(producto=hoja["producto"].map(PRODUCTOS_FUTUROS))
    for columna in ("fecha", "inicio_entrega", "fin_entrega"):
        hoja[columna] = pd.to_datetime(hoja[columna], errors="coerce").dt.normalize()
    hoja["precio_eur_mwh"] = pd.to_numeric(hoja["precio_eur_mwh"], errors="coerce")
    return hoja[["fecha", "producto", "inicio_entrega", "fin_entrega", "precio_eur_mwh"]].dropna()


def gas_diario(anio_inicio: int = ANIO_INICIO, anio_fin: int | None = None) -> pd.DataFrame:
    """Índice diario MIBGAS-ES (€/MWh) de los años pedidos.

    Raises:
        ErrorFuente: si no se pudo leer ningún año.
    """
    anio_fin = anio_fin or dt.date.today().year
    partes = [_leer_indices(fichero_anio(a)) for a in range(anio_inicio, anio_fin + 1)]
    if not partes:
        raise ErrorFuente(f"{ETIQUETA}: sin datos")
    return pd.concat(partes).drop_duplicates("fecha").sort_values("fecha").reset_index(drop=True)


def gas_futuros(anio_inicio: int = ANIO_INICIO, anio_fin: int | None = None) -> pd.DataFrame:
    """Precios de referencia de los futuros de gas M+1, Q+1 e Y+1 (€/MWh) por día de negociación."""
    anio_fin = anio_fin or dt.date.today().year
    partes = [_leer_futuros(fichero_anio(a)) for a in range(anio_inicio, anio_fin + 1)]
    return pd.concat(partes).drop_duplicates(["fecha", "producto"]).sort_values(["fecha", "producto"]).reset_index(drop=True)
