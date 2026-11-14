"""Simulación determinista de un CPD en las 52 provincias con datos reales y el modelo del proyecto.

No entrena nada: pasa los indicadores reales de cada provincia (data/curated/provincias_actual y el panel
mensual panel_provincia_mes) por las mismas funciones que la app de Streamlit (cpd.scoring.evaluar y
cpd.simulator) y escribe frontend/public/data/provincias_simuladas.json para el mapa.

Entradas a escala provincial (últimos 12 meses del panel, salvo indicación):
  temperatura media → PUE (pue_estimado) y riesgo de calor · humedad · días ≥ 35 °C · horas de free cooling
  precio spot medio de 12 meses (nacional) → coste de la energía, OPEX, VAN, ROI y payback
  estrés hídrico WRI (comunidad) → filtro de agua (M6) · reservas de embalses del ámbito → aviso
  distancia al IXP más cercano → latencia (M3) · capacidad de acceso disponible (comunidad) → M1
  subestaciones 220/400 kV → tensión disponible · población y paro → mercado y talento
  demanda eléctrica anual de la comunidad → impacto local
Lo que solo existe por parcela (zona inundable, Red Natura de la parcela, distancia a subestación, sismicidad
en g, precio y superficie de suelo, fibra, carreteras, aeropuertos) no se evalúa a escala provincial.

Clase de rentabilidad (4 clases): «no viable» o VAN ≤ 0 → no_rentable; el resto, por tercios de su VAN
(alta, media, baja). Es RELATIVA entre provincias: con los supuestos actuales todas tienen VAN positivo.

Uso: .venv\\Scripts\\python.exe frontend\\scripts\\simular_provincias.py   (o npm run data)
"""

from __future__ import annotations

import copy
import json
import math
import sys
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))  # usa el código de este checkout

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from cpd.config import cargar_settings  # noqa: E402
from cpd.scoring import evaluar  # noqa: E402
from cpd.simulator import CPDParams  # noqa: E402

CURADO = RAIZ / "data" / "curated"
SALIDA = RAIZ / "frontend" / "public" / "data" / "provincias_simuladas.json"
META = RAIZ / "frontend" / "src" / "data" / "provincias.json"

CLASES = ("alta", "media", "baja", "no_rentable")

# Entradas del modelo que solo existen para una parcela o municipio concreto.
NO_PROVINCIALES = [
    "zona inundable",
    "parcela dentro de Red Natura 2000",
    "distancia a la subestación",
    "peligrosidad sísmica (g)",
    "precio y superficie de suelo industrial",
    "cobertura de fibra, autopista y aeropuerto",
]

# Entradas provinciales que pueden faltar en alguna provincia (se dicen en la ficha).
NOMBRE_ENTRADA = {
    "temp_media_c": "temperatura media",
    "estres_hidrico_idx": "estrés hídrico",
    "dist_ixp_km": "distancia al punto de intercambio (IXP)",
    "capacidad_acceso_mw": "capacidad de acceso a la red",
    "tension_subestacion_kv": "subestaciones de 220/400 kV",
    "consumo_electrico_municipal_mwh": "demanda eléctrica de la comunidad",
    "poblacion": "población",
    "tasa_paro": "paro registrado",
    "reserva_hidrica_pct": "reservas de los embalses",
    "horas_free_cooling_anual": "horas de free cooling",
}


def _leer(nombre: str, curado: Path) -> pd.DataFrame:
    parquet, csv = curado / f"{nombre}.parquet", curado / f"{nombre}.csv"
    if parquet.exists():
        df = pd.read_parquet(parquet)
    elif csv.exists():
        df = pd.read_csv(csv, dtype={"codigo_provincia": str})
    else:
        raise FileNotFoundError(f"No encuentro {parquet} ni {csv}: ejecuta antes la actualización de datos")
    df["codigo_provincia"] = df["codigo_provincia"].astype(str).str.zfill(2)
    return df


def _num(v: Any) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _redondeo(v: Any, d: int = 6) -> float | None:
    x = _num(v)
    return None if x is None else round(x, d)


