"""Tests de la fase de ingesta.

Los scripts de src/ingesta descargan de internet al ejecutarse, así que aquí NO se ejecutan:
solo se comprueba que son Python válido y que el registro de descargas y el manifiesto son coherentes.
"""

import csv
import py_compile
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
INGESTA = RAIZ / "src" / "ingesta"
REGISTRO = RAIZ / "data" / "raw" / "_registro_descargas.csv"
MANIFIESTO = RAIZ / "docs" / "datos" / "manifiesto_raw_2026-11-09.csv"

SCRIPTS = ["utils.py", "01_municipios.py", "02_demografia.py", "03_energia.py", "04_agua.py"]


def leer_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_script_de_ingesta_existe_y_compila(nombre, tmp_path):
    script = INGESTA / nombre
    assert script.exists(), f"Falta {script}"
    py_compile.compile(str(script), cfile=str(tmp_path / "x.pyc"), doraise=True)


def test_registro_de_descargas_tiene_columnas_y_urls_oficiales():
    filas = leer_csv(REGISTRO)
    assert len(filas) >= 10
    assert set(filas[0]) == {"fecha_descarga", "fuente", "descripcion", "url", "archivo", "tam_kb"}
    for fila in filas:
        assert fila["url"].startswith("https://"), fila["url"]
        assert fila["archivo"].startswith("data/raw/"), fila["archivo"]
        assert fila["fuente"].strip()


def test_manifiesto_tiene_huellas_validas_y_cubre_el_registro():
    manifiesto = leer_csv(MANIFIESTO)
    rutas = {fila["ruta"] for fila in manifiesto}
    assert len(rutas) == len(manifiesto), "Rutas duplicadas en el manifiesto"
    for fila in manifiesto:
        assert re.fullmatch(r"[0-9a-f]{64}", fila["sha256"]), fila
        assert int(fila["bytes"]) > 0, fila
    # Cada entrada del registro (fichero o carpeta de JSON) aparece en el manifiesto
    for fila in leer_csv(REGISTRO):
        archivo = fila["archivo"]
        assert archivo in rutas or any(r.startswith(archivo + "/") for r in rutas), archivo
