"""Contrato de calidad para publicar el panel provincial y la ficha territorial."""
from __future__ import annotations

import datetime as dt
import math

import numpy as np
import pandas as pd

CODIGOS_PROVINCIA = frozenset(f"{i:02d}" for i in range(1, 53))
COBERTURA_MINIMA = {
    "tmedia_mes_c": 0.9,
    "precio_spot_medio_mes_eur_mwh": 0.9,
    "demanda_ccaa_mwh": 0.75,
}
CODIGOS_CCAA = frozenset(f"{i:02d}" for i in range(1, 20))
MESES_MAXIMO_RETRASO = 2


class DatosNoPublicables(ValueError):
    """La versión candidata no cumple el contrato de datos."""


def validar(panel: pd.DataFrame, actual: pd.DataFrame, *,
            hoy: dt.date | None = None, permitir_historico: bool = False,
            permitir_demanda_incompleta: bool = False) -> dict:
    """Comprueba claves, meses cerrados y cobertura de los últimos 12 meses."""
    for tabla, claves in ((panel, ["codigo_provincia", "mes"]), (actual, ["codigo_provincia"])):
        if not set(claves).issubset(tabla.columns):
            raise DatosNoPublicables(f"Faltan columnas de la clave {claves}")
        if tabla[claves].isna().any().any() or tabla.duplicated(claves).any():
            raise DatosNoPublicables(f"Clave nula o duplicada {claves}")
        if set(tabla["codigo_provincia"]) != CODIGOS_PROVINCIA:
            raise DatosNoPublicables("La cobertura geográfica debe incluir los 52 códigos INE de provincia")

    mes = pd.to_datetime(panel["mes"], errors="coerce")
    if mes.isna().any() or not mes.eq(mes.dt.to_period("M").dt.to_timestamp()).all():
        raise DatosNoPublicables("El panel debe usar fechas de inicio de mes")
    if not mes.value_counts().eq(len(CODIGOS_PROVINCIA)).all():
        raise DatosNoPublicables("Cada mes del panel debe tener las 52 provincias")
    ultimo_cerrado = pd.Period(hoy or dt.date.today(), freq="M") - 1
    referencia = mes.max().to_period("M")
    if referencia > ultimo_cerrado:
        raise DatosNoPublicables("El panel contiene un mes sin cerrar")
    if not permitir_historico and ultimo_cerrado.ordinal - referencia.ordinal > MESES_MAXIMO_RETRASO:
        raise DatosNoPublicables(f"El panel está desactualizado: último mes {referencia}")
    ventana = panel.loc[mes >= (referencia - 11).start_time].assign(mes=mes)
    if len(ventana) != 12 * len(CODIGOS_PROVINCIA):
        raise DatosNoPublicables("El panel debe cubrir los últimos 12 meses completos y consecutivos")

    if "codigo_ccaa" not in ventana or ventana["codigo_ccaa"].isna().any():
        raise DatosNoPublicables("Faltan códigos de CCAA en el panel")
    por_mes = ventana.groupby("mes")["codigo_ccaa"].agg(set)
    if not por_mes.map(lambda codigos: codigos == CODIGOS_CCAA).all():
        raise DatosNoPublicables("Cada mes debe incluir las 19 CCAA y ciudades autónomas")
    if ventana.groupby("codigo_provincia")["codigo_ccaa"].nunique().ne(1).any():
        raise DatosNoPublicables("La CCAA de una provincia cambia dentro del panel")

    cobertura = {}
    reciente = {}
    avisos = []
    claves_por_indicador = {
        "tmedia_mes_c": ["mes", "codigo_provincia"],
        "precio_spot_medio_mes_eur_mwh": ["mes"],
        "demanda_ccaa_mwh": ["mes", "codigo_ccaa"],
    }
    for columna, minimo in COBERTURA_MINIMA.items():
        claves = claves_por_indicador[columna]
        if not set([columna, *claves]).issubset(ventana.columns):
            raise DatosNoPublicables(f"Falta el indicador crítico {columna} o su clave")
        grupo = ventana.groupby(claves, dropna=False)[columna]
        if grupo.nunique().gt(1).any():
            raise DatosNoPublicables(f"Valores incompatibles dentro de la granularidad de {columna}")
        valores = pd.to_numeric(grupo.first(), errors="coerce")
        validos = np.isfinite(valores).fillna(False)
        es_demanda = columna == "demanda_ccaa_mwh"
        if es_demanda:
            validos &= valores.gt(0)
        ratio = float(validos.mean())
        ultimo = float(validos[validos.index.get_level_values("mes") == mes.max()].mean())
        cobertura[columna] = round(ratio, 4)
        reciente[columna] = round(ultimo, 4)
        if not math.isfinite(ratio) or not math.isfinite(ultimo) or min(ratio, ultimo) < minimo:
            mensaje = (f"Cobertura insuficiente en {columna}: {ratio:.1%} en 12 meses, "
                       f"{ultimo:.1%} en el último mes (mínimo {minimo:.0%})")
            if es_demanda and permitir_demanda_incompleta and ratio > 0:
                avisos.append(mensaje)
            else:
                raise DatosNoPublicables(mensaje)
    if "mes_referencia_panel" not in actual or not pd.to_datetime(
        actual["mes_referencia_panel"], errors="coerce",
    ).eq(mes.max()).all():
        raise DatosNoPublicables("La ficha provincial no corresponde al último mes del panel")

    return {
        "fecha_panel": str(referencia),
        "filas_panel": len(panel),
        "cobertura_12m": cobertura,
        "cobertura_ultimo_mes": reciente,
        "avisos": avisos,
    }

