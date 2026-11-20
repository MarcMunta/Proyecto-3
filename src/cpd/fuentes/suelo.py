"""Ministerio de Transportes y Movilidad Sostenible: precio medio del suelo urbano por provincia (€/m²).

Fuente: Boletín Estadístico online, «Estadística de Precios de Suelo», tabla 4 «Precio medio del metro cuadrado de
suelo urbano por comunidades autónomas y provincias» (trimestral, desde 2004):
https://apps.fomento.gob.es/BoletinOnline2/?nivel=2&orden=36000000

- Se usa la **mediana de los 4 últimos trimestres publicados** de cada provincia: el dato de un trimestre salta mucho
  cuando hay pocas compraventas (Zaragoza pasó de 116 a 24 y a 142 €/m² en tres trimestres de 2024).
- Es suelo **urbano** (todos los usos), no solo industrial. No hay una estadística oficial y abierta del suelo
  industrial por provincia, así que se usa como aproximación del coste del suelo.
- Ceuta y Melilla vienen juntas y sin dato significativo («n.s.»): quedan sin valor (no se inventa).
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import numpy as np
import pandas as pd

from cpd.fuentes.http import RUTA_API, descargar_archivo
from cpd.fuentes.provincias import emparejar_nombre_ine

FUENTE: str = "Ministerio de Transportes (precios de suelo)"
URL: str = "https://apps.fomento.gob.es/BoletinOnline2/sedal/36400500.XLS"
CARPETA: Path = RUTA_API / "suelo"
TRIMESTRES: int = 4

# Nombres del boletín que no coinciden con el nombre INE de la provincia (comunidades uniprovinciales y
# nombres en castellano antiguo). Las comunidades con varias provincias se saltan (no son una provincia).
ALIAS: dict[str, str] = {
    "asturias (principado de )": "33", "asturias (principado de)": "33", "balears (illes)": "07",
    "madrid (comunidad de)": "28", "murcia (región de)": "30", "navarra (comunidad foral de)": "31",
    "rioja (la)": "26", "cantabria": "39", "palmas (las)": "35", "coruña (a)": "15", "álava": "01",
    "guipúzcoa": "20", "vizcaya": "48", "avila": "05", "ávila": "05", "alicante/alacant": "03",
    "castellón/castelló": "12", "valencia/valència": "46",
}
COMUNIDADES: frozenset[str] = frozenset(
    {
        "total nacional", "andalucía", "aragón", "canarias", "castilla y león", "castilla-la mancha", "cataluña",
        "comunitat valenciana", "extremadura", "galicia", "país vasco", "ceuta y melilla",
    }
)


def descargar(hoy: dt.date | None = None) -> Path:
    """Descarga la tabla 4 del boletín (una copia por mes, para coger los trimestres nuevos) y devuelve su ruta."""
    hoy = hoy or dt.date.today()
    destino = CARPETA / f"{hoy:%Y_%m}_36400500.XLS"
    return descargar_archivo(URL, destino, FUENTE, "Precio medio del m² de suelo urbano por provincias (tabla 4)")


def codigo_provincia(nombre: str) -> str | None:
    """Código INE de la provincia de una fila del boletín, o None si la fila es una comunidad o el total."""
    texto = " ".join(str(nombre).split()).lower()
    if not texto or texto in COMUNIDADES:
        return None
    if texto in ALIAS:
        return ALIAS[texto]
    return emparejar_nombre_ine(texto)


def _numero(valor: object) -> float:
    """Valor de una celda en €/m²; «n.s.», «.» o vacío → NaN."""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return float("nan")


def precio_desde_rejilla(rejilla: pd.DataFrame, trimestres: int = TRIMESTRES) -> pd.DataFrame:
    """Precio por provincia a partir de la hoja tal cual (sin cabecera).

    Busca la fila con los años («Año 2004», …) y la de los trimestres («1º» … «4º»); cada columna de dato queda
    asociada a un (año, trimestre). La columna de nombres es la que tiene «TOTAL NACIONAL».

    Returns:
        `codigo_provincia`, `precio_suelo_urbano_eur_m2` (mediana de los `trimestres` últimos con dato),
        `trimestres_usados`, `ultimo_trimestre` (AAAA-Tn).
    """
    celdas = rejilla.astype(object)
    fila_anios = next(i for i in range(len(celdas)) if any(re.match(r"A[ñn]o \d{4}", str(v)) for v in celdas.iloc[i]))
    fila_trim = next(i for i in range(fila_anios + 1, len(celdas)) if any(re.match(r"^[1-4]º$", str(v).strip()) for v in celdas.iloc[i]))
    col_nombre = next(j for j in range(celdas.shape[1]) if celdas.iloc[:, j].astype(str).str.strip().str.upper().eq("TOTAL NACIONAL").any())
    columnas: list[tuple[int, int, int]] = []  # (columna, año, trimestre)
    anio = None
    for j in range(celdas.shape[1]):
        m = re.match(r"A[ñn]o (\d{4})", str(celdas.iat[fila_anios, j]))
        if m:
            anio = int(m.group(1))
        t = re.match(r"^([1-4])º$", str(celdas.iat[fila_trim, j]).strip())
        if anio is not None and t:
            columnas.append((j, anio, int(t.group(1))))
    filas = []
    for i in range(fila_trim + 1, len(celdas)):
        nombre = celdas.iat[i, col_nombre]
        codigo = codigo_provincia(nombre) if pd.notna(nombre) else None
        if codigo is None:
            continue
        serie = [(anio, trim, _numero(celdas.iat[i, j])) for j, anio, trim in columnas]
        con_dato = [(a, t, v) for a, t, v in serie if np.isfinite(v) and v > 0][-trimestres:]
        if not con_dato:
            continue
        filas.append(
            {
                "codigo_provincia": codigo,
                "precio_suelo_urbano_eur_m2": round(float(np.median([v for _, _, v in con_dato])), 2),
                "trimestres_usados": len(con_dato),
                "ultimo_trimestre": f"{con_dato[-1][0]}-T{con_dato[-1][1]}",
            }
        )
    return pd.DataFrame(filas, columns=["codigo_provincia", "precio_suelo_urbano_eur_m2", "trimestres_usados", "ultimo_trimestre"])


def leer_precio_suelo(ruta: Path) -> pd.DataFrame:
    """Lee el XLS del boletín (formato Excel antiguo, con xlrd) y devuelve el precio por provincia."""
    return precio_desde_rejilla(pd.read_excel(ruta, sheet_name=0, header=None, engine="xlrd"))
