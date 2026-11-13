"""Exporta el resultado del modelo de viabilidad a JSON para el frontend (mapa interactivo).

Ejecuta el mismo modelo que la app de Streamlit: lee la tabla de municipios y config/settings.yaml,
llama a cpd.scoring.evaluar() con los parámetros por defecto del CPD y escribe
frontend/public/data/viabilidad.json con:

- los municipios evaluados (estado, motivos, sub-scores, score global, CAPEX, OPEX, VAN, ROI...);
- un resumen por provincia (código INE de 2 dígitos): mejor emplazamiento y media provincial;
- los parámetros, precios, pesos y umbrales usados (para poder recalcular con el precio de la luz en vivo).

No inventa nada: las provincias sin municipios en la tabla simplemente no aparecen en "provincias"
y el mapa las muestra como "sin datos todavía".

Uso (desde la raíz del repositorio):
    .venv\\Scripts\\python.exe frontend\\scripts\\export_data.py
    .venv\\Scripts\\python.exe frontend\\scripts\\export_data.py --csv data\\curated\\tabla_maestra.csv
o desde frontend/:  npm run data
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))  # usa el código de este checkout, no otra instalación

import pandas as pd  # noqa: E402

from cpd.config import RUTA_DEMO, cargar_settings  # noqa: E402
from cpd.scoring import INDICADORES_POR_BLOQUE, evaluar  # noqa: E402
from cpd.simulator import CPDParams  # noqa: E402

SALIDA_POR_DEFECTO = RAIZ / "frontend" / "public" / "data" / "viabilidad.json"

# Columnas de entrada que el panel muestra (si existen en la tabla).
ENTRADAS = (
    "poblacion", "tasa_paro", "pct_estudios_superiores", "dist_subestacion_km", "tension_subestacion_kv",
    "capacidad_acceso_mw", "consumo_electrico_municipal_mwh", "temp_media_c", "temp_max_hist_c",
    "humedad_media_pct", "dias_calor_extremo", "estres_hidrico_idx", "consumo_hidrico_municipal_m3",
    "cobertura_fibra_pct", "dist_ixp_km", "dist_autopista_km", "dist_aeropuerto_km", "precio_suelo_eur_m2",
    "suelo_industrial_ha", "zona_inundable", "red_natura", "peligrosidad_sismica_g",
)
# Salidas del simulador (ver cpd.scoring.simular_municipio).
SALIDAS = (
    "pue_estimado", "pue_aplicado", "potencia_total_mw", "consumo_mwh", "agua_m3_anual", "coste_energia_eur",
    "opex_energia_eur", "opex_agua_eur", "opex_personal_eur", "opex_mantenimiento_eur", "opex_impuestos_eur",
    "opex_eur", "co2_t", "impacto_local_pct", "latencia_rtt_ms", "coste_suelo_eur", "capex_total_eur",
    "ingresos_alquiler_eur", "ingresos_energia_eur", "ingresos_anuales_eur", "flujo_caja_anual_eur",
    "van_eur", "roi", "payback_anos",
)


def _limpio(valor: Any) -> Any:
    """Convierte tipos de numpy/pandas a JSON y NaN/infinito a None."""
    if valor is None:
        return None
    if hasattr(valor, "item"):
        valor = valor.item()
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, float):
        return round(valor, 6)
    return valor


def _params_por_defecto(settings: dict[str, Any]) -> CPDParams:
    """CPDParams con los valores de settings.yaml (cpd_por_defecto), igual que la app."""
    defecto = settings.get("cpd_por_defecto", {})
    validos = {f.name for f in fields(CPDParams)}
    return CPDParams(**{k: v for k, v in defecto.items() if k in validos})


def exportar(ruta_csv: Path, salida: Path) -> dict[str, Any]:
    """Evalúa la tabla de municipios y escribe el JSON del frontend. Devuelve el diccionario escrito."""
    settings = cargar_settings()
    params = _params_por_defecto(settings)
    tabla = pd.read_csv(ruta_csv, dtype={"codigo_ine": str})
    tabla["codigo_ine"] = tabla["codigo_ine"].str.zfill(5)
    resultado = evaluar(tabla, params, settings)

    municipios: list[dict[str, Any]] = []
    for _, fila in resultado.iterrows():
        origen = str(fila.get("origen_datos", "") or "")
        municipio = {
            "codigo_ine": fila["codigo_ine"],
            "municipio": fila["municipio"],
            "provincia_codigo": fila["codigo_ine"][:2],
            "provincia": fila.get("provincia"),
            "ccaa": fila.get("ccaa"),
            "lat": _limpio(fila.get("lat")),
            "lon": _limpio(fila.get("lon")),
            "origen_datos": origen,
            "sintetico": "sint" in origen.lower() or "demo" in origen.lower(),
            "ranking": int(fila["ranking"]),
            "estado": fila["estado"],
            "motivos": list(fila["motivos"]),
            "score_global": _limpio(fila["score_global"]),
            "sub": {bloque: _limpio(fila[f"sub_{bloque}"]) for bloque in INDICADORES_POR_BLOQUE},
            "entradas": {c: _limpio(fila.get(c)) for c in ENTRADAS if c in resultado.columns},
            "salidas": {c: _limpio(fila.get(c)) for c in SALIDAS if c in resultado.columns},
        }
        municipios.append(municipio)

    # Resumen por provincia: el orden de evaluar() ya pone primero el mejor emplazamiento
    # (Viable > Viable con condiciones > No viable, y dentro de cada estado mayor score).
    provincias: dict[str, dict[str, Any]] = {}
    for m in municipios:
        p = provincias.setdefault(m["provincia_codigo"], {
            "codigo": m["provincia_codigo"],
            "municipios": [],
            "mejor": m["codigo_ine"],
            "estado": m["estado"],
            "conteo_estados": {},
        })
        p["municipios"].append(m["codigo_ine"])
        p["conteo_estados"][m["estado"]] = p["conteo_estados"].get(m["estado"], 0) + 1
    for codigo, p in provincias.items():
        scores = [m["score_global"] for m in municipios if m["provincia_codigo"] == codigo and m["score_global"] is not None]
        p["score_max"] = max(scores) if scores else None
        p["score_medio"] = round(sum(scores) / len(scores), 1) if scores else None
        p["n_municipios"] = len(p["municipios"])

    sintetico = all(m["sintetico"] for m in municipios)
    try:
        fichero = ruta_csv.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        fichero = ruta_csv.name
    datos = {
        "generado": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "fuente": {
            "fichero": fichero,
            "sintetico": sintetico,
            "n_municipios": len(municipios),
            "nota": (
                "Indicadores SINTÉTICOS de demostración (nombres, códigos INE y coordenadas reales)."
                if sintetico else "Tabla de municipios con datos de origen declarados en origen_datos."
            ),
        },
        "parametros": asdict(params),
        "precios": settings["precios"],
        "pesos": settings["pesos"],
        "umbrales": settings["umbrales"],
        "latencia": settings["latencia"],
        "municipios": municipios,
        "provincias": dict(sorted(provincias.items())),
    }
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return datos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=RUTA_DEMO, help="tabla de municipios (por defecto la de demo)")
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO, help="JSON de salida")
    args = parser.parse_args()
    datos = exportar(args.csv, args.salida)
    print(
        f"OK: {datos['fuente']['n_municipios']} municipios, {len(datos['provincias'])} provincias con datos "
        f"({'SINTÉTICOS' if datos['fuente']['sintetico'] else 'reales'}) -> {args.salida}"
    )


if __name__ == "__main__":
    main()
