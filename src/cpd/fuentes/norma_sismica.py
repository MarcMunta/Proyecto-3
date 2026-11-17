"""Peligrosidad sísmica oficial por municipio y provincia: norma sismorresistente NCSE-02 (Real Decreto 997/2002).

Fuente: BOE núm. 244, de 11 de octubre de 2002, anejo 1 «Valores de la aceleración sísmica básica, ab, y del
coeficiente de contribución, K, de los términos municipales con ab ≥ 0,04 g» (mapa de peligrosidad del IGN):
https://www.boe.es/boe/dias/2002/10/11/pdfs/A35898-35967.pdf

- Cada línea del anejo es «MUNICIPIO 0,14 (1,0)»: ab/g y K, bajo una cabecera «PROVINCIA DE …» (Ceuta y Melilla
  vienen como «CIUDAD DE …» con el valor en la línea siguiente).
- Los municipios que no aparecen tienen ab < 0,04 g. A nivel de provincia se usa la **aceleración de la capital**
  (como las demás medidas, que usan la capital); si la capital no aparece se toma **0,04 g**, el máximo posible
  (cota superior: la norma no da el valor exacto por debajo de 0,04 g).
- La NCSE-02 es la norma vigente para proyectar edificios; el IGN actualizó su mapa de peligrosidad en 2012-2015, pero
  sin tabla abierta por municipio.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from cpd.fuentes.http import RUTA_API, descargar_archivo
from cpd.fuentes.provincias import PROVINCIAS

FUENTE: str = "BOE (NCSE-02, anejo 1)"
URL: str = "https://www.boe.es/boe/dias/2002/10/11/pdfs/A35898-35967.pdf"
CARPETA: Path = RUTA_API / "boe"
AB_MINIMO_LISTADO: float = 0.04

# Nombre de la capital tal como lo escribe la norma (sin tildes ni signos), por provincia de las que aparecen.
CAPITALES: dict[str, tuple[str, ...]] = {
    "01": ("VITORIA GASTEIZ", "VITORIA"), "02": ("ALBACETE",), "03": ("ALICANTE ALACANT", "ALICANTE"), "04": ("ALMERIA",),
    "06": ("BADAJOZ",), "07": ("PALMA DE MALLORCA", "PALMA"), "08": ("BARCELONA",), "10": ("CACERES",), "11": ("CADIZ",),
    "14": ("CORDOBA",), "15": ("CORUNA A", "A CORUNA"), "17": ("GIRONA",), "18": ("GRANADA",), "20": ("DONOSTIA SAN SEBASTIAN", "DONOSITA SAN SEBASTIAN", "SAN SEBASTIAN"),  # «DONOSITA»: errata del BOE
    "21": ("HUELVA",), "22": ("HUESCA",), "23": ("JAEN",), "25": ("LLEIDA",), "27": ("LUGO",), "29": ("MALAGA",), "30": ("MURCIA",),
    "31": ("PAMPLONA IRUNA", "PAMPLONA"), "32": ("OURENSE",), "35": ("PALMAS DE GRAN CANARIA LAS", "LAS PALMAS DE GRAN CANARIA"),
    "36": ("PONTEVEDRA",), "38": ("SANTA CRUZ DE TENERIFE",), "41": ("SEVILLA",), "43": ("TARRAGONA",), "46": ("VALENCIA", "VALENCIA VALENCIA"),
    "50": ("ZARAGOZA",),
}
# Cabeceras «PROVINCIA DE …» de la norma que no coinciden con el nombre INE.
ALIAS_PROVINCIA: dict[str, str] = {
    "ALAVA": "01", "GUIPUZCOA": "20", "ILLES BALEARS": "07", "A CORUNA": "15", "LAS PALMAS": "35", "NAVARRA": "31",
    "ALICANTE ALACANT": "03", "VALENCIA VALENCIA": "46", "CIUDAD DE CEUTA": "51", "CIUDAD DE MELILLA": "52",
}
_DATO = re.compile(r"^(.*?)\s*(0,\d{2})\s*\((\d,\d)\)$")


def _normalizar(texto: str) -> str:
    """Mayúsculas sin tildes ni signos (los «/», «,» y «-» pasan a espacio)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^A-Za-z ]", " ", sin_tildes).upper().split())


