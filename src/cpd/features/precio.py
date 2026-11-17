"""Features para prever el precio medio mensual de la electricidad (mercado spot, España peninsular).

Previsión **directa** con un solo modelo para todos los horizontes: cada fila es un par (origen `r`, horizonte `h`)
y predice el mes `t = r + h` con datos conocidos hasta `r`. El objetivo es `log(precio_t) − log(nivel_r)`, con
`nivel_r` = media de los 12 meses que terminan en `r` (el mismo precio que usa hoy el simulador).

Fuentes (tablas de `data/curated/tablas/`):
- `precios_diarios`: precio spot diario (REData/OMIE, €/MWh) → media mensual.
- `reservas_ambito_mensual`: agua embalsada de los 16 ámbitos (MITECO) → reserva nacional (%). Más agua, más
  generación hidráulica barata.
- `co2`: emisiones del sistema eléctrico (REData, tCO2 eq.) → peso de la generación térmica (gas y carbón).

Limitación conocida: no hay precio del gas (MIBGAS/TTF), que explica la mayor parte de los picos de 2021-2022.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from cpd.features.demanda import DefinicionFeature

HORIZONTES: tuple[int, ...] = tuple(range(1, 13))


def _mes(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie).dt.to_period("M").dt.to_timestamp()


def serie_precio_mensual(precios_diarios: pd.DataFrame, hoy: dt.date | None = None) -> pd.Series:
    """Precio spot medio de cada mes completo (€/MWh). Quita el mes en curso y los meses con días sin dato.

    Args:
        precios_diarios: tabla con `fecha` y `precio_spot_eur_mwh` (€/MWh).
        hoy: fecha de referencia para el mes en curso (por defecto, hoy).
    """
    datos = precios_diarios.dropna(subset=["precio_spot_eur_mwh"]).assign(mes=lambda d: _mes(d["fecha"]))
    resumen = datos.groupby("mes")["precio_spot_eur_mwh"].agg(["mean", "count"])
    dias_mes = resumen.index.days_in_month
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    completos = (resumen["count"] >= dias_mes) & (resumen.index < en_curso)
    return resumen.loc[completos, "mean"].rename("precio_eur_mwh")


def serie_reserva_nacional(reservas: pd.DataFrame) -> pd.Series:
    """Reserva hídrica nacional (% de la capacidad) por mes: suma de volúmenes / suma de capacidades de los ámbitos.

    Solo cuenta los meses con todos los ámbitos (si falta alguno, el total no es comparable).
    """
    datos = reservas.assign(mes=_mes(reservas["mes"]))
    total = datos.groupby("mes").agg(
        ambitos=("ambito", "nunique"),
        volumen=("volumen_hm3_media_mes", "sum"),
        capacidad=("capacidad_hm3_media_mes", "sum"),
    )
    completos = total["ambitos"] == total["ambitos"].max()
    return (total.loc[completos, "volumen"] / total.loc[completos, "capacidad"] * 100).rename("reserva_nacional_pct")


def serie_co2(co2: pd.DataFrame, hoy: dt.date | None = None) -> pd.Series:
    """Emisiones mensuales del sistema eléctrico (tCO2 eq.), sin el mes en curso."""
    datos = co2.assign(mes=_mes(co2["fecha"])).groupby("mes")["emisiones_co2_tco2eq"].sum()
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    return datos[datos.index < en_curso].rename("co2_tco2eq")


def series_gas(gas_diario: pd.DataFrame, gas_futuros: pd.DataFrame, hoy: dt.date | None = None) -> pd.DataFrame:
    """Gas mensual (MIBGAS, €/MWh): spot medio del mes y precio medio de los futuros negociados en ese mes.

    Columnas: `gas_spot_eur_mwh`, `gas_m1_eur_mwh` (mes siguiente), `gas_q1_eur_mwh` (trimestre siguiente) y
    `gas_y1_eur_mwh` (año natural siguiente). Un mes sin negociación de un futuro toma el último valor conocido
    (hasta 2 meses): es lo que se sabría en ese momento. Sin el mes en curso.
    """
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    spot = gas_diario.assign(mes=_mes(gas_diario["fecha"])).groupby("mes")["gas_mibgas_es_eur_mwh"].mean()
    tabla = pd.DataFrame({"gas_spot_eur_mwh": spot})
    futuros = gas_futuros.assign(mes=_mes(gas_futuros["fecha"]))
    for producto, columna in (("M+1", "gas_m1_eur_mwh"), ("Q+1", "gas_q1_eur_mwh"), ("Y+1", "gas_y1_eur_mwh")):
        serie = futuros[futuros["producto"] == producto].groupby("mes")["precio_eur_mwh"].mean()
        tabla = tabla.join(serie.rename(columna), how="outer")
    tabla = tabla.sort_index()
    tabla = tabla.reindex(pd.date_range(tabla.index.min(), tabla.index.max(), freq="MS")).ffill(limit=2)
    return tabla[tabla.index < en_curso]


def tabla_mensual(precio: pd.Series, reserva: pd.Series, co2: pd.Series, gas: pd.DataFrame | None = None) -> pd.DataFrame:
    """Une las series en una tabla mensual continua (los meses sin dato quedan en NaN). `gas` es opcional
    (salida de `series_gas`)."""
    meses = pd.date_range(precio.index.min(), precio.index.max(), freq="MS")
    tabla = pd.DataFrame(index=pd.Index(meses, name="mes")).join([precio, reserva, co2])
    return tabla.join(gas) if gas is not None else tabla


def construir_features_precio(mensual: pd.DataFrame, horizontes: tuple[int, ...] = HORIZONTES, meses_futuros: int = 0) -> pd.DataFrame:
    """Filas (origen, horizonte) con features calculadas solo con datos hasta el origen `r = t − h`.

    Args:
        mensual: salida de `tabla_mensual` (índice `mes`; `precio_eur_mwh`, `reserva_nacional_pct`, `co2_tco2eq`).
        horizontes: meses de antelación (1 a 12).
        meses_futuros: meses posteriores al último precio que se añaden sin objetivo (previsión final).

    Returns:
        DataFrame con `mes` (objetivo), `mes_origen`, `horizonte_meses`, `nivel_eur_mwh`, features `f_*`,
        `objetivo_log_ratio` y `precio_eur_mwh` real (NaN en el futuro). Sin filas con features incompletas.

    Raises:
        ValueError: si algún horizonte es menor que 1 o mayor que 12.
    """
    if min(horizontes) < 1 or max(horizontes) > 12:
        raise ValueError("Los horizontes deben estar entre 1 y 12 meses")
    meses = pd.date_range(mensual.index.min(), mensual.index.max() + pd.DateOffset(months=meses_futuros), freq="MS")
    datos = mensual.reindex(meses)
    log_p = np.log(datos["precio_eur_mwh"])
    nivel = datos["precio_eur_mwh"].rolling(12, min_periods=12).mean()
    media3 = datos["precio_eur_mwh"].rolling(3, min_periods=3).mean()
    volatilidad = log_p.diff().rolling(12, min_periods=12).std()
    reserva = datos["reserva_nacional_pct"] / 100
    co2_rel = np.log(datos["co2_tco2eq"]) - np.log(datos["co2_tco2eq"].rolling(12, min_periods=12).mean())
    hay_gas = "gas_spot_eur_mwh" in datos.columns
    if hay_gas:
        # Gas relativo a su propio nivel de 12 meses: cuánto espera el mercado que suba o baje el gas.
        log_gas_nivel = np.log(datos["gas_spot_eur_mwh"].rolling(12, min_periods=12).mean())
        gas_rel = {
            "f_gas_spot": np.log(datos["gas_spot_eur_mwh"]) - log_gas_nivel,
            "f_gas_trimestre": np.log(datos["gas_q1_eur_mwh"]) - log_gas_nivel,
            "f_gas_anio": np.log(datos["gas_y1_eur_mwh"]) - log_gas_nivel,
        }
    partes = []
    for h in horizontes:
        log_nivel = np.log(nivel.shift(h))
        tabla = pd.DataFrame(index=meses)
        tabla["mes"] = meses
        tabla["mes_origen"] = meses - pd.DateOffset(months=h)
        tabla["horizonte_meses"] = h
        tabla["nivel_eur_mwh"] = nivel.shift(h)
        tabla["f_ultimo"] = log_p.shift(h) - log_nivel
        tabla["f_penultimo"] = log_p.shift(h + 1) - log_nivel
        tabla["f_media_3m"] = np.log(media3.shift(h)) - log_nivel
        tabla["f_mismo_mes_anio_anterior"] = log_p.shift(12) - log_nivel  # t − 12 ≤ r porque h ≤ 12
        tabla["f_tendencia_anual"] = log_nivel - np.log(nivel.shift(h + 12))
        tabla["f_volatilidad_12m"] = volatilidad.shift(h)
        tabla["f_reserva_hidrica"] = reserva.shift(h)
        tabla["f_reserva_variacion_anual"] = reserva.shift(h) - reserva.shift(h + 12)
        tabla["f_co2_relativo"] = co2_rel.shift(h)
        tabla["f_mes_sin"] = np.sin(2 * np.pi * tabla["mes"].dt.month / 12)
        tabla["f_mes_cos"] = np.cos(2 * np.pi * tabla["mes"].dt.month / 12)
        tabla["f_horizonte"] = h / 12
        if hay_gas:
            for nombre, serie in gas_rel.items():
                tabla[nombre] = serie.shift(h)
        tabla["precio_eur_mwh"] = datos["precio_eur_mwh"]
        tabla["objetivo_log_ratio"] = log_p - log_nivel
        partes.append(tabla)
    salida = pd.concat(partes, ignore_index=True)
    return salida.dropna(subset=columnas_features(salida)).reset_index(drop=True)


def columnas_features(tabla: pd.DataFrame) -> list[str]:
    """Columnas de entrada del modelo (prefijo `f_`)."""
    return [c for c in tabla.columns if c.startswith("f_")]


def diccionario_features_precio() -> list[DefinicionFeature]:
    """Diccionario de las features del precio (r = mes de origen = t − h)."""
    fuente = "REData/OMIE (precios_diarios)"
    return [
        DefinicionFeature("f_ultimo", "log(precio(r)) − log(nivel(r)); nivel = media de 12 meses hasta r", "1 mes", fuente, "Ninguno: r = t − h"),
        DefinicionFeature("f_penultimo", "log(precio(r−1)) − log(nivel(r))", "1 mes", fuente, "Ninguno"),
        DefinicionFeature("f_media_3m", "log(media de 3 meses hasta r) − log(nivel(r))", "3 meses", fuente, "Ninguno"),
        DefinicionFeature("f_mismo_mes_anio_anterior", "log(precio(t−12)) − log(nivel(r))", "1 mes", fuente, "Ninguno: t − 12 ≤ r porque h ≤ 12"),
        DefinicionFeature("f_tendencia_anual", "log(nivel(r)) − log(nivel(r−12))", "24 meses", fuente, "Ninguno"),
        DefinicionFeature("f_volatilidad_12m", "desviación típica de Δlog(precio) en los 12 meses hasta r", "12 meses", fuente, "Ninguno"),
        DefinicionFeature("f_reserva_hidrica", "reserva nacional de embalses en r (0-1)", "1 mes", "MITECO (16 ámbitos)", "Ninguno"),
        DefinicionFeature("f_reserva_variacion_anual", "reserva(r) − reserva(r−12)", "12 meses", "MITECO", "Ninguno"),
        DefinicionFeature("f_co2_relativo", "log(CO2(r)) − log(media de 12 meses del CO2 hasta r)", "12 meses", "REData (co2)", "Ninguno"),
        DefinicionFeature("f_mes_sin, f_mes_cos", "seno y coseno de 2π·mes/12 del mes objetivo t", "calendario", "calendario", "Ninguno"),
        DefinicionFeature("f_horizonte", "h / 12", "—", "—", "Ninguno"),
        DefinicionFeature("f_gas_spot", "log(gas spot medio de r) − log(media de 12 meses del gas hasta r)", "12 meses", "MIBGAS", "Ninguno"),
        DefinicionFeature("f_gas_trimestre", "log(futuro de gas del trimestre siguiente negociado en r) − log(nivel del gas)", "1 mes", "MIBGAS", "Ninguno: precio publicado en r"),
        DefinicionFeature("f_gas_anio", "log(futuro de gas del año siguiente negociado en r) − log(nivel del gas)", "1 mes", "MIBGAS", "Ninguno: precio publicado en r"),
        DefinicionFeature("objetivo_log_ratio", "log(precio(t)) − log(nivel(r)) — OBJETIVO, nunca entrada", "1 mes (t)", fuente, "Es el objetivo"),
    ]
