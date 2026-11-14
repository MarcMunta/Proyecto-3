"""Construye las dos salidas listas para entrenar modelos a partir de las tablas por API.

- ``panel_provincia_mes``: provincia x mes (desde 2015-01 hasta el último mes con datos), una columna por
  variable; NaN donde la fuente no tiene dato. Variables anuales se repiten en los meses de su año y las
  variables "estáticas" (foto de una descarga) se repiten en todos los meses (ver diccionario).
- ``provincias_actual``: 52 filas con el último valor disponible de cada variable y los campos de tiempo real.

Las tablas de entrada son las que escribe ``actualizar`` en data/curated/tablas/*.csv. Este módulo es
puro (no descarga nada), así que se puede probar sin conexión.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from cpd.config import RUTA_RAIZ
from cpd.fuentes import agua
from cpd.fuentes.embalses import AMBITO_POR_PROVINCIA
from cpd.fuentes.provincias import CODIGOS

CARPETA_CURADO: Path = RUTA_RAIZ / "data" / "curated"
CARPETA_TABLAS: Path = CARPETA_CURADO / "tablas"
ANIO_INICIO: int = 2015
CLAVES: tuple[str, ...] = ("codigo_provincia", "mes")


@dataclass(frozen=True)
class Campo:
    """Descripción de una columna de las salidas (para el diccionario de datos)."""

    nombre: str
    descripcion: str
    unidad: str
    fuente: str
    nivel: str  # provincia | ccaa | nacional | provincia (estático) ...
    frecuencia: str  # diaria/mensual/anual/estática/tiempo real


DICCIONARIO: tuple[Campo, ...] = (
    Campo("codigo_provincia", "Código INE de provincia (dos dígitos)", "-", "INE", "provincia", "-"),
    Campo("mes", "Primer día del mes de referencia", "fecha", "-", "-", "mensual"),
    Campo("provincia", "Nombre de la provincia", "-", "INE", "provincia", "estática"),
    Campo("ccaa", "Comunidad autónoma", "-", "INE", "provincia", "estática"),
    Campo("codigo_ccaa", "Código INE de comunidad autónoma", "-", "INE", "provincia", "estática"),
    Campo("tmedia_mes_c", "Temperatura media del aire del mes (media de medias diarias)", "°C", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("tmax_media_c", "Media mensual de la temperatura máxima diaria", "°C", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("tmin_media_c", "Media mensual de la temperatura mínima diaria", "°C", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("precipitacion_mes_mm", "Precipitación acumulada en el mes", "mm", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("humedad_relativa_media_pct", "Humedad relativa media del mes", "%", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("viento_medio_kmh", "Velocidad media del viento a 10 m", "km/h", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("radiacion_solar_media_kwh_m2_dia", "Radiación solar global media diaria del mes", "kWh/m²/día", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("et0_hargreaves_mes_mm", "ET0 de referencia (Hargreaves-Samani) acumulada en el mes; NaN si el mes está incompleto", "mm", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("dias_mas_35c", "Días del mes con temperatura máxima >= 35 °C", "días", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("balance_hidrico_mes_mm", "Balance hídrico climático del mes: precipitación − ET0 Hargreaves (negativo = demanda superior a la lluvia)", "mm", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("precipitacion_12m_mm", "Precipitación acumulada en los últimos 12 meses", "mm", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("indice_sequia_12m", "Índice de sequía a 12 meses (z-score del acumulado frente a su mismo mes del calendario; < -1 sequía moderada)", "z", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("dias_con_clima", "Días del mes con dato climático (un mes parcial tiene menos)", "días", "NASA POWER diario (MERRA-2)", "provincia", "mensual"),
    Campo("horas_free_cooling", "Horas del mes con temperatura < 18 °C (free-cooling)", "horas", "NASA POWER horario (MERRA-2)", "provincia", "mensual"),
    Campo("pct_horas_free_cooling", "Porcentaje de horas del mes con temperatura < 18 °C", "%", "NASA POWER horario (MERRA-2)", "provincia", "mensual"),
    Campo("demanda_ccaa_mwh", "Demanda eléctrica mensual de la comunidad autónoma (REData)", "MWh", "Red Eléctrica REData", "ccaa", "mensual"),
    Campo("generacion_total_ccaa_mwh", "Generación eléctrica mensual de la comunidad (todas las tecnologías)", "MWh", "Red Eléctrica REData", "ccaa", "mensual"),
    Campo("generacion_renovable_ccaa_mwh", "Generación renovable mensual de la comunidad", "MWh", "Red Eléctrica REData", "ccaa", "mensual"),
    Campo("pct_renovable_ccaa", "Porcentaje renovable de la generación de la comunidad", "%", "Red Eléctrica REData", "ccaa", "mensual"),
    Campo("emisiones_co2_nacional_tco2eq", "Emisiones de CO2 del sistema eléctrico (total nacional)", "tCO2 eq.", "Red Eléctrica REData", "nacional", "mensual"),
    Campo("precio_spot_medio_mes_eur_mwh", "Precio medio mensual del mercado spot (media de días)", "€/MWh", "Red Eléctrica REData (OMIE)", "nacional", "mensual"),
    Campo("precio_pvpc_medio_mes_eur_mwh", "Precio medio mensual PVPC (tarifa regulada) (media de días)", "€/MWh", "Red Eléctrica REData", "nacional", "mensual"),
    Campo("poblacion", "Población residente a 1 de enero del año (Tempus3 hasta 2021; padrón municipal 2022 en adelante)", "habitantes", "INE Tempus3 (2852) y padrón (29005)", "provincia", "anual"),
    Campo("fuente_poblacion", "Tabla de la que procede la población de ese año", "-", "INE", "provincia", "anual"),
    Campo("diferencia_padron_vs_tempus_pct", "Diferencia relativa padrón frente a Tempus3 en los años solapados (control de consistencia)", "%", "INE", "provincia", "anual"),
    Campo("temp_prevision_7d_media_c", "Temperatura media prevista para los próximos 7 días en la capital", "°C", "Open-Meteo (forecast)", "provincia", "tiempo real"),
    Campo("temp_prevision_7d_max_c", "Temperatura máxima prevista para los próximos 7 días en la capital", "°C", "Open-Meteo (forecast)", "provincia", "tiempo real"),
    Campo("precipitacion_prevision_7d_mm", "Precipitación prevista para los próximos 7 días en la capital", "mm", "Open-Meteo (forecast)", "provincia", "tiempo real"),
    Campo("renta_neta_media_persona_eur", "Renta neta media por persona del año", "€/año", "INE ADRH (53689)", "provincia", "anual"),
    Campo("renta_neta_media_hogar_eur", "Renta neta media por hogar del año", "€/año", "INE ADRH (53689)", "provincia", "anual"),
    Campo("mediana_renta_unidad_consumo_eur", "Mediana de la renta por unidad de consumo del año", "€/año", "INE ADRH (53689)", "provincia", "anual"),
    Campo("paro_registrado", "Paro registrado a fin de mes (suma de municipios)", "personas", "SEPE", "provincia", "mensual"),
    Campo("paro_por_1000_hab", "Paro registrado por cada 1.000 habitantes (población del año)", "por mil", "SEPE + INE", "provincia", "mensual"),
    Campo("n_centros_datos", "Centros de datos (PeeringDB 'facility') en la provincia", "nº", "PeeringDB", "provincia", "estática"),
    Campo("n_ixp", "Puntos de intercambio de tráfico (IXP) en la provincia", "nº", "PeeringDB", "provincia", "estática"),
    Campo("distancia_ixp_km", "Distancia desde la capital al IXP más cercano (aprox. por ciudad del IXP)", "km", "PeeringDB", "provincia", "estática"),
    Campo("subestaciones_220_400kv", "Subestaciones de 220 o 400 kV mapeadas en OpenStreetMap", "nº", "OpenStreetMap (Overpass)", "provincia", "estática"),
    Campo("subestaciones_400kv", "Subestaciones de 400 kV mapeadas en OpenStreetMap", "nº", "OpenStreetMap (Overpass)", "provincia", "estática"),
    Campo("capacidad_demanda_rdt_disponible_mw", "Capacidad de acceso disponible para demanda en red de transporte (comunidad)", "MW", "Red Eléctrica (capacidad de acceso)", "ccaa", "estática"),
    Campo("nudos_acceso_ccaa", "Nudos de la red de transporte de la comunidad con datos de capacidad", "nº", "Red Eléctrica (capacidad de acceso)", "ccaa", "estática"),
    Campo("pct_superficie_natura2000", "Porcentaje de la superficie provincial en Red Natura 2000", "%", "EEA Natura 2000", "provincia", "estática"),
    Campo("espacios_natura_2000", "Espacios Natura 2000 que intersecan la provincia", "nº", "EEA Natura 2000", "provincia", "estática"),
    Campo("n_terremotos", "Terremotos M>=1.5 con epicentro en la provincia durante el año", "nº", "EMSC (FDSN)", "provincia", "anual"),
    Campo("magnitud_max", "Magnitud máxima de los terremotos del año en la provincia", "Mw/ML", "EMSC (FDSN)", "provincia", "anual"),
    Campo("n_terremotos_m3_plus", "Terremotos M>=3.0 del año en la provincia", "nº", "EMSC (FDSN)", "provincia", "anual"),
    Campo("temperatura_actual_c", "Temperatura del aire en la capital (tiempo real)", "°C", "Open-Meteo (forecast current)", "provincia", "tiempo real"),
    Campo("humedad_relativa_actual_pct", "Humedad relativa actual en la capital", "%", "Open-Meteo (forecast current)", "provincia", "tiempo real"),
    Campo("viento_actual_kmh", "Viento actual a 10 m en la capital", "km/h", "Open-Meteo (forecast current)", "provincia", "tiempo real"),
    Campo("precipitacion_actual_mm", "Precipitación en el último intervalo en la capital", "mm", "Open-Meteo (forecast current)", "provincia", "tiempo real"),
    Campo("momento_observacion", "Hora local de la observación de tiempo actual", "fecha-hora", "Open-Meteo (forecast current)", "provincia", "tiempo real"),
    Campo("demanda_tiempo_real_mw", "Última demanda real publicada, sistema peninsular (cada 5 min)", "MW", "Red Eléctrica REData", "nacional", "tiempo real"),
    Campo("precio_spot_actual_eur_mwh", "Último precio spot publicado (cuarto de hora)", "€/MWh", "Red Eléctrica REData", "nacional", "tiempo real"),
    Campo("precio_spot_manana_medio_eur_mwh", "Precio spot medio del día siguiente (OMIE), si ya está publicado", "€/MWh", "OMIE marginalpdbc", "nacional", "tiempo real"),
    Campo("ambito_hidrografico", "Ámbito hidrográfico dominante de la provincia (asignación estática aproximada)", "-", "MITECO (embalses) + criterio propio", "provincia", "estática"),
    Campo("reserva_hidrica_pct", "Reserva de los embalses del ámbito: media mensual de las semanas del mes", "%", "MITECO embalses semanal", "ámbito (se asigna a la provincia)", "mensual"),
    Campo("reserva_hidrica_hm3", "Volumen embalsado del ámbito: media mensual de las semanas del mes", "hm³", "MITECO embalses semanal", "ámbito (se asigna a la provincia)", "mensual"),
    Campo("capacidad_embalses_ambito_hm3", "Capacidad total de los embalses del ámbito (media mensual)", "hm³", "MITECO embalses semanal", "ámbito (se asigna a la provincia)", "mensual"),
    Campo("semanas_reserva_mes", "Semanas con dato de reservas en el mes (un mes parcial tiene menos)", "nº", "MITECO embalses semanal", "ámbito (se asigna a la provincia)", "mensual"),
    Campo("estres_hidrico_wri_0_1", "Estrés hídrico de referencia (WRI Aqueduct 4.0, indicador bws, escala 0-5 reescalada a 0-1) de la comunidad autónoma", "0-1", "WRI Aqueduct 4.0", "comunidad autónoma", "estática"),
    Campo("cpd_existentes", "Centros de datos existentes en la provincia (PeeringDB); etiqueta positiva", "nº", "PeeringDB", "provincia", "estática"),
)
_DESCRIPCION: dict[str, Campo] = {campo.nombre: campo for campo in DICCIONARIO}
COLUMNAS_TIEMPO_REAL: tuple[str, ...] = (
    "temperatura_actual_c", "humedad_relativa_actual_pct", "viento_actual_kmh", "precipitacion_actual_mm",
    "momento_observacion", "temp_prevision_7d_media_c", "temp_prevision_7d_max_c", "precipitacion_prevision_7d_mm",
    "demanda_tiempo_real_mw", "precio_spot_actual_eur_mwh", "precio_spot_manana_medio_eur_mwh",
)
UMBRAL_CALOR_EXTREMO_C: float = 35.0  # días >= 35 °C (dias_mas_35c)
AMBITO_POR_CODIGO: dict[str, str | None] = AMBITO_POR_PROVINCIA


def leer_tablas(carpeta: Path = CARPETA_TABLAS) -> dict[str, pd.DataFrame]:
    """Lee las tablas guardadas por actualizar (data/curated/tablas/<nombre>.csv)."""
    tablas: dict[str, pd.DataFrame] = {}
    for ruta in carpeta.glob("*.csv"):
        tablas[ruta.stem] = pd.read_csv(ruta, dtype={"codigo_provincia": str, "codigo_ccaa": str})
    return tablas


def _mes(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie).dt.to_period("M").dt.to_timestamp()


def _clima_mensual(clima: pd.DataFrame) -> pd.DataFrame:
    """Medias y acumulados mensuales por provincia desde la tabla diaria (NASA POWER).

    Los acumulados (precipitación, evapotranspiración) quedan NaN si el mes no está completo:
    sumar un mes parcial daría un valor falso bajo. Las medias sí se calculan con los días disponibles.
    """
    if clima.empty:
        return pd.DataFrame(columns=list(CLAVES))
    datos = clima.copy()
    datos["mes"] = _mes(datos["fecha"])
    datos["dia_calor_extremo"] = (datos["tmax_c"] >= UMBRAL_CALOR_EXTREMO_C).astype(float).where(datos["tmax_c"].notna())
    agregado = datos.groupby(["codigo_provincia", "mes"]).agg(
        tmedia_mes_c=("tmedia_c", "mean"),
        tmax_media_c=("tmax_c", "mean"),
        tmin_media_c=("tmin_c", "mean"),
        precipitacion_mes_mm=("precipitacion_mm", "sum"),
        humedad_relativa_media_pct=("humedad_relativa_media_pct", "mean"),
        viento_medio_kmh=("viento_medio_kmh", "mean"),
        radiacion_solar_media_kwh_m2_dia=("radiacion_solar_kwh_m2_dia", "mean"),
        et0_hargreaves_mes_mm=("et0_hargreaves_mm", "sum"),
        dias_con_clima=("tmedia_c", "count"),
        dias_mas_35c=("dia_calor_extremo", "sum"),
    ).reset_index()
    completo = agregado["dias_con_clima"] == agregado["mes"].dt.days_in_month
    for columna in ("precipitacion_mes_mm", "et0_hargreaves_mes_mm"):
        agregado[columna] = agregado[columna].where(completo)
    agregado["dias_mas_35c"] = agregado["dias_mas_35c"].where(agregado["dias_con_clima"] > 0)
    return agregado


def _precios_mensuales(precios: pd.DataFrame) -> pd.DataFrame:
    if precios.empty:
        return pd.DataFrame(columns=["mes"])
    datos = precios.copy()
    datos["mes"] = _mes(datos["fecha"])
    return datos.groupby("mes").agg(
        precio_spot_medio_mes_eur_mwh=("precio_spot_eur_mwh", "mean"),
        precio_pvpc_medio_mes_eur_mwh=("precio_pvpc_eur_mwh", "mean"),
    ).reset_index()


def _fusionar(base: pd.DataFrame, tabla: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    if tabla is None or tabla.empty:
        return base
    return base.merge(tabla, on=claves, how="left")


def construir_panel(tablas: dict[str, pd.DataFrame], hasta: pd.Timestamp | None = None) -> pd.DataFrame:
    """Panel provincia x mes desde ANIO_INICIO-01 hasta el último mes con algún dato.

    Args:
        tablas: diccionario nombre -> tabla (claves: provincias, clima_diario, free_cooling, ccaa_demanda,
            ccaa_generacion, co2, precios_diarios, poblacion, renta, paro, conectividad, capacidad_ccaa,
            subestaciones, sismos, natura, conectividad).
        hasta: último mes a incluir (por defecto, el último mes con datos en clima o energía).
    """
    provincias = tablas["provincias"]
    fin = hasta
    if fin is None:
        candidatos = [pd.Timestamp(dt.date.today()).to_period("M").to_timestamp()]
        for nombre in ("clima_diario", "ccaa_demanda", "paro"):
            if nombre in tablas and not tablas[nombre].empty:
                col = "fecha" if "fecha" in tablas[nombre] else "mes"
                candidatos.append(_mes(tablas[nombre][col]).max())
        fin = min(candidatos)
    meses = pd.date_range(pd.Timestamp(f"{ANIO_INICIO}-01-01"), fin, freq="MS")
    base = pd.MultiIndex.from_product([list(CODIGOS), meses], names=list(CLAVES)).to_frame(index=False)
    base = base.merge(provincias[["codigo_provincia", "provincia", "codigo_ccaa", "ccaa"]], on="codigo_provincia", how="left")
    base["anio"] = base["mes"].dt.year
    base["ambito_hidrografico"] = base["codigo_provincia"].map(AMBITO_POR_CODIGO)

    base = _fusionar(base, _clima_mensual(tablas.get("clima_diario", pd.DataFrame())), list(CLAVES))
    if "free_cooling" in tablas and not tablas["free_cooling"].empty:
        frio = tablas["free_cooling"].assign(mes=lambda d: _mes(d["mes"]))
        frio = frio[["codigo_provincia", "mes", "horas_free_cooling", "pct_horas_free_cooling"]]
        base = base.merge(frio, on=list(CLAVES), how="left")
    if "precipitacion_mes_mm" in base and "et0_hargreaves_mes_mm" in base:
        base["balance_hidrico_mes_mm"] = agua.balance_hidrico_mm(base["precipitacion_mes_mm"], base["et0_hargreaves_mes_mm"])
        sequia = agua.indice_sequia_12m(base[["mes", "codigo_provincia", "precipitacion_mes_mm"]])
        base = base.merge(sequia, on=list(CLAVES), how="left")

    if "reservas_ambito_mensual" in tablas and not tablas["reservas_ambito_mensual"].empty:
        reservas = tablas["reservas_ambito_mensual"].assign(mes=lambda d: _mes(d["mes"]))
        reservas = reservas.rename(columns={
            "ambito": "ambito_hidrografico",
            "reserva_pct_media_mes": "reserva_hidrica_pct",
            "volumen_hm3_media_mes": "reserva_hidrica_hm3",
            "capacidad_hm3_media_mes": "capacidad_embalses_ambito_hm3",
            "semanas_con_dato": "semanas_reserva_mes",
        })[["ambito_hidrografico", "mes", "reserva_hidrica_pct", "reserva_hidrica_hm3",
            "capacidad_embalses_ambito_hm3", "semanas_reserva_mes"]]
        base = base.merge(reservas, on=["ambito_hidrografico", "mes"], how="left")
    if "estres_hidrico_wri" in tablas and not tablas["estres_hidrico_wri"].empty:
        base = base.merge(tablas["estres_hidrico_wri"][["codigo_provincia", "estres_hidrico_wri_0_1"]],
                          on="codigo_provincia", how="left")

    if "ccaa_demanda" in tablas and not tablas["ccaa_demanda"].empty:
        demanda = tablas["ccaa_demanda"].assign(mes=lambda d: _mes(d["fecha"]))
        demanda = demanda.rename(columns={"demanda_mwh": "demanda_ccaa_mwh"})[["codigo_ccaa", "mes", "demanda_ccaa_mwh"]]
        base = base.merge(demanda, on=["codigo_ccaa", "mes"], how="left")
    if "ccaa_generacion" in tablas and not tablas["ccaa_generacion"].empty:
        gen = tablas["ccaa_generacion"].assign(mes=lambda d: _mes(d["fecha"]))
        gen = gen.rename(columns={
            "generacion_total_mwh": "generacion_total_ccaa_mwh",
            "generacion_renovable_mwh": "generacion_renovable_ccaa_mwh",
            "pct_renovable": "pct_renovable_ccaa",
        })[["codigo_ccaa", "mes", "generacion_total_ccaa_mwh", "generacion_renovable_ccaa_mwh", "pct_renovable_ccaa"]]
        base = base.merge(gen, on=["codigo_ccaa", "mes"], how="left")
    if "co2" in tablas and not tablas["co2"].empty:
        co2 = tablas["co2"].assign(mes=lambda d: _mes(d["fecha"]))
        co2 = co2.rename(columns={"emisiones_co2_tco2eq": "emisiones_co2_nacional_tco2eq"})[["mes", "emisiones_co2_nacional_tco2eq"]]
        base = base.merge(co2, on="mes", how="left")
    base = _fusionar(base, _precios_mensuales(tablas.get("precios_diarios", pd.DataFrame())), ["mes"])

    if "poblacion" in tablas and not tablas["poblacion"].empty:
        base = base.merge(tablas["poblacion"][["codigo_provincia", "anio", "poblacion"]], on=["codigo_provincia", "anio"], how="left")
    if "renta" in tablas and not tablas["renta"].empty:
        base = base.merge(tablas["renta"], on=["codigo_provincia", "anio"], how="left")
    if "paro" in tablas and not tablas["paro"].empty:
        paro = tablas["paro"].assign(mes=lambda d: _mes(d["mes"]))[["codigo_provincia", "mes", "paro_registrado"]]
        base = base.merge(paro, on=["codigo_provincia", "mes"], how="left")
        base["paro_por_1000_hab"] = (1000 * base["paro_registrado"] / base["poblacion"]).round(2)

    if "conectividad" in tablas and not tablas["conectividad"].empty:
        base = base.merge(tablas["conectividad"], on="codigo_provincia", how="left")
    if "subestaciones" in tablas and not tablas["subestaciones"].empty:
        base = base.merge(tablas["subestaciones"], on="codigo_provincia", how="left")
    if "natura" in tablas and not tablas["natura"].empty:
        base = base.merge(tablas["natura"], on="codigo_provincia", how="left")
    if "capacidad_ccaa" in tablas and not tablas["capacidad_ccaa"].empty:
        capacidad = tablas["capacidad_ccaa"].rename(columns={"nudos": "nudos_acceso_ccaa"})
        base = base.merge(capacidad[["codigo_ccaa", "nudos_acceso_ccaa", "capacidad_demanda_rdt_disponible_mw"]], on="codigo_ccaa", how="left")
    if "sismos" in tablas and not tablas["sismos"].empty:
        sismos = tablas["sismos"].rename(columns={"anio": "anio"})
        base = base.merge(sismos, on=["codigo_provincia", "anio"], how="left")
        # Dentro del rango descargado, la ausencia de eventos significa cero eventos (no un dato faltante)
        anios_cubiertos = set(range(int(sismos["anio"].min()), int(sismos["anio"].max()) + 1))
        dentro = base["anio"].isin(anios_cubiertos)
        for columna in ("n_terremotos", "n_terremotos_m3_plus"):
            base.loc[dentro & base[columna].isna(), columna] = 0

    base = base.drop(columns=["anio"])
    orden = ["codigo_provincia", "mes", "provincia", "ccaa", "codigo_ccaa"]
    resto = [c for c in base.columns if c not in orden]
    return base[orden + resto].sort_values(["codigo_provincia", "mes"]).reset_index(drop=True)


def provincias_actual(panel: pd.DataFrame, tablas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Una fila por provincia con el último valor disponible de cada variable y los campos de tiempo real."""
    provincias = tablas["provincias"][["codigo_provincia", "provincia", "codigo_ccaa", "ccaa", "lat_punto", "lon_punto"]]
    variables = [c for c in panel.columns if c not in ("codigo_provincia", "mes", "provincia", "ccaa", "codigo_ccaa")]
    ultimos = panel.sort_values("mes").groupby("codigo_provincia")[variables].last().reset_index()
    if "paro_registrado" in panel:
        ultimo_mes = panel.dropna(subset=["paro_registrado"]).groupby("codigo_provincia")["mes"].max()
    else:
        ultimo_mes = pd.Series(dtype="datetime64[ns]")
    resultado = provincias.merge(ultimos, on="codigo_provincia", how="left")
    resultado["mes_referencia_panel"] = resultado["codigo_provincia"].map(panel.groupby("codigo_provincia")["mes"].max().to_dict())
    resultado["mes_ultimo_paro"] = resultado["codigo_provincia"].map(ultimo_mes.to_dict())

    tiempo_real = tablas.get("tiempo_real_provincia", pd.DataFrame())
    if not tiempo_real.empty:
        resultado = resultado.merge(tiempo_real, on="codigo_provincia", how="left")
    energia = tablas.get("energia_tiempo_real", pd.DataFrame())
    if not energia.empty:
        fila = energia.iloc[0]
        resultado["demanda_tiempo_real_mw"] = fila.get("demanda_tiempo_real_mw")
        resultado["precio_spot_actual_eur_mwh"] = fila.get("precio_spot_actual_eur_mwh")
        resultado["precio_spot_manana_medio_eur_mwh"] = fila.get("precio_spot_manana_medio_eur_mwh")
    for columna in COLUMNAS_TIEMPO_REAL:
        if columna not in resultado:
            resultado[columna] = pd.NA
    if "n_centros_datos" in resultado:
        resultado["cpd_existentes"] = resultado["n_centros_datos"]
    return resultado


