"""Análisis exploratorio (fase 4): figuras en `docs/figuras/eda/` y datos para `docs/analisis/eda_panel.md`.

Técnicas de clase (C2): histogramas, box plots, series temporales, barras, dispersión, heatmap de correlación
(Pearson, Spearman y Kendall) y pair plot. Cada figura lleva título y ejes con unidades.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # sin ventana: solo ficheros
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from cpd.config import RUTA_RAIZ  # noqa: E402
from cpd.features.demanda import marcar_atipicos_demanda, serie_demanda_ccaa  # noqa: E402
from cpd.features.provincia import features_estaticas_provincia  # noqa: E402

RUTA_FIGURAS: Path = RUTA_RAIZ / "docs" / "figuras" / "eda"
RUTA_SIMULACION: Path = RUTA_RAIZ / "frontend" / "public" / "data" / "provincias_simuladas.json"
RUTA_CALIDAD: Path = RUTA_RAIZ / "data" / "curated" / "calidad_demanda_ccaa.csv"

# Variables mensuales que se describen (columna del panel → etiqueta con unidad).
VARIABLES_MENSUALES: dict[str, str] = {
    "tmedia_mes_c": "Temperatura media del mes (°C)",
    "precipitacion_mes_mm": "Precipitación del mes (mm)",
    "pct_horas_free_cooling": "Horas con free cooling (% del mes)",
    "reserva_hidrica_pct": "Reserva de embalses del ámbito (%)",
    "indice_sequia_12m": "Índice de sequía a 12 meses (z)",
    "precio_spot_medio_mes_eur_mwh": "Precio spot medio (€/MWh)",
    "pct_renovable_ccaa": "Generación renovable de la comunidad (%)",
    "paro_por_1000_hab": "Paro registrado (por 1.000 hab.)",
    "renta_neta_media_persona_eur": "Renta neta media por persona (€/año)",
}

# Variables por provincia para correlaciones (feature → etiqueta corta).
VARIABLES_PROVINCIA: dict[str, str] = {
    "log_poblacion": "log población",
    "renta_persona_eur": "renta €/persona",
    "paro_por_1000_hab": "paro ‰",
    "tmedia_anual_c": "temp. media °C",
    "pct_horas_free_cooling": "% free cooling",
    "estres_hidrico_wri_0_1": "estrés hídrico",
    "subestaciones_220_400kv": "subestaciones",
    "pct_superficie_natura2000": "% Natura 2000",
    "capacidad_acceso_ccaa_mw": "capacidad acceso MW",
    "terremotos_m3_por_anio": "terremotos M≥3/año",
    "n_centros_datos": "nº CPD",
}

COLOR = "#2c714e"
COLOR_2 = "#e47b2f"


def _guardar(figura: plt.Figure, nombre: str, carpeta: Path) -> str:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    figura.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(figura)
    return ruta.relative_to(RUTA_RAIZ).as_posix()


def _atipicos_registrados(marcada: pd.DataFrame) -> pd.DataFrame:
    """Meses de demanda excluidos por el control de calidad, con su valor original.

    El curado deja esos meses en NaN en el panel y guarda el registro en `data/curated/calidad_demanda_ccaa.csv`;
    si no existe (panel antiguo), se usan los que marque aquí `marcar_atipicos_demanda`.
    """
    if RUTA_CALIDAD.exists():
        registro = pd.read_csv(RUTA_CALIDAD, dtype={"codigo_ccaa": str})
        return pd.DataFrame(
            {
                "ccaa": registro["ccaa"],
                "mes": pd.to_datetime(registro["mes"]),
                "demanda_mwh": registro["demanda_mwh_original"],
                "cociente_interanual": registro["cociente_interanual"],
                "motivo_atipico": registro["motivo"],
            }
        )
    return marcada[marcada["atipico"]][["ccaa", "mes", "demanda_mwh", "cociente_interanual", "motivo_atipico"]]


def resumen_general(panel: pd.DataFrame) -> pd.DataFrame:
    """Una fila por columna: tipo, % de nulos, mínimo, máximo y nº de valores distintos (paso 1 de la fase 4)."""
    filas = []
    for columna in panel.columns:
        serie = panel[columna]
        numerica = pd.api.types.is_numeric_dtype(serie)
        filas.append(
            {
                "columna": columna,
                "tipo": "numérica" if numerica else ("fecha" if pd.api.types.is_datetime64_any_dtype(serie) else "texto"),
                "nulos_pct": round(serie.isna().mean() * 100, 1),
                "minimo": round(float(serie.min()), 2) if numerica and serie.notna().any() else None,
                "maximo": round(float(serie.max()), 2) if numerica and serie.notna().any() else None,
                "distintos": int(serie.nunique()),
            }
        )
    return pd.DataFrame(filas)


def _datos_simulacion(tabla: pd.DataFrame) -> pd.DataFrame:
    """Añade VAN (M€) y score de viabilidad de la simulación del mapa, si existe (para la correlación con B6)."""
    if not RUTA_SIMULACION.exists():
        return tabla
    datos = json.loads(RUTA_SIMULACION.read_text(encoding="utf-8"))
    sim = pd.DataFrame(datos["provincias"] if isinstance(datos, dict) else datos)
    sim["codigo_provincia"] = sim["codigo_provincia"].astype(str).str.zfill(2)
    sim = sim.set_index("codigo_provincia")[["van_eur", "score_viabilidad"]]
    sim["van_meur"] = sim["van_eur"] / 1e6
    return tabla.join(sim[["van_meur", "score_viabilidad"]])


def correlaciones(tabla: pd.DataFrame, columnas: list[str]) -> dict[str, pd.DataFrame]:
    """Matrices de correlación de Pearson, Spearman y Kendall (C2 p.23-24)."""
    datos = tabla[columnas].astype(float)
    return {metodo: datos.corr(method=metodo) for metodo in ("pearson", "spearman", "kendall")}


def pares_colineales(matriz: pd.DataFrame, umbral: float = 0.8) -> list[tuple[str, str, float]]:
    """Pares de variables con |correlación| ≥ `umbral` (multicolinealidad, recomendación)."""
    pares = []
    columnas = list(matriz.columns)
    for i, a in enumerate(columnas):
        for b in columnas[i + 1 :]:
            valor = matriz.loc[a, b]
            if pd.notna(valor) and abs(valor) >= umbral:
                pares.append((a, b, float(valor)))
    return sorted(pares, key=lambda p: -abs(p[2]))


def _heatmap(matriz: pd.DataFrame, titulo: str, etiquetas: list[str]) -> plt.Figure:
    figura, eje = plt.subplots(figsize=(8.5, 7))
    imagen = eje.imshow(matriz.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    eje.set_xticks(range(len(etiquetas)), etiquetas, rotation=60, ha="right", fontsize=8)
    eje.set_yticks(range(len(etiquetas)), etiquetas, fontsize=8)
    for i in range(len(etiquetas)):
        for j in range(len(etiquetas)):
            valor = matriz.iat[i, j]
            if pd.notna(valor):
                eje.text(j, i, f"{valor:.2f}", ha="center", va="center", fontsize=6.5, color="white" if abs(valor) > 0.6 else "black")
    figura.colorbar(imagen, ax=eje, shrink=0.8, label="Coeficiente de correlación (−1 a 1)")
    eje.set_title(titulo)
    return figura


def generar(panel: pd.DataFrame, carpeta: Path = RUTA_FIGURAS) -> dict[str, Any]:
    """Genera todas las figuras del EDA y devuelve las tablas y rutas que usa el informe.

    Args:
        panel: panel provincia × mes.
        carpeta: carpeta de salida de las figuras (PNG).

    Returns:
        Diccionario con `resumen`, `figuras` (nombre → ruta relativa), `correlaciones`, `colineales`,
        `atipicos_demanda`, `tabla_provincias` y cifras para el texto.
    """
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    figuras: dict[str, str] = {}
    datos = panel.copy()
    datos["mes"] = pd.to_datetime(datos["mes"])

    # 1. Histogramas de variables mensuales (C2 p.8)
    figura, ejes = plt.subplots(3, 3, figsize=(12, 9))
    for eje, (columna, etiqueta) in zip(ejes.flat, VARIABLES_MENSUALES.items()):
        valores = datos[columna].dropna()
        eje.hist(valores, bins=30, color=COLOR)
        eje.set_xlabel(etiqueta)
        eje.set_ylabel("Provincias × mes (nº)")
    figura.suptitle("Distribución de las variables mensuales del panel (52 provincias, 2015-2026)")
    figura.tight_layout()
    figuras["histogramas"] = _guardar(figura, "01_histogramas.png", carpeta)

    # 2. Box plots: estacionalidad de la temperatura y precio por año (C2 p.10)
    figura, (a, b) = plt.subplots(1, 2, figsize=(12, 4.2))
    por_mes = [datos.loc[datos["mes"].dt.month == m, "tmedia_mes_c"].dropna() for m in range(1, 13)]
    a.boxplot(por_mes, tick_labels=["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    a.set_title("Temperatura media mensual por mes del año")
    a.set_xlabel("Mes")
    a.set_ylabel("Temperatura media (°C)")
    precio = datos.drop_duplicates("mes")[["mes", "precio_spot_medio_mes_eur_mwh"]]
    anios = sorted(precio["mes"].dt.year.unique())
    b.boxplot([precio.loc[precio["mes"].dt.year == x, "precio_spot_medio_mes_eur_mwh"].dropna() for x in anios], tick_labels=[str(x)[2:] for x in anios])
    b.set_title("Precio spot medio mensual por año")
    b.set_xlabel("Año (20xx)")
    b.set_ylabel("Precio spot (€/MWh)")
    figura.tight_layout()
    figuras["boxplots"] = _guardar(figura, "02_boxplots.png", carpeta)

    # 3. Series temporales: demanda por comunidad con atípicos marcados (C2 p.6)
    marcada = marcar_atipicos_demanda(serie_demanda_ccaa(datos))
    serie = marcada[~marcada["atipico"]]
    atipicos = _atipicos_registrados(marcada)
    principales = serie.groupby("ccaa")["demanda_mwh"].median().nlargest(6).index
    figura, eje = plt.subplots(figsize=(12, 4.8))
    for ccaa in principales:
        s = serie[serie["ccaa"] == ccaa]
        eje.plot(s["mes"], s["demanda_mwh"] / 1e3, lw=1.2, label=ccaa)
        malos = atipicos[atipicos["ccaa"] == ccaa]
        eje.scatter(malos["mes"], malos["demanda_mwh"] / 1e3, marker="x", color="black", zorder=3, s=30)
    eje.scatter([], [], marker="x", color="black", label="dato atípico (excluido)")
    eje.set_title("Demanda eléctrica mensual de las 6 comunidades con más consumo (REData)")
    eje.set_xlabel("Mes")
    eje.set_ylabel("Demanda (GWh)")
    eje.legend(ncols=4, fontsize=8)
    figuras["serie_demanda"] = _guardar(figura, "03_serie_demanda.png", carpeta)

    figura, (a, b) = plt.subplots(1, 2, figsize=(12, 4.2))
    a.plot(precio["mes"], precio["precio_spot_medio_mes_eur_mwh"], color=COLOR_2)
    a.set_title("Precio spot medio mensual (nacional)")
    a.set_xlabel("Mes")
    a.set_ylabel("€/MWh")
    reservas = datos.dropna(subset=["reserva_hidrica_pct"]).drop_duplicates(["ambito_hidrografico", "mes"])
    for ambito in ("Tajo", "Guadalquivir", "Ebro", "Segura"):
        r = reservas[reservas["ambito_hidrografico"] == ambito]
        if not r.empty:
            b.plot(r["mes"], r["reserva_hidrica_pct"], lw=1.1, label=ambito)
    b.set_title("Reserva de los embalses por ámbito hidrográfico")
    b.set_xlabel("Mes")
    b.set_ylabel("Reserva (% de la capacidad)")
    b.legend(fontsize=8)
    figura.tight_layout()
    figuras["series_precio_agua"] = _guardar(figura, "04_series_precio_agua.png", carpeta)

    # 4. Barras: CPD por provincia (C2 p.7)
    tabla = _datos_simulacion(features_estaticas_provincia(datos))
    con_cpd = tabla[tabla["n_centros_datos"] > 0].sort_values("n_centros_datos")
    figura, eje = plt.subplots(figsize=(8, 5))
    eje.barh(con_cpd["provincia"], con_cpd["n_centros_datos"], color=COLOR)
    eje.set_title(f"Centros de datos por provincia (PeeringDB): {int(tabla['n_centros_datos'].sum())} en {len(con_cpd)} provincias")
    eje.set_xlabel("Centros de datos (nº)")
    figuras["barras_cpd"] = _guardar(figura, "05_barras_cpd.png", carpeta)

    # 5. Dispersión: variable objetivo frente a candidatas (C2 p.9)
    figura, (a, b) = plt.subplots(1, 2, figsize=(12, 4.5))
    poblacion = np.exp(tabla["log_poblacion"]) / 1e6
    a.scatter(poblacion, tabla["n_centros_datos"], color=COLOR)
    a.set_xscale("log")
    for _, fila in tabla[tabla["n_centros_datos"] >= 6].iterrows():
        a.annotate(fila["provincia"], (np.exp(fila["log_poblacion"]) / 1e6, fila["n_centros_datos"]), fontsize=8, xytext=(4, 2), textcoords="offset points")
    a.set_title("Centros de datos frente a población")
    a.set_xlabel("Población (millones de habitantes, escala log)")
    a.set_ylabel("Centros de datos (nº)")
    if "score_viabilidad" in tabla.columns:
        b.scatter(tabla["pct_horas_free_cooling"], tabla["score_viabilidad"], color=COLOR_2)
        b.set_title("Score de viabilidad simulado frente a free cooling")
        b.set_xlabel("Horas con free cooling (% medio 2016-2025)")
        b.set_ylabel("Score de viabilidad (0-100)")
    figura.tight_layout()
    figuras["dispersion"] = _guardar(figura, "06_dispersion.png", carpeta)

    # 6. Correlaciones por provincia (C2 p.11, p.23-24)
    columnas = [c for c in VARIABLES_PROVINCIA if c in tabla.columns]
    if "score_viabilidad" in tabla.columns:
        columnas += ["van_meur", "score_viabilidad"]
    etiquetas = [VARIABLES_PROVINCIA.get(c, {"van_meur": "VAN M€", "score_viabilidad": "score viabilidad"}.get(c, c)) for c in columnas]
    matrices = correlaciones(tabla, columnas)
    figuras["correlacion_pearson"] = _guardar(_heatmap(matrices["pearson"], "Correlación de Pearson entre variables por provincia (n = 52)", etiquetas), "07_correlacion_pearson.png", carpeta)
    figuras["correlacion_spearman"] = _guardar(_heatmap(matrices["spearman"], "Correlación de Spearman entre variables por provincia (n = 52)", etiquetas), "08_correlacion_spearman.png", carpeta)

    # 7. Pair plot de variables seleccionadas (C2 p.13)
    seleccion = ["log_poblacion", "renta_persona_eur", "pct_horas_free_cooling", "estres_hidrico_wri_0_1"]
    n = len(seleccion)
    figura, ejes = plt.subplots(n, n, figsize=(10, 10))
    colores = np.where(tabla["tiene_cpd"] == 1, COLOR_2, COLOR)
    for i, fila_var in enumerate(seleccion):
        for j, col_var in enumerate(seleccion):
            eje = ejes[i, j]
            if i == j:
                eje.hist(tabla[fila_var].dropna(), bins=12, color="#999999")
            else:
                eje.scatter(tabla[col_var], tabla[fila_var], c=colores, s=14)
            if i == n - 1:
                eje.set_xlabel(VARIABLES_PROVINCIA[col_var], fontsize=8)
            if j == 0:
                eje.set_ylabel(VARIABLES_PROVINCIA[fila_var], fontsize=8)
    figura.suptitle("Pair plot por provincia (naranja = tiene CPD, verde = no tiene)")
    figura.tight_layout()
    figuras["pair_plot"] = _guardar(figura, "09_pair_plot.png", carpeta)

    diferencias = (matrices["pearson"] - matrices["spearman"]).abs()
    temp_mes = datos.groupby(datos["mes"].dt.month)["tmedia_mes_c"].median()
    precio_anual = precio.groupby(precio["mes"].dt.year)["precio_spot_medio_mes_eur_mwh"].mean()
    demanda_anual = serie.groupby(serie["mes"].dt.year)["demanda_mwh"].sum()
    minimos_reserva = {}
    for ambito in ("Guadalquivir", "Segura"):
        r = reservas[reservas["ambito_hidrografico"] == ambito]
        if not r.empty:
            fila = r.loc[r["reserva_hidrica_pct"].idxmin()]
            minimos_reserva[ambito] = (fila["mes"].strftime("%Y-%m"), float(fila["reserva_hidrica_pct"]))
    cifras = {
        "temp_mediana_min": (int(temp_mes.idxmin()), float(temp_mes.min())),
        "temp_mediana_max": (int(temp_mes.idxmax()), float(temp_mes.max())),
        "precio_anual": {int(k): float(v) for k, v in precio_anual.items()},
        "asimetria": {c: float(datos[c].skew()) for c in ("precipitacion_mes_mm", "precio_spot_medio_mes_eur_mwh", "renta_neta_media_persona_eur", "paro_por_1000_hab")},
        "demanda_anual_twh": {int(k): float(v) / 1e6 for k, v in demanda_anual.items() if 2019 <= k <= 2023},
        "minimos_reserva": minimos_reserva,
    }
    return {
        "cifras": cifras,
        "resumen": resumen_general(panel),
        "figuras": figuras,
        "correlaciones": matrices,
        "etiquetas": dict(zip(columnas, etiquetas)),
        "colineales": pares_colineales(matrices["spearman"]),
        "diferencias_pearson_spearman": pares_colineales(diferencias.where(np.triu(np.ones(diferencias.shape, dtype=bool), 1)), umbral=0.25),
        "atipicos_demanda": atipicos[["ccaa", "mes", "demanda_mwh", "cociente_interanual", "motivo_atipico"]],
        "tabla_provincias": tabla,
        "filas_panel": len(panel),
        "columnas_panel": panel.shape[1],
        "rango_meses": (datos["mes"].min().strftime("%Y-%m"), datos["mes"].max().strftime("%Y-%m")),
    }
