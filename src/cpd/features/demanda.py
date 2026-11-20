"""Features para prever la demanda eléctrica mensual de cada comunidad autónoma (CCAA).

Esquema de previsión **directa** a `h` meses vista: para predecir el mes `t` solo se usan datos de los meses
`t − h` y anteriores. Así el mismo modelo sirve para prever los próximos `h` meses de una sola vez.

Para que comunidades de tamaños muy distintos (Andalucía frente a Melilla) compartan modelo, todo se expresa en
logaritmos y **relativo al nivel reciente**: `nivel = media de los 12 meses que terminan en t − h`. El objetivo
del modelo es `log(demanda_t) − log(nivel)`; la previsión en MWh se recupera con `exp(objetivo) × nivel`.

Fuente: `data/curated/panel_provincia_mes` (columna `demanda_ccaa_mwh`, Red Eléctrica REData).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from cpd.fuentes.calidad import CCAA_EXTRAPENINSULARES, marcar_atipicos_demanda

__all__ = ["CCAA_EXTRAPENINSULARES", "marcar_atipicos_demanda"]  # se reexportan: la regla vive en cpd.fuentes.calidad

# Meses con confinamiento por la COVID-19 (estado de alarma con restricción de actividad): marzo-junio de 2020.
MESES_CONFINAMIENTO: tuple[str, ...] = ("2020-03", "2020-04", "2020-05", "2020-06")


@dataclass(frozen=True)
class DefinicionFeature:
    """Una fila del diccionario de features (R-3)."""

    nombre: str
    formula: str
    ventana: str
    fuente: str
    riesgo_fuga: str


def serie_demanda_ccaa(panel: pd.DataFrame) -> pd.DataFrame:
    """Serie mensual de demanda por comunidad a partir del panel provincia × mes.

    La demanda del panel es de la comunidad (se repite en cada provincia), así que se toma una fila por
    comunidad y mes. Los meses sin dato quedan fuera (no se imputan, R-1).

    Args:
        panel: panel provincia × mes con `codigo_ccaa`, `ccaa`, `mes` y `demanda_ccaa_mwh` (MWh).

    Returns:
        DataFrame ordenado con `codigo_ccaa`, `ccaa`, `mes` (inicio de mes) y `demanda_mwh` (MWh).
    """
    columnas = ["codigo_ccaa", "ccaa", "mes", "demanda_ccaa_mwh"]
    serie = panel[columnas].drop_duplicates(["codigo_ccaa", "mes"]).dropna(subset=["demanda_ccaa_mwh"])
    serie = serie.rename(columns={"demanda_ccaa_mwh": "demanda_mwh"})
    serie["mes"] = pd.to_datetime(serie["mes"]).dt.to_period("M").dt.to_timestamp()
    serie["codigo_ccaa"] = serie["codigo_ccaa"].astype(str).str.zfill(2)
    return serie.sort_values(["codigo_ccaa", "mes"]).reset_index(drop=True)


def preparar_serie_modelo(serie: pd.DataFrame) -> pd.DataFrame:
    """Serie lista para construir features, con huecos y atípicos tratados y marcados (R-9, R-10).

    El curado (`cpd.fuentes.calidad.depurar_demanda_ccaa`) ya deja en NaN la demanda imposible; aquí se vuelve a
    aplicar la misma regla por si la serie viene de otra fuente.

    - Huecos o atípicos al final de la serie de una comunidad (p. ej. jul-ago de 2026): la serie termina antes.
    - Huecos o atípicos intermedios (p. ej. oct-2025 en Asturias): se sustituyen por la demanda del mismo mes del
      año anterior y se marcan con `imputado = True`. Solo sirven como entrada (lags y ventanas); nunca como
      objetivo ni para evaluar (ver `construir_features_demanda`).

    Args:
        serie: salida de `serie_demanda_ccaa`.

    Returns:
        DataFrame con `codigo_ccaa`, `ccaa`, `mes`, `demanda_mwh` (MWh), `imputado` (bool) y `sin_dato_valido`
        (bool: el mes no tenía dato o era atípico).
    """
    marcada = marcar_atipicos_demanda(serie)
    partes = []
    for (codigo, nombre), grupo in marcada.groupby(["codigo_ccaa", "ccaa"], sort=True):
        validos = grupo.loc[~grupo["atipico"], "mes"]
        if validos.empty:
            continue
        meses = pd.date_range(validos.min(), validos.max(), freq="MS")  # recorta lo inválido de los extremos
        grupo = grupo.set_index("mes").reindex(meses).rename_axis("mes")
        grupo["codigo_ccaa"], grupo["ccaa"] = codigo, nombre
        grupo["sin_dato_valido"] = grupo["atipico"].isna() | grupo["atipico"].astype("boolean").fillna(True)
        grupo["sin_dato_valido"] = grupo["sin_dato_valido"].astype(bool)
        grupo["imputado"] = False
        for mes in grupo.index[grupo["sin_dato_valido"]]:  # en orden: un hueco puede usar otro ya imputado
            previo = mes - pd.DateOffset(months=12)
            if previo in grupo.index and (not grupo.at[previo, "sin_dato_valido"] or grupo.at[previo, "imputado"]):
                grupo.at[mes, "demanda_mwh"] = grupo.at[previo, "demanda_mwh"]
                grupo.at[mes, "imputado"] = True
        grupo = grupo[~grupo["sin_dato_valido"] | grupo["imputado"]].reset_index()
        partes.append(grupo)
    salida = pd.concat(partes, ignore_index=True)
    return salida[["codigo_ccaa", "ccaa", "mes", "demanda_mwh", "imputado", "sin_dato_valido"]]


def _rejilla_completa(serie: pd.DataFrame, meses_extra: int) -> pd.DataFrame:
    """Rellena cada comunidad con todos los meses de su rango (+ `meses_extra` futuros) para que los desplazamientos
    por posición equivalgan a desplazamientos por calendario. Los meses añadidos quedan con demanda NaN."""
    filas = []
    serie = serie if "imputado" in serie.columns else serie.assign(imputado=False)
    for (codigo, nombre), grupo in serie.groupby(["codigo_ccaa", "ccaa"], sort=True):
        meses = pd.date_range(grupo["mes"].min(), grupo["mes"].max() + pd.DateOffset(months=meses_extra), freq="MS")
        rejilla = pd.DataFrame({"codigo_ccaa": codigo, "ccaa": nombre, "mes": meses})
        filas.append(rejilla.merge(grupo[["mes", "demanda_mwh", "imputado"]], on="mes", how="left"))
    tabla = pd.concat(filas, ignore_index=True)
    tabla["imputado"] = tabla["imputado"].astype("boolean").fillna(False).astype(bool)
    return tabla


def construir_features_demanda(serie: pd.DataFrame, horizonte: int, meses_futuros: int = 0) -> pd.DataFrame:
    """Tabla de features para prever la demanda del mes `t` con datos hasta `t − horizonte`.

    Args:
        serie: salida de `serie_demanda_ccaa` (una fila por comunidad y mes, `demanda_mwh` en MWh).
        horizonte: meses de antelación `h` (≥ 1). Ningún dato posterior a `t − h` entra en las features.
        meses_futuros: meses posteriores al último dato que se añaden sin objetivo (para la previsión final).

    Returns:
        DataFrame con claves (`codigo_ccaa`, `ccaa`, `mes`), `mes_referencia` (= t − h, último mes que se conoce),
        `nivel_mwh` (media de los 12 meses hasta `t − h`), las features (`f_*`), el objetivo `objetivo_log_ratio`
        y la demanda real `demanda_mwh` (NaN en los meses futuros). Se descartan las filas sin nivel completo.

    Raises:
        ValueError: si `horizonte` < 1.
    """
    if horizonte < 1:
        raise ValueError("El horizonte debe ser de al menos 1 mes")
    h = horizonte
    tabla = _rejilla_completa(serie, meses_futuros)
    grupos = tabla.groupby("codigo_ccaa", sort=False)["demanda_mwh"]
    log_d = np.log(tabla["demanda_mwh"])
    log_grupos = log_d.groupby(tabla["codigo_ccaa"], sort=False)

    tabla["mes_referencia"] = tabla["mes"] - pd.DateOffset(months=h)
    # Nivel: media de los 12 meses que terminan en t − h (incluido). min_periods=12 → sin huecos.
    tabla["nivel_mwh"] = grupos.transform(lambda s: s.shift(h).rolling(12, min_periods=12).mean())
    log_nivel = np.log(tabla["nivel_mwh"])

    # Lags (en log, relativos al nivel). Solo retardos k ≥ h.
    for k in sorted({h, h + 1, h + 2, max(12, h), 24}):
        if k < h:
            continue
        tabla[f"f_lag_{k}"] = log_grupos.shift(k) - log_nivel
    # Ventanas móviles de 3 y 6 meses que terminan en t − h, relativas al nivel; volatilidad de 12 meses.
    for v in (3, 6):
        media = grupos.transform(lambda s, v=v: s.shift(h).rolling(v, min_periods=v).mean())
        tabla[f"f_media_{v}m"] = np.log(media) - log_nivel
    tabla["f_desv_12m"] = log_grupos.transform(lambda s: s.diff().shift(h).rolling(12, min_periods=12).std())
    # Tendencia interanual del nivel: nivel(t − h) frente a nivel(t − h − 12).
    nivel_anterior = grupos.transform(lambda s: s.shift(h + 12).rolling(12, min_periods=12).mean())
    tabla["f_tendencia_anual"] = log_nivel - np.log(nivel_anterior)
    # Estacionalidad del mes objetivo (calendario: se conoce siempre).
    mes_num = tabla["mes"].dt.month
    tabla["f_mes_sin"] = np.sin(2 * np.pi * mes_num / 12)
    tabla["f_mes_cos"] = np.cos(2 * np.pi * mes_num / 12)
    for m in range(2, 13):
        tabla[f"f_mes_{m:02d}"] = (mes_num == m).astype(float)
    # Eventos conocidos (C4 p.18): confinamiento en el mes objetivo o en el mes de referencia.
    confinado = tabla["mes"].dt.strftime("%Y-%m").isin(MESES_CONFINAMIENTO)
    tabla["f_confinamiento"] = confinado.astype(float)
    tabla["f_confinamiento_ref"] = tabla["mes_referencia"].dt.strftime("%Y-%m").isin(MESES_CONFINAMIENTO).astype(float)

    tabla["objetivo_log_ratio"] = log_d - log_nivel
    # Un mes imputado nunca es objetivo ni se evalúa: solo ha servido como entrada de meses posteriores.
    tabla.loc[tabla["imputado"], ["objetivo_log_ratio", "demanda_mwh"]] = np.nan
    tabla["horizonte_meses"] = h
    columnas_f = columnas_features(tabla)
    tabla = tabla.dropna(subset=["nivel_mwh", *columnas_f]).reset_index(drop=True)
    return tabla


def columnas_features(tabla: pd.DataFrame) -> list[str]:
    """Nombres de las columnas de entrada del modelo (prefijo `f_`)."""
    return [c for c in tabla.columns if c.startswith("f_")]


def diccionario_features_demanda(horizonte: int) -> list[DefinicionFeature]:
    """Diccionario de las features de demanda para un horizonte `h` (fórmula, ventana y riesgo de fuga)."""
    h = horizonte
    fuente = "Red Eléctrica REData (demanda_ccaa_mwh del panel)"
    filas = [
        DefinicionFeature(f"f_lag_{k}", f"log(demanda(t−{k})) − log(nivel)", f"1 mes (t−{k})", fuente, f"Ninguno: {k} ≥ h={h}")
        for k in sorted({h, h + 1, h + 2, max(12, h), 24})
    ]
    filas += [
        DefinicionFeature(f"f_media_{v}m", f"log(media de {v} meses hasta t−{h}) − log(nivel)", f"{v} meses", fuente, "Ninguno")
        for v in (3, 6)
    ]
    filas += [
        DefinicionFeature("f_desv_12m", f"desviación típica de Δlog(demanda) en los 12 meses hasta t−{h}", "12 meses", fuente, "Ninguno"),
        DefinicionFeature("f_tendencia_anual", f"log(nivel en t−{h}) − log(nivel en t−{h}−12)", "24 meses", fuente, "Ninguno"),
        DefinicionFeature("f_mes_sin, f_mes_cos", "sin y cos de 2π·mes/12 del mes objetivo", "calendario", "calendario", "Ninguno: el calendario se conoce"),
        DefinicionFeature("f_mes_02 … f_mes_12", "1 si el mes objetivo es ese mes (enero es la referencia)", "calendario", "calendario", "Ninguno"),
        DefinicionFeature("f_confinamiento", "1 si el mes objetivo está entre 2020-03 y 2020-06", "evento", "BOE (estado de alarma)", "Evento conocido a posteriori: solo afecta a entrenamiento"),
        DefinicionFeature("f_confinamiento_ref", "1 si el mes de referencia t−h está entre 2020-03 y 2020-06", "evento", "BOE (estado de alarma)", "Ninguno"),
    ]
    filas.append(
        DefinicionFeature(
            "objetivo_log_ratio",
            f"log(demanda(t)) − log(nivel), con nivel = media de los 12 meses hasta t−{h} — OBJETIVO, nunca entrada",
            "1 mes (t)",
            fuente,
            "Es el objetivo",
        )
    )
    return filas