def diccionario_para(columnas: list[str]) -> pd.DataFrame:
    """Diccionario de datos (CSV) de las columnas indicadas."""
    filas = []
    for columna in columnas:
        campo = _DESCRIPCION.get(columna, Campo(columna, "Columna sin descripción específica", "-", "-", "-", "-"))
        filas.append(
            {"columna": campo.nombre, "descripcion": campo.descripcion, "unidad": campo.unidad,
             "fuente": campo.fuente, "nivel": campo.nivel, "frecuencia": campo.frecuencia}
        )
    return pd.DataFrame(filas)


def escribir_salidas(panel: pd.DataFrame, actual: pd.DataFrame, carpeta: Path = CARPETA_CURADO) -> dict[str, Path]:
    """Guarda panel y provincias_actual (CSV y Parquet) y sus diccionarios de datos."""
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = {
        "panel_csv": carpeta / "panel_provincia_mes.csv",
        "panel_parquet": carpeta / "panel_provincia_mes.parquet",
        "actual_csv": carpeta / "provincias_actual.csv",
        "actual_parquet": carpeta / "provincias_actual.parquet",
        "dicc_panel": carpeta / "diccionario_panel_provincia_mes.csv",
        "dicc_actual": carpeta / "diccionario_provincias_actual.csv",
    }
    panel.to_csv(rutas["panel_csv"], index=False, encoding="utf-8")
    panel.to_parquet(rutas["panel_parquet"], index=False)
    actual.to_csv(rutas["actual_csv"], index=False, encoding="utf-8")
    actual.to_parquet(rutas["actual_parquet"], index=False)
    diccionario_para(list(panel.columns)).to_csv(rutas["dicc_panel"], index=False, encoding="utf-8")
    diccionario_para(list(actual.columns)).to_csv(rutas["dicc_actual"], index=False, encoding="utf-8")
    return rutas