def _codigo_provincia(cabecera: str) -> str | None:
    """Código INE de la provincia de una cabecera «PROVINCIA DE …» o «CIUDAD DE …»."""
    completo = _normalizar(cabecera)
    nombre = _normalizar(cabecera.upper().replace("PROVINCIA DE", ""))
    for clave in (completo, nombre):
        if clave in ALIAS_PROVINCIA:
            return ALIAS_PROVINCIA[clave]
    for p in PROVINCIAS:
        if nombre in (_normalizar(p.nombre_ine), _normalizar(p.nombre)):
            return p.codigo
    return None


def municipios_desde_texto(texto: str) -> pd.DataFrame:
    """Municipios del anejo 1 a partir del texto extraído del PDF.

    Returns:
        `codigo_provincia`, `municipio`, `ab_g`, `k`.
    """
    filas: list[dict] = []
    provincia: str | None = None
    ciudad: str | None = None
    for linea in (l.strip() for l in texto.splitlines()):
        if not linea:
            continue
        mayus = linea.upper()
        if mayus.startswith("PROVINCIA DE") or mayus.startswith("CIUDAD DE"):
            provincia = _codigo_provincia(linea)
            ciudad = _normalizar(mayus.replace("CIUDAD DE", "")) if mayus.startswith("CIUDAD DE") else None
            continue
        m = _DATO.match(linea)
        if m and provincia:
            filas.append(
                {
                    "codigo_provincia": provincia,
                    "municipio": m.group(1).strip() or (ciudad or ""),
                    "ab_g": float(m.group(2).replace(",", ".")),
                    "k": float(m.group(3).replace(",", ".")),
                }
            )
    return pd.DataFrame(filas, columns=["codigo_provincia", "municipio", "ab_g", "k"])


def provincias_desde_municipios(municipios: pd.DataFrame) -> pd.DataFrame:
    """Por provincia: aceleración de la capital (0,04 g si no aparece), máxima y nº de municipios con ab ≥ 0,08 g.

    Ceuta y Melilla son un solo municipio: su valor es el de la ciudad.
    """
    filas = []
    for p in PROVINCIAS:
        datos = municipios[municipios["codigo_provincia"] == p.codigo]
        nombres = datos["municipio"].map(_normalizar)
        capital = None
        if p.codigo in ("51", "52") and len(datos):
            capital = float(datos["ab_g"].iloc[0])
        else:
            for variante in CAPITALES.get(p.codigo, ()):
                coincide = datos[nombres == variante]
                if len(coincide):
                    capital = float(coincide["ab_g"].iloc[0])
                    break
        filas.append(
            {
                "codigo_provincia": p.codigo,
                "aceleracion_sismica_capital_g": capital if capital is not None else AB_MINIMO_LISTADO,
                "capital_en_norma": capital is not None,
                "aceleracion_sismica_max_g": float(datos["ab_g"].max()) if len(datos) else AB_MINIMO_LISTADO,
                "municipios_ab_008_o_mas": int((datos["ab_g"] >= 0.08).sum()),
            }
        )
    return pd.DataFrame(filas)


def descargar() -> Path:
    """Descarga el BOE con la NCSE-02 (no cambia: norma de 2002) y devuelve su ruta."""
    return descargar_archivo(URL, CARPETA / "A35898-35967.pdf", FUENTE, "NCSE-02: aceleración sísmica básica por municipio (anejo 1)")


def leer_peligrosidad(ruta: Path) -> pd.DataFrame:
    """Lee el PDF (con pypdf) desde el anejo 1 y devuelve la tabla por provincia."""
    from pypdf import PdfReader

    paginas = [p.extract_text() or "" for p in PdfReader(str(ruta)).pages]
    inicio = next(i for i, t in enumerate(paginas) if "ANEJO 1" in t.upper())
    return provincias_desde_municipios(municipios_desde_texto("\n".join(paginas[inicio:])))
