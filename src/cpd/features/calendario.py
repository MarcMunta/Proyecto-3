"""Días hábiles de cada mes en España (añadido el 18/11/2026).

Las sociedades se inscriben y la industria trabaja en días hábiles: un mes con Semana Santa o con más fines de semana
tiene menos actividad aunque nada haya cambiado. Contar los días hábiles permite prever la actividad **por día
hábil** (más estable) y volver a multiplicar por los días hábiles del mes que se prevé, que se conocen de antemano
(no es fuga de información: el calendario es público y fijo).

Días hábiles = lunes a viernes menos los festivos **nacionales** que caen entre semana: 1 y 6 de enero, Viernes Santo,
1 de mayo, 15 de agosto, 12 de octubre, 1 de noviembre y 6, 8 y 25 de diciembre. Los festivos autonómicos y locales
cambian cada año y no se incluyen (aproximación; recomendación, no viene de clase).
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np
import pandas as pd
from dateutil.easter import easter

FESTIVOS_FIJOS: tuple[tuple[int, int], ...] = ((1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25))


@lru_cache(maxsize=None)
def festivos_nacionales(anio: int) -> frozenset[dt.date]:
    """Festivos nacionales de un año (fijos más Viernes Santo)."""
    viernes_santo = easter(anio) - dt.timedelta(days=2)
    return frozenset({dt.date(anio, m, d) for m, d in FESTIVOS_FIJOS} | {viernes_santo})


@lru_cache(maxsize=None)
def _dias_habiles(anio: int, mes: int) -> int:
    inicio = pd.Timestamp(anio, mes, 1)
    dias = pd.date_range(inicio, inicio + pd.offsets.MonthEnd(0), freq="D")
    festivos = festivos_nacionales(anio)
    return int(sum(1 for d in dias if d.weekday() < 5 and d.date() not in festivos))


def dias_habiles(mes: pd.Timestamp) -> int:
    """Días hábiles (lunes-viernes no festivos nacionales) del mes que contiene `mes`."""
    t = pd.Timestamp(mes)
    return _dias_habiles(t.year, t.month)


def dias_habiles_serie(meses: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Días hábiles de cada mes de una serie o índice de fechas."""
    return np.array([dias_habiles(m) for m in pd.to_datetime(pd.Series(meses))], dtype=float)