def entradas(actual: pd.DataFrame, panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Tabla de entrada de cpd.scoring.evaluar con una fila por provincia, y metadatos del cálculo."""
    nombres = {p["codigo"]: p["nombre"] for p in json.loads(META.read_text(encoding="utf-8"))}
    ref = pd.to_datetime(actual["mes_referencia_panel"]).max()
    panel = panel.assign(mes=pd.to_datetime(panel["mes"]))
    ventana = panel[(panel["mes"] > ref - pd.DateOffset(months=12)) & (panel["mes"] <= ref)]
    anual = ventana.groupby("codigo_provincia").agg(
        temp_media_c=("tmedia_mes_c", "mean"),
        temp_max_hist_c=("tmax_media_c", "max"),
        humedad_media_pct=("humedad_relativa_media_pct", "mean"),
        dias_calor_extremo=("dias_mas_35c", "sum"),
        horas_free_cooling_anual=("horas_free_cooling", "sum"),
        consumo_electrico_municipal_mwh=("demanda_ccaa_mwh", "sum"),
        meses=("mes", "nunique"),
    )
    precio_12m = float(ventana.groupby("mes")["precio_spot_medio_mes_eur_mwh"].first().mean())

    a = actual.set_index("codigo_provincia")
    tension = np.where(a["subestaciones_400kv"] > 0, 400.0, np.where(a["subestaciones_220_400kv"] > 0, 220.0, np.nan))
    df = pd.DataFrame(
        {
            "codigo_ine": [c + "000" for c in a.index],
            "codigo_provincia": a.index,
            "municipio": [nombres.get(c, n) for c, n in zip(a.index, a["provincia"])],
            "provincia": [nombres.get(c, n) for c, n in zip(a.index, a["provincia"])],
            "ccaa": a["ccaa"].values,
            "lat": a["lat_punto"].values,
            "lon": a["lon_punto"].values,
            "poblacion": a["poblacion"].values,
            "tasa_paro": (a["paro_por_1000_hab"] / 1000).values,
            "capacidad_acceso_mw": a["capacidad_demanda_rdt_disponible_mw"].values,
            "tension_subestacion_kv": tension,
            "estres_hidrico_idx": a["estres_hidrico_wri_0_1"].values,
            "dist_ixp_km": a["distancia_ixp_km"].values,
            "reserva_hidrica_pct": a["reserva_hidrica_pct"].values,
        }
    ).merge(anual, left_on="codigo_provincia", right_index=True, how="left")
    observado = pd.to_datetime(actual["momento_observacion"], errors="coerce").max()
    meta = {
        "precio_12m": precio_12m,
        "mes_referencia": ref.strftime("%Y-%m"),
        "actualizado": observado.isoformat() if pd.notna(observado) else None,
    }
    return df.reset_index(drop=True), meta


def clases_rentabilidad(estado: list[str], van: list[float | None]) -> list[str]:
    """«No viable» o VAN ≤ 0 → no_rentable; el resto, tercios de VAN (alta, media, baja)."""
    salida = ["no_rentable"] * len(estado)
    resto = [i for i, (e, v) in enumerate(zip(estado, van)) if e != "No viable" and v is not None and v > 0]
    resto.sort(key=lambda i: van[i], reverse=True)
    n = len(resto)
    for pos, i in enumerate(resto):
        salida[i] = "alta" if pos < n / 3 else "media" if pos < 2 * n / 3 else "baja"
    return salida


def _motivos(fila: pd.Series, extra: pd.Series, faltan: list[str]) -> list[str]:
    """Motivos del embudo sin el aviso genérico de datos ausentes, más avisos provinciales con datos reales."""
    motivos = [m for m in fila["motivos"] if not m.startswith("Aviso: datos ausentes")]
    reserva = _num(extra.get("reserva_hidrica_pct"))
    if reserva is not None and reserva < 40:
        motivos.append(f"Reservas de los embalses del ámbito al {reserva:.0f} %: riesgo para refrigerar con agua")
    natura = _num(extra.get("pct_superficie_natura2000"))
    if natura is not None and natura >= 30:
        motivos.append(f"El {natura:.0f} % de la provincia es Red Natura 2000: menos suelo disponible")
    sismos = _num(extra.get("n_terremotos_m3_plus"))
    if sismos:
        motivos.append(f"{sismos:.0f} terremoto{'s' if sismos != 1 else ''} de magnitud ≥ 3 este año en la provincia")
    cpd = _num(extra.get("cpd_existentes"))
    if cpd and cpd >= 3:
        motivos.append(f"Ya hay {cpd:.0f} centros de datos en la provincia (ecosistema existente)")
    if faltan:
        motivos.append(f"Sin dato de {', '.join(faltan)}: esa parte no se ha evaluado")
    return motivos


def simular(curado: Path = CURADO) -> dict[str, Any]:
    """Ejecuta la simulación para las 52 provincias y devuelve el JSON del mapa."""
    actual = _leer("provincias_actual", curado)
    panel = _leer("panel_provincia_mes", curado)
    settings = cargar_settings()
    validos = {f.name for f in fields(CPDParams)}
    params = CPDParams(**{k: v for k, v in settings.get("cpd_por_defecto", {}).items() if k in validos})

    df, meta = entradas(actual, panel)
    ajustes = copy.deepcopy(settings)
    ajustes["precios"]["precio_electricidad_eur_mwh"] = meta["precio_12m"]
    r = evaluar(df, params, ajustes).set_index("codigo_provincia", drop=False)
    a = actual.set_index("codigo_provincia")

    orden = list(r.index)
    clase = dict(zip(orden, clases_rentabilidad(list(r["estado"]), [_num(v) for v in r["van_eur"]])))

    provincias = []
    for codigo in sorted(r.index):
        fila = r.loc[codigo]
        extra = a.loc[codigo]
        faltan = [nombre for col, nombre in NOMBRE_ENTRADA.items() if _num(fila.get(col)) is None]
        provincias.append(
            {
                "codigo_provincia": codigo,
                "provincia": fila["provincia"],
                "ccaa": fila["ccaa"],
                "rentabilidad_clase": clase[codigo],
                "score_viabilidad": _redondeo(fila["score_global"], 1),
                "estado": fila["estado"],
                "van_eur": _redondeo(fila["van_eur"], 0),
                "roi": _redondeo(fila["roi"], 4),
                "payback_anos": _redondeo(fila["payback_anos"], 2),
                "capex_eur": _redondeo(fila["capex_total_eur"], 0),
                "opex_eur_anual": _redondeo(fila["opex_eur"], 0),
                "precio_luz_actual_eur_mwh": _redondeo(extra.get("precio_spot_actual_eur_mwh"), 2),
                "precio_luz_previsto_eur_mwh": _redondeo(extra.get("precio_spot_manana_medio_eur_mwh"), 2),
                "precio_luz_usado_eur_mwh": round(meta["precio_12m"], 2),
                "temp_media_anual_c": _redondeo(fila["temp_media_c"], 2),
                "horas_free_cooling_anual": _redondeo(fila["horas_free_cooling_anual"], 0),
                "reserva_hidrica_pct": _redondeo(fila["reserva_hidrica_pct"], 1),
                "estres_hidrico": _redondeo(fila["estres_hidrico_idx"], 3),
                "prob_cpd": None,
                "cpd_existentes": _redondeo(extra.get("cpd_existentes"), 0),
                "pue": _redondeo(fila["pue_aplicado"], 3),
                "latencia_rtt_ms": _redondeo(fila["latencia_rtt_ms"], 2),
                "motivos": _motivos(fila, extra, faltan),
                "faltan": faltan,
                "generado_en": meta["actualizado"],
            }
        )

    return {
        "tipo": "simulacion",
        "generado": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "actualizado": meta["actualizado"],
        "mes_referencia": meta["mes_referencia"],
        "precio_luz_usado_eur_mwh": round(meta["precio_12m"], 2),
        "metodo": (
            "Simulación determinista con cpd.scoring.evaluar() sobre datos reales por provincia; "
            "precio de la luz = media spot de 12 meses; clase relativa (tercios del VAN; no viable = no rentable)."
        ),
        "no_evaluado_a_escala_provincial": NO_PROVINCIALES,
        "provincias": provincias,
    }


def escribir(datos: dict[str, Any], salida: Path = SALIDA) -> Path:
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return salida


def main() -> None:
    datos = escribir(simular())
    provincias = json.loads(datos.read_text(encoding="utf-8"))["provincias"]
    reparto = {c: sum(p["rentabilidad_clase"] == c for p in provincias) for c in CLASES}
    print(f"OK: {len(provincias)} provincias simuladas con datos reales {reparto} -> {datos}")


if __name__ == "__main__":
    main()
