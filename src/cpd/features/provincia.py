"""Features estáticas por provincia para estimar la probabilidad de que una provincia tenga un CPD.

Es un problema **transversal** (una fila por provincia), no una serie temporal: la etiqueta es si la provincia tiene
hoy al menos un centro de datos registrado en PeeringDB (`n_centros_datos > 0`) y las features describen la
provincia con el último año completo de cada fuente. No hay fechas de apertura de los CPD, así que no se puede
hacer una validación temporal; se valida con validación cruzada estratificada (ver `cpd.modelos.prob_cpd`).

Fuga (R-8): se excluyen `n_ixp` y `distancia_ixp_km`, porque los puntos de intercambio (IXP) se alojan dentro de
centros de datos: tener un IXP en la provincia implica tener un CPD, y eso sería usar la etiqueta como entrada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cpd.features.demanda import DefinicionFeature

# Provincias insulares o fuera de la península (sistemas eléctricos aislados): Baleares, Las Palmas, Santa Cruz de
# Tenerife, Ceuta y Melilla.
CODIGOS_EXTRAPENINSULARES: frozenset[str] = frozenset({"07", "35", "38", "51", "52"})

# Columnas del panel que NO se pueden usar como entrada (fuga de la etiqueta).
EXCLUIDAS_POR_FUGA: tuple[str, ...] = ("n_centros_datos", "n_ixp", "distancia_ixp_km")

FEATURES_PROVINCIA: tuple[str, ...] = (
    "log_poblacion",
    "renta_persona_eur",
    "paro_por_1000_hab",
    "tmedia_anual_c",
    "pct_horas_free_cooling",
    "estres_hidrico_wri_0_1",
    "subestaciones_220_400kv",
    "pct_superficie_natura2000",
    "capacidad_acceso_ccaa_mw",
    "terremotos_m3_por_anio",
    "extrapeninsular",
)


def _ultimo_anio_completo(panel: pd.DataFrame, columna: str) -> int:
    """Último año en el que todas las provincias con la columna tienen dato en algún mes."""
    con_dato = panel.dropna(subset=[columna])
    cobertura = con_dato.groupby(con_dato["mes"].dt.year)["codigo_provincia"].nunique()
    maximo = cobertura.max()
    return int(cobertura[cobertura >= maximo * 0.95].index.max())


def features_estaticas_provincia(panel: pd.DataFrame) -> pd.DataFrame:
    """Una fila por provincia con las features del modelo `prob_cpd` y su etiqueta.

    Args:
        panel: panel provincia × mes (`data/curated/panel_provincia_mes`).

    Returns:
        DataFrame indexado por `codigo_provincia` con `provincia`, `ccaa`, las columnas de `FEATURES_PROVINCIA`,
        `n_centros_datos` (nº, solo para informar) y la etiqueta `tiene_cpd` (0/1). Los valores ausentes quedan en
        NaN: la imputación se hace dentro de la validación cruzada (R-7, R-9).
    """
    datos = panel.copy()
    datos["mes"] = pd.to_datetime(datos["mes"])
    datos["codigo_provincia"] = datos["codigo_provincia"].astype(str).str.zfill(2)
    anio = datos["mes"].dt.year
    clave = "codigo_provincia"

    base = datos.sort_values("mes").groupby(clave).last()[["provincia", "ccaa", "n_centros_datos"]]

    # Población (habitantes) del último año con dato → log, muy asimétrica (C4 p.25).
    anio_pob = _ultimo_anio_completo(datos, "poblacion")
    poblacion = datos[anio == anio_pob].groupby(clave)["poblacion"].mean()
    # Renta neta media por persona (€/año) del último año publicado por el INE.
    anio_renta = _ultimo_anio_completo(datos, "renta_neta_media_persona_eur")
    renta = datos[anio == anio_renta].groupby(clave)["renta_neta_media_persona_eur"].mean()
    # Paro por 1.000 habitantes: media de los 12 últimos meses con dato.
    paro = datos.dropna(subset=["paro_por_1000_hab"]).groupby(clave).apply(
        lambda g: g.sort_values("mes")["paro_por_1000_hab"].tail(12).mean(), include_groups=False
    )
    # Clima: medias de los años completos 2016-2025 (10 años).
    clima = datos[(anio >= 2016) & (anio <= 2025)].groupby(clave)[["tmedia_mes_c", "pct_horas_free_cooling"]].mean()
    # Sismicidad: terremotos de magnitud ≥ 3 al año (el dato del panel es anual y se repite cada mes).
    por_anio = datos.assign(anio=anio).drop_duplicates([clave, "anio"])
    terremotos = por_anio[por_anio["anio"] <= 2025].groupby(clave)["n_terremotos_m3_plus"].mean()
    estatico = datos.sort_values("mes").groupby(clave).last()[
        ["estres_hidrico_wri_0_1", "subestaciones_220_400kv", "pct_superficie_natura2000", "capacidad_demanda_rdt_disponible_mw"]
    ]

    tabla = base.join(
        pd.DataFrame(
            {
                "log_poblacion": np.log(poblacion),
                "renta_persona_eur": renta,
                "paro_por_1000_hab": paro,
                "tmedia_anual_c": clima["tmedia_mes_c"],
                "pct_horas_free_cooling": clima["pct_horas_free_cooling"],
                "terremotos_m3_por_anio": terremotos,
            }
        )
    ).join(estatico)
    tabla = tabla.rename(columns={"capacidad_demanda_rdt_disponible_mw": "capacidad_acceso_ccaa_mw"})
    tabla["extrapeninsular"] = tabla.index.isin(CODIGOS_EXTRAPENINSULARES).astype(float)
    tabla["tiene_cpd"] = (tabla["n_centros_datos"] > 0).astype(int)
    tabla.attrs["anios_referencia"] = {"poblacion": anio_pob, "renta": anio_renta, "clima": "2016-2025"}
    return tabla[["provincia", "ccaa", *FEATURES_PROVINCIA, "n_centros_datos", "tiene_cpd"]].sort_index()


def diccionario_features_provincia() -> list[DefinicionFeature]:
    """Diccionario de las features de `prob_cpd` (fórmula, ventana, fuente y riesgo de fuga)."""
    return [
        DefinicionFeature("log_poblacion", "log(población a 1 de enero)", "último año publicado", "INE (padrón)", "Ninguno"),
        DefinicionFeature("renta_persona_eur", "renta neta media por persona (€/año)", "último año publicado", "INE ADRH", "Ninguno"),
        DefinicionFeature("paro_por_1000_hab", "paro registrado por 1.000 habitantes, media", "12 últimos meses", "SEPE + INE", "Ninguno"),
        DefinicionFeature("tmedia_anual_c", "media de la temperatura media mensual (°C)", "2016-2025", "NASA POWER", "Ninguno"),
        DefinicionFeature("pct_horas_free_cooling", "media del % de horas por debajo de 18 °C", "2016-2025", "NASA POWER", "Ninguno"),
        DefinicionFeature("estres_hidrico_wri_0_1", "estrés hídrico de referencia de la comunidad (0-1)", "estática", "WRI Aqueduct 4.0", "Ninguno"),
        DefinicionFeature("subestaciones_220_400kv", "nº de subestaciones de 220 o 400 kV", "estática", "OpenStreetMap", "Ninguno"),
        DefinicionFeature("pct_superficie_natura2000", "% de superficie en Red Natura 2000", "estática", "EEA Natura 2000", "Ninguno"),
        DefinicionFeature("capacidad_acceso_ccaa_mw", "capacidad de acceso disponible para demanda (MW, comunidad)", "estática", "Red Eléctrica", "Ninguno; es de la comunidad, no de la provincia"),
        DefinicionFeature("terremotos_m3_por_anio", "media anual de terremotos de magnitud ≥ 3", "2015-2025", "EMSC", "Ninguno"),
        DefinicionFeature("extrapeninsular", "1 si es Baleares, Canarias, Ceuta o Melilla", "estática", "INE (códigos)", "Ninguno"),
        DefinicionFeature("tiene_cpd", "1 si n_centros_datos > 0 — ETIQUETA, nunca entrada", "estática (2026)", "PeeringDB", "Es la etiqueta"),
        DefinicionFeature("n_ixp, distancia_ixp_km", "EXCLUIDAS", "—", "PeeringDB", "Fuga: los IXP se alojan en centros de datos"),
    ]
