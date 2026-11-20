"""INE: Tablas Input-Output (TIO) de la Contabilidad Nacional Anual de España (Revisión Estadística 2024).

Fichero: https://www.ine.es/daco/daco42/cne24/cne_tio_<AA>.xlsx (último: 2022, publicado el 19/12/2025).
Se usan dos hojas (producto × producto, 65 productos con el «44 bis»):

- **Tabla 1** (TIO a precios básicos, millones de €): por producto, producción, valor añadido bruto (VAB),
  importaciones, oferta y puestos de trabajo equivalentes a tiempo completo (miles).
- **Tabla 7** (coeficientes de la matriz inversa **interior**, Leontief): producción interior de cada producto que hace
  falta por cada euro de demanda final interior de otro (incluye la propia demanda).

El producto 40 («Servicios de programación, consultoría y otros relacionados con la informática», CNAE 62-63)
incluye el proceso de datos y el hosting (CNAE 63.11), que es la actividad de un CPD.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from cpd.fuentes.http import RUTA_API, descargar_archivo

FUENTE: str = "INE (Tablas Input-Output)"
ANIO_TIO: int = 2022
CARPETA: Path = RUTA_API / "ine"
FILAS_TABLA1: dict[str, str] = {
    "Valor añadido bruto a precios básicos": "vab_meur",
    "Producción a precios básicos": "produccion_meur",
    "Importaciones": "importaciones_meur",
    "Oferta a precios básicos": "oferta_meur",
}


def url_tio(anio: int = ANIO_TIO) -> str:
    return f"https://www.ine.es/daco/daco42/cne24/cne_tio_{anio % 100:02d}.xlsx"


def descargar(anio: int = ANIO_TIO) -> Path:
    """Descarga el fichero de las TIO de un año (una vez; la tabla de un año cerrado no cambia salvo revisión)."""
    return descargar_archivo(url_tio(anio), CARPETA / f"cne_tio_{anio % 100:02d}.xlsx", FUENTE, f"Tablas Input-Output {anio}")


def _codigo(etiqueta: object) -> str | None:
    """«40. Servicios de programación…» → «40»; «44 bis. Alquileres…» → «44bis»; otras filas → None."""
    m = re.match(r"^\s*(\d+)(\s*bis)?\.\s", str(etiqueta))
    return None if m is None else m.group(1) + ("bis" if m.group(2) else "")


def _texto(valor: object) -> str:
    return " ".join(str(valor).split())


def leer_tio(ruta: Path) -> dict[str, pd.DataFrame]:
    """Lee las TIO y devuelve `ramas` (una fila por producto) y `leontief` (inversa interior, 65 × 65).

    Returns:
        `ramas`: codigo, nombre, produccion_meur, vab_meur, importaciones_meur, oferta_meur, empleo_etc_miles.
        `leontief`: matriz con índice y columnas = códigos de producto.
    """
    t1 = pd.read_excel(ruta, sheet_name="Tabla1", header=None)
    codigos_fila = t1.iloc[:, 1].map(_codigo)
    filas_productos = codigos_fila[codigos_fila.notna()]
    codigos = filas_productos.tolist()
    nombres = [_texto(t1.iloc[i, 1]).split(". ", 1)[1] for i in filas_productos.index]
    # Columnas de productos: desde la columna 2, en el mismo orden que las filas.
    columnas = list(range(2, 2 + len(codigos)))
    etiquetas = t1.iloc[:, 1].map(_texto)
    ramas = pd.DataFrame({"codigo": codigos, "nombre": nombres})
    for texto, nombre_col in FILAS_TABLA1.items():
        fila = etiquetas[etiquetas == texto].index
        if len(fila) == 0:
            raise ValueError(f"TIO: no se encuentra la fila «{texto}» en la Tabla 1")
        ramas[nombre_col] = pd.to_numeric(t1.iloc[fila[0], columnas], errors="coerce").to_numpy()
    # Puestos de trabajo equivalentes a tiempo completo: la fila «Total» que sigue a su título.
    titulo = etiquetas[etiquetas.str.startswith("Puestos de trabajo equivalentes a tiempo completo")].index
    if len(titulo) == 0:
        raise ValueError("TIO: no se encuentra el empleo equivalente a tiempo completo en la Tabla 1")
    fila_total = next(i for i in range(titulo[0] + 1, len(etiquetas)) if etiquetas[i] == "Total")
    ramas["empleo_etc_miles"] = pd.to_numeric(t1.iloc[fila_total, columnas], errors="coerce").to_numpy()

    t7 = pd.read_excel(ruta, sheet_name="Tabla7", header=None)
    cod7 = t7.iloc[:, 1].map(_codigo)
    filas7 = cod7[cod7.notna()]
    if filas7.tolist() != codigos:
        raise ValueError("TIO: los productos de la Tabla 7 no coinciden con los de la Tabla 1")
    matriz = t7.iloc[filas7.index, 2 : 2 + len(codigos)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    leontief = pd.DataFrame(matriz, index=codigos, columns=codigos)
    if not np.isfinite(matriz).all():
        raise ValueError("TIO: la inversa interior tiene celdas vacías")
    return {"ramas": ramas, "leontief": leontief}
