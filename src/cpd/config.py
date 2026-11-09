"""Carga de la configuración del proyecto desde config/settings.yaml.

Centraliza las rutas del proyecto para que el resto de módulos no dependan
de la carpeta desde la que se ejecute la aplicación o los tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Raíz del proyecto: src/cpd/config.py -> parents[2] = p3-cpd/
RUTA_RAIZ: Path = Path(__file__).resolve().parents[2]
RUTA_CONFIG: Path = RUTA_RAIZ / "config" / "settings.yaml"
RUTA_DEMO: Path = RUTA_RAIZ / "data" / "demo" / "municipios_demo.csv"
RUTA_DEMANDA_LIMPIA: Path = RUTA_RAIZ / "data" / "clean" / "ree_demanda_mensual.csv"
RUTA_RAW: Path = RUTA_RAIZ / "data" / "raw"

PESOS_ESPERADOS: tuple[str, ...] = (
    "energia",
    "agua_refrigeracion",
    "conectividad",
    "riesgos_naturales",
    "suelo_regulatorio",
    "costes",
    "mercado_talento",
    "impacto",
)


def cargar_settings(ruta: Path | str | None = None) -> dict[str, Any]:
    """Lee el fichero YAML de configuración y devuelve un diccionario.

    Args:
        ruta: ruta alternativa al YAML. Si es None se usa config/settings.yaml.

    Returns:
        Diccionario con las secciones pesos, umbrales, precios, cpd_por_defecto y latencia.

    Raises:
        FileNotFoundError: si el fichero no existe.
        ValueError: si los pesos no suman 1 (tolerancia 1e-6).
    """
    ruta_yaml = Path(ruta) if ruta is not None else RUTA_CONFIG
    if not ruta_yaml.exists():
        raise FileNotFoundError(f"No se encuentra el fichero de configuración: {ruta_yaml}")
    with ruta_yaml.open("r", encoding="utf-8") as fichero:
        settings = yaml.safe_load(fichero) or {}

    total_pesos = sum(float(settings["pesos"][clave]) for clave in PESOS_ESPERADOS)
    if abs(total_pesos - 1.0) > 1e-6:
        raise ValueError(f"Los pesos deben sumar 1.0 y suman {total_pesos:.4f}")
    return settings
