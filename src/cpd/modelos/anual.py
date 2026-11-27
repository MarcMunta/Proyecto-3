"""Previsión a 1 año (12 meses, mes a mes) con el menor error posible: demanda por comunidad, precio de la luz,
reservas de agua por ámbito y temperatura media por provincia.

Protocolo común (fases 7 y 8; R-6):
- **Orígenes de validación:** 24 orígenes mensuales consecutivos (dos años). En cada origen `r` cada modelo se
  entrena solo con datos hasta `r` y prevé los 12 meses siguientes. Sus meses objetivo terminan antes del test.
- **Test:** un único origen, 12 meses antes del último dato; se mira una vez.
- **Candidatos:** baselines, modelos estadísticos (ETS de Holt-Winters amortiguado), ML (Ridge, gradient boosting)
  y la **combinación** (media) de los 3 mejores en validación. Combinar modelos suele reducir el error porque sus
  errores no coinciden (recomendación, no viene de clase).
- **Elección:** la combinación, salvo que un modelo individual tenga más de un 5 % menos de error medio en
  validación (MAPE para la demanda, MAE en €/MWh para el precio).
- **Intervalo:** cuantiles 10-90 % del error relativo del modelo elegido en validación, por horizonte.

Todas las comparaciones usan exactamente las mismas filas (serie, mes, origen) para todos los modelos.
"""

from __future__ import annotations

from functools import lru_cache

import datetime as dt
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cpd.features import demanda as fdem
from cpd.features import precio as fpre
from cpd.modelos.metricas import metricas_regresion

SEMILLA: int = 42
HORIZONTE: int = 12
MIEMBROS_COMBINACION: int = 3
# Un modelo solo sustituye a la combinación si mejora su error de validación en más de un 5 %: con pocos orígenes
# (y muy correlacionados) una diferencia menor puede ser casualidad, y la combinación es más robusta.
MARGEN_COMBINACION: float = 0.05

# Función de un candidato: origen r → DataFrame con serie, mes, horizonte_meses, prevision (solo datos ≤ r).
Candidato = Callable[[pd.Timestamp], pd.DataFrame]


@dataclass(frozen=True)
class Origenes:
    """Orígenes de validación (varios) y de test (uno)."""

    validacion: tuple[pd.Timestamp, ...]
    test: pd.Timestamp
    fin: pd.Timestamp

    def como_texto(self) -> dict[str, str]:
        """Orígenes y meses objetivo en AAAA-MM."""
        mes = lambda t: pd.Timestamp(t).strftime("%Y-%m")  # noqa: E731
        return {
            "origenes_validacion": f"{mes(self.validacion[0])} a {mes(self.validacion[-1])} ({len(self.validacion)} orígenes)",
            "meses_validacion": f"{mes(self.validacion[0] + pd.DateOffset(months=1))} a {mes(self.validacion[-1] + pd.DateOffset(months=HORIZONTE))}",
            "origen_test": mes(self.test),
            "meses_test": f"{mes(self.test + pd.DateOffset(months=1))} a {mes(self.fin)}",
        }


ORIGENES_VALIDACION: int = 24


def definir_origenes(fin: pd.Timestamp, n_validacion: int = ORIGENES_VALIDACION) -> Origenes:
    """Test = origen `fin − 12`; validación = los `n_validacion` orígenes que terminan en `fin − 24`, de forma que
    ningún mes objetivo de validación cae en el test.

    Se usan 24 orígenes (dos años) y no 12: con 12 orígenes consecutivos la validación solo veía un periodo de
    precios estable y elegía un modelo (gradient boosting) que luego fue el peor en test. Esta decisión se tomó
    después de ver ese primer test, así que el test del precio no es del todo independiente (se dice en el informe).
    """
    test = fin - pd.DateOffset(months=HORIZONTE)
    ultimo = fin - pd.DateOffset(months=2 * HORIZONTE)
    validacion = tuple(ultimo - pd.DateOffset(months=k) for k in range(n_validacion - 1, -1, -1))
    return Origenes(validacion, test, fin)


def _ets(log_serie: pd.Series, pasos: int) -> np.ndarray:
    """Holt-Winters con tendencia amortiguada y estacionalidad aditiva sobre el logaritmo (statsmodels)."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = ExponentialSmoothing(
            log_serie.to_numpy(dtype=float), trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
            initialization_method="estimated",
        ).fit()
    return np.exp(modelo.forecast(pasos))


def _ar_diferencias(log_serie: pd.Series, pasos: int) -> np.ndarray:
    """Modelo sobre **diferencias** (técnica de clase I52, C4 p.7 y 17; añadido el 18/11/2026): AR(1) sobre la
    diferencia estacional del logaritmo, Δ₁₂ log y_t = c + φ · Δ₁₂ log y_(t−1) + ε (SARIMA(1,0,0)(0,1,0)₁₂ con
    constante). La diferencia de 12 meses quita la estacionalidad y la tendencia; se prevé la diferencia y se deshace
    sumándola al mismo mes del año anterior."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = SARIMAX(log_serie.to_numpy(dtype=float), order=(1, 0, 0), seasonal_order=(0, 1, 0, 12), trend="c").fit(disp=False)
    return np.exp(modelo.forecast(pasos))


def _filas_futuras(serie: str, origen: pd.Timestamp) -> pd.DataFrame:
    meses = pd.date_range(origen + pd.DateOffset(months=1), periods=HORIZONTE, freq="MS")
    return pd.DataFrame({"serie": serie, "mes": meses, "horizonte_meses": range(1, HORIZONTE + 1)})


# ---------------------------------------------------------------------------------------------- demanda por CCAA


def candidatos_demanda(serie: pd.DataFrame, con_diferencias: bool = False) -> dict[str, Candidato]:
    """Candidatos para la demanda mensual de cada comunidad (MWh).

    Args:
        serie: salida de `cpd.features.demanda.preparar_serie_modelo` (`codigo_ccaa`, `mes`, `demanda_mwh`).
        con_diferencias: añade el modelo sobre diferencias (`ar_diferencias`, técnica I52). **Probado el 18/11/2026:**
            por sí solo acierta 96,1 % / 95,0 % (como el estacional y el Ridge), pero entra en los 3 mejores por 0,003
            puntos de MAPE, desplaza al Ridge y la combinación empeora un poco en validación (MAPE 3,93 % frente a
            3,90 %); por eso no se usa en el pipeline.
    """
    por_ccaa = {c: g.set_index("mes")["demanda_mwh"].sort_index() for c, g in serie.groupby("codigo_ccaa")}
    tablas = {h: fdem.construir_features_demanda(serie, h, meses_futuros=HORIZONTE) for h in range(1, HORIZONTE + 1)}

    def _hasta(origen: pd.Timestamp) -> dict[str, pd.Series]:
        return {c: s.loc[:origen] for c, s in por_ccaa.items() if len(s.loc[:origen]) >= 36 and s.index.max() >= origen}

    def estacional(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = s.reindex(filas["mes"] - pd.DateOffset(months=12)).to_numpy()
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def estacional_tendencia(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            ultimo, anterior = s.iloc[-12:].sum(), s.iloc[-24:-12].sum()
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = s.reindex(filas["mes"] - pd.DateOffset(months=12)).to_numpy() * (ultimo / anterior)
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def ets(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = _ets(np.log(s.iloc[-96:]), HORIZONTE)  # 8 años como máximo
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def ar_diferencias(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for codigo, s in _hasta(origen).items():
            filas = _filas_futuras(codigo, origen)
            filas["prevision"] = _ar_diferencias(np.log(s.iloc[-96:]), HORIZONTE)  # 8 años como máximo, como la ETS
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def ridge(origen: pd.Timestamp) -> pd.DataFrame:
        partes = []
        for h, tabla in tablas.items():
            columnas = fdem.columnas_features(tabla)
            entrenamiento = tabla[(tabla["mes"] <= origen)].dropna(subset=["objetivo_log_ratio"])
            prever = tabla[tabla["mes_referencia"] == origen]
            if entrenamiento.empty or prever.empty:
                continue
            modelo = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(entrenamiento[columnas], entrenamiento["objetivo_log_ratio"])
            partes.append(
                pd.DataFrame(
                    {
                        "serie": prever["codigo_ccaa"].to_numpy(),
                        "mes": prever["mes"].to_numpy(),
                        "horizonte_meses": h,
                        "prevision": np.exp(modelo.predict(prever[columnas])) * prever["nivel_mwh"].to_numpy(),
                    }
                )
            )
        return pd.concat(partes, ignore_index=True)

    candidatos = {"estacional": estacional, "estacional_tendencia": estacional_tendencia, "ets": ets, "ridge": ridge}
    if con_diferencias:
        candidatos["ar_diferencias"] = ar_diferencias
    return candidatos


def reales_demanda(serie: pd.DataFrame) -> pd.DataFrame:
    """Valores reales para evaluar (sin los meses imputados: nunca se evalúa contra un dato inventado)."""
    datos = serie[~serie["imputado"]] if "imputado" in serie.columns else serie
    return datos.rename(columns={"codigo_ccaa": "serie", "demanda_mwh": "real"})[["serie", "mes", "real"]]


# ------------------------------------------------------------------------------------------------ precio de la luz


def candidatos_precio(mensual: pd.DataFrame) -> dict[str, Candidato]:
    """Candidatos para el precio spot medio mensual (€/MWh). Si `mensual` tiene las columnas de gas
    (`cpd.features.precio.series_gas`), los modelos de ML las usan."""
    precio = mensual["precio_eur_mwh"].dropna()
    tabla = fpre.construir_features_precio(mensual, meses_futuros=HORIZONTE)
    columnas = fpre.columnas_features(tabla)
    columnas_gas = [c for c in columnas if c.startswith("f_gas")]

    def _salida(filas: pd.DataFrame, prevision: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame({"serie": "ES", "mes": filas["mes"].to_numpy(), "horizonte_meses": filas["horizonte_meses"].to_numpy(), "prevision": prevision})

    def _baseline(nombre: str) -> Candidato:
        def prever(origen: pd.Timestamp) -> pd.DataFrame:
            filas = _filas_futuras("ES", origen)
            hasta = precio.loc[:origen]
            if nombre == "media_12m":
                filas["prevision"] = hasta.iloc[-12:].mean()
            elif nombre == "naive":
                filas["prevision"] = hasta.iloc[-1]
            else:  # estacional
                filas["prevision"] = hasta.reindex(filas["mes"] - pd.DateOffset(months=12)).to_numpy()
            return filas

        return prever

    def ets(origen: pd.Timestamp) -> pd.DataFrame:
        filas = _filas_futuras("ES", origen)
        filas["prevision"] = _ets(np.log(precio.loc[:origen]), HORIZONTE)
        return filas

    def _ml(modelo: Any, cols: list[str]) -> Candidato:
        def prever(origen: pd.Timestamp) -> pd.DataFrame:
            entrenamiento = tabla[tabla["mes"] <= origen].dropna(subset=["objetivo_log_ratio"])
            filas = tabla[tabla["mes_origen"] == origen]
            if len(entrenamiento) < 24 or filas.empty:  # sin historia suficiente (p. ej. antes de los futuros de gas)
                return pd.DataFrame(columns=["serie", "mes", "horizonte_meses", "prevision"])
            ajustado = clone(modelo).fit(entrenamiento[cols].to_numpy(dtype=float), entrenamiento["objetivo_log_ratio"].to_numpy(dtype=float))
            return _salida(filas, np.exp(ajustado.predict(filas[cols].to_numpy(dtype=float))) * filas["nivel_eur_mwh"].to_numpy())

        return prever

    candidatos: dict[str, Candidato] = {n: _baseline(n) for n in ("media_12m", "naive", "estacional")}
    candidatos["ets"] = ets
    candidatos["ridge"] = _ml(make_pipeline(StandardScaler(), Ridge(alpha=100.0)), columnas)
    if columnas_gas:
        base = ["f_mes_sin", "f_mes_cos", "f_horizonte", "f_ultimo"]
        candidatos["ridge_gas"] = _ml(make_pipeline(StandardScaler(), Ridge(alpha=10.0)), base + columnas_gas)
        candidatos["gradient_boosting"] = _ml(
            HistGradientBoostingRegressor(learning_rate=0.05, max_depth=2, max_iter=200, min_samples_leaf=30, random_state=SEMILLA), columnas
        )
    return candidatos


def reales_precio(mensual: pd.DataFrame) -> pd.DataFrame:
    """Precio real mensual (€/MWh) en el formato de evaluación."""
    precio = mensual["precio_eur_mwh"].dropna()
    return pd.DataFrame({"serie": "ES", "mes": precio.index, "real": precio.to_numpy()})


# ------------------------------------------------------------------------------------ reservas de agua por ámbito


def series_reservas(reservas: pd.DataFrame, hoy: dt.date | None = None) -> pd.DataFrame:
    """Reserva de los embalses (% de la capacidad) por ámbito hidrográfico y mes completo (sin el mes en curso).

    Args:
        reservas: tabla `reservas_ambito_mensual` (MITECO): `mes`, `ambito`, `reserva_pct_media_mes`.
    """
    datos = reservas.assign(mes=pd.to_datetime(reservas["mes"]).dt.to_period("M").dt.to_timestamp())
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    datos = datos[datos["mes"] < en_curso].dropna(subset=["reserva_pct_media_mes"])
    return datos.rename(columns={"ambito": "serie", "reserva_pct_media_mes": "real"})[["serie", "mes", "real"]].sort_values(["serie", "mes"]).reset_index(drop=True)


def candidatos_reservas(reales: pd.DataFrame) -> dict[str, Candidato]:
    """Candidatos para la reserva mensual de cada ámbito (%):

    - `naive`: la reserva del mes de origen se mantiene.
    - `estacional`: la del mismo mes del año anterior.
    - `climatologia`: la media de ese mes del calendario en los 10 años anteriores al origen.
    - `anomalia_persistente`: climatología + la anomalía del origen multiplicada por φ_h, con φ_h ajustado por
      mínimos cuadrados con los años anteriores al origen (todas las cuencas juntas). Las reservas tienen memoria:
      una sequía no se arregla en un mes.
    - `anomalia_por_cuenca`: lo mismo con un φ_h propio de cada cuenca (últimos 20 años): los embalses grandes
      (Tajo, Guadiana) se recuperan más despacio que los pequeños.
    - `ets`: Holt-Winters con tendencia amortiguada y estacionalidad aditiva sobre el nivel.
    Las previsiones se recortan a [0, 100] %.
    """
    return candidatos_estacionales(reales, limites=(0.0, 100.0), min_meses=120, nombre_propio="anomalia_por_cuenca")


def candidatos_estacionales(
    reales: pd.DataFrame, limites: tuple[float, float] | None, min_meses: int, nombre_propio: str
) -> dict[str, Candidato]:
    """Candidatos para series mensuales muy estacionales (reservas de agua, temperatura): último valor, mismo mes
    del año anterior, climatología, anomalía persistente (con un φ común y con un φ propio de cada serie, que se
    llama `nombre_propio`) y ETS. Ver `candidatos_reservas` para el detalle de cada uno.

    Args:
        reales: `serie`, `mes`, `real`.
        limites: rango físico en el que se recortan las previsiones (p. ej. 0-100 %), o None para no recortar.
        min_meses: meses de historia que necesita una serie en el origen para prever (la climatología usa hasta 10
            años; con menos historia, todos los años disponibles).
        nombre_propio: nombre del candidato con φ propio de cada serie.
    """
    bajo, alto = limites if limites is not None else (-np.inf, np.inf)
    por_serie = {s: g.set_index("mes")["real"].sort_index() for s, g in reales.groupby("serie")}

    def _hasta(origen: pd.Timestamp) -> dict[str, pd.Series]:
        return {s: v.loc[:origen] for s, v in por_serie.items() if len(v.loc[:origen]) >= min_meses and v.index.max() >= origen}

    def _clim(s: pd.Series, meses: pd.Series) -> np.ndarray:
        ultimos = s.iloc[-120:]
        por_mes = ultimos.groupby(ultimos.index.month).mean()
        return por_mes.reindex(meses.dt.month).to_numpy()

    def _aplicar(origen: pd.Timestamp, regla: Callable[[pd.Series, pd.DataFrame], np.ndarray]) -> pd.DataFrame:
        partes = []
        for serie, s in _hasta(origen).items():
            filas = _filas_futuras(serie, origen)
            filas["prevision"] = np.clip(regla(s, filas), bajo, alto)
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def naive(origen: pd.Timestamp) -> pd.DataFrame:
        return _aplicar(origen, lambda s, f: np.repeat(s.iloc[-1], len(f)))

    def estacional(origen: pd.Timestamp) -> pd.DataFrame:
        return _aplicar(origen, lambda s, f: s.reindex(f["mes"] - pd.DateOffset(months=12)).to_numpy())

    def climatologia(origen: pd.Timestamp) -> pd.DataFrame:
        return _aplicar(origen, lambda s, f: _clim(s, f["mes"]))

    def _phi(anomalias: list[pd.Series]) -> dict[int, float]:
        """φ_h por mínimos cuadrados: anomalía(t + h) ≈ φ_h · anomalía(t), con los pares disponibles."""
        phi = {}
        for h in range(1, HORIZONTE + 1):
            x = np.concatenate([a.to_numpy()[:-h] for a in anomalias if len(a) > h] or [np.array([])])
            y = np.concatenate([a.to_numpy()[h:] for a in anomalias if len(a) > h] or [np.array([])])
            phi[h] = float(np.dot(x, y) / np.dot(x, x)) if len(x) and np.dot(x, x) > 0 else 0.0  # serie plana: sin memoria
        return phi

    def _anomalia(origen: pd.Timestamp, por_cuenca: bool) -> pd.DataFrame:
        # Anomalías hasta el origen (frente a la media del mismo mes de los 10 años anteriores).
        anomalias = {}
        for serie, s in _hasta(origen).items():
            clim = s.groupby(s.index.month).transform(lambda v: v.rolling(10, min_periods=5).mean().shift(1))
            anomalias[serie] = (s - clim).dropna()
        comun = _phi(list(anomalias.values()))
        propio = {serie: _phi([a.iloc[-240:]]) for serie, a in anomalias.items()} if por_cuenca else {}

        partes = []
        for serie, s in _hasta(origen).items():
            phi = propio.get(serie, comun)
            filas = _filas_futuras(serie, origen)
            ultimos = s.iloc[-121:-1]
            anomalia = s.iloc[-1] - ultimos[ultimos.index.month == s.index[-1].month].mean()
            filas["prevision"] = np.clip(_clim(s, filas["mes"]) + anomalia * np.array([phi[h] for h in filas["horizonte_meses"]]), bajo, alto)
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    def anomalia_persistente(origen: pd.Timestamp) -> pd.DataFrame:
        return _anomalia(origen, por_cuenca=False)

    def anomalia_propia(origen: pd.Timestamp) -> pd.DataFrame:
        return _anomalia(origen, por_cuenca=True)

    def ets(origen: pd.Timestamp) -> pd.DataFrame:
        def regla(s: pd.Series, f: pd.DataFrame) -> np.ndarray:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ajuste = ExponentialSmoothing(
                    s.iloc[-180:].to_numpy(dtype=float), trend="add", damped_trend=True, seasonal="add", seasonal_periods=12, initialization_method="estimated"
                ).fit()
            return ajuste.forecast(len(f))

        return _aplicar(origen, regla)

    return {
        "naive": naive,
        "estacional": estacional,
        "climatologia": climatologia,
        "anomalia_persistente": anomalia_persistente,
        nombre_propio: anomalia_propia,
        "ets": ets,
    }


# --------------------------------------------------------------------------- temperatura media por provincia


def series_temperatura(clima_diario: pd.DataFrame, hoy: dt.date | None = None) -> pd.DataFrame:
    """Temperatura media mensual (°C) de cada provincia: media de las diarias, solo meses completos y sin el mes
    en curso.

    Args:
        clima_diario: tabla `clima_diario` (NASA POWER): `fecha`, `codigo_provincia`, `tmedia_c` (°C).
        hoy: fecha de referencia para el mes en curso (por defecto, hoy).

    Returns:
        `serie` (código INE de provincia, 2 cifras), `mes`, `real` (°C).
    """
    datos = clima_diario.assign(
        mes=pd.to_datetime(clima_diario["fecha"]).dt.to_period("M").dt.to_timestamp(),
        serie=clima_diario["codigo_provincia"].astype(str).str.zfill(2),
    ).dropna(subset=["tmedia_c"])
    resumen = datos.groupby(["serie", "mes"])["tmedia_c"].agg(["mean", "count"]).reset_index()
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    completos = (resumen["count"] >= resumen["mes"].dt.days_in_month) & (resumen["mes"] < en_curso)
    return resumen[completos].rename(columns={"mean": "real"})[["serie", "mes", "real"]].sort_values(["serie", "mes"]).reset_index(drop=True)


def series_renovables(generacion: pd.DataFrame, hoy: dt.date | None = None, columna: str = "pct_renovable") -> pd.DataFrame:
    """Porcentaje de generación renovable (%) de cada comunidad autónoma por mes, sin el mes en curso.

    Deja fuera las comunidades sin ninguna generación renovable en todo el periodo (Ceuta): su serie es siempre 0 y
    no hay nada que prever.

    Args:
        generacion: tabla `ccaa_generacion` (REData): `codigo_ccaa`, `fecha` (mes), `pct_renovable` (%).
        hoy: fecha de referencia para el mes en curso (por defecto, hoy).
        columna: columna que se prevé (`pct_renovable` en %, o `generacion_renovable_mwh` en MWh).

    Returns:
        `serie` (código INE de comunidad, 2 cifras), `mes`, `real` (unidad de `columna`).
    """
    datos = generacion.assign(
        mes=pd.to_datetime(generacion["fecha"]).dt.to_period("M").dt.to_timestamp(),
        serie=generacion["codigo_ccaa"].astype(str).str.zfill(2),
    ).dropna(subset=[columna])
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    datos = datos[datos["mes"] < en_curso]
    con_renovables = datos.groupby("serie")[columna].transform("max") > 0
    datos = datos[con_renovables].rename(columns={columna: "real"})
    return datos[["serie", "mes", "real"]].sort_values(["serie", "mes"]).reset_index(drop=True)


def series_generacion_renovable(generacion: pd.DataFrame, hoy: dt.date | None = None) -> pd.DataFrame:
    """Generación renovable (MWh) de cada comunidad autónoma por mes, sin el mes en curso ni las comunidades sin
    generación renovable en todo el periodo (Ceuta).

    Args:
        generacion: tabla `ccaa_generacion` (REData): `codigo_ccaa`, `fecha` (mes), `generacion_renovable_mwh`.
        hoy: fecha de referencia para el mes en curso (por defecto, hoy).

    Returns:
        `serie` (código INE de comunidad, 2 cifras), `mes`, `real` (MWh).
    """
    return series_renovables(generacion, hoy, columna="generacion_renovable_mwh")


def candidatos_por_dia_habil(fabrica: Callable[[pd.DataFrame], dict[str, Candidato]], reales: pd.DataFrame) -> dict[str, Candidato]:
    """Versión «por día hábil» de unos candidatos (añadido el 18/11/2026): se prevé el valor de cada mes dividido entre
    sus días hábiles (`cpd.features.calendario`) y la previsión se vuelve a multiplicar por los días hábiles del mes
    previsto, que se conocen de antemano. Quita el ruido de calendario (Semana Santa, meses con más fines de semana).

    Args:
        fabrica: función que crea los candidatos a partir de unas series reales (`serie`, `mes`, `real`).
        reales: series reales en su unidad (no por día).

    Returns:
        Los mismos candidatos con el sufijo «_dias_habiles».
    """
    from cpd.features.calendario import dias_habiles_serie

    por_dia = reales.assign(real=reales["real"] / dias_habiles_serie(reales["mes"]))
    return escalar_por_dias(fabrica(por_dia), dias_habiles_serie, "_dias_habiles")


def escalar_por_dias(base: dict[str, Candidato], dias: Callable[[pd.Series], np.ndarray], sufijo: str) -> dict[str, Candidato]:
    """Multiplica la previsión de cada candidato (hecha sobre valores por día) por los días del mes previsto."""

    def envolver(prever: Candidato) -> Candidato:
        def prever_dias(origen: pd.Timestamp) -> pd.DataFrame:
            filas = prever(origen)
            if filas is None or filas.empty:
                return filas
            return filas.assign(prevision=filas["prevision"].to_numpy(dtype=float) * dias(filas["mes"]))

        return prever_dias

    return {f"{nombre}{sufijo}": envolver(c) for nombre, c in base.items()}


def candidatos_demanda_por_dia(serie: pd.DataFrame, habiles: bool) -> dict[str, Candidato]:
    """Candidatos de la demanda prevista por día (hábil o natural) y vuelta a multiplicar por los días del mes previsto.
    Los días naturales quitan el efecto de febrero bisiesto; los hábiles, el de Semana Santa y los fines de semana.

    **Probado y descartado (18/11/2026):** en validación, por día hábil empeora (la electricidad se consume todos los
    días: ETS 3,76 % → 5,31 % de MAPE) y por día natural no mejora (3,78 %). No se usa en el pipeline; se deja para
    poder repetir la prueba."""
    from cpd.features.calendario import dias_habiles_serie

    def naturales(meses: pd.Series) -> np.ndarray:
        return pd.to_datetime(pd.Series(meses)).dt.days_in_month.to_numpy(dtype=float)

    dias = dias_habiles_serie if habiles else naturales
    por_dia = serie.assign(demanda_mwh=serie["demanda_mwh"] / dias(serie["mes"]))
    return escalar_por_dias(candidatos_demanda(por_dia), dias, "_dias_habiles" if habiles else "_dias_naturales")


def candidatos_renovables(reales: pd.DataFrame, maximo: float = 100.0, con_log: bool = False) -> dict[str, Candidato]:
    """Candidatos para el % renovable mensual de cada comunidad (o, con `maximo=np.inf`, para la generación renovable
    en MWh): los de `candidatos_estacionales` (con un φ propio de cada comunidad) y dos variantes de ETS con los
    últimos 5 años, con tendencia amortiguada y sin tendencia: con tanta potencia solar nueva en 2022-2025, la
    historia larga frena la tendencia (se vio en la validación, después de la primera prueba). Con `con_log` se añade
    una ETS de 5 años sobre el logaritmo (crecimiento proporcional, útil en MWh). Las previsiones se recortan a
    [0, maximo]."""
    candidatos = candidatos_estacionales(reales, limites=(0.0, maximo), min_meses=60, nombre_propio="anomalia_por_comunidad")
    por_serie = {s: g.set_index("mes")["real"].sort_index() for s, g in reales.groupby("serie")}

    def _ets_5_anios(tendencia: bool, logaritmo: bool = False) -> Candidato:
        def prever(origen: pd.Timestamp) -> pd.DataFrame:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing

            partes = []
            for serie, s in por_serie.items():
                s = s.loc[:origen]
                if len(s) < 60 or s.index.max() < origen:
                    continue
                filas = _filas_futuras(serie, origen)
                valores = s.iloc[-60:].to_numpy(dtype=float)
                if logaritmo:
                    valores = np.log(np.maximum(valores, 1.0))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    ajuste = ExponentialSmoothing(
                        valores, trend="add" if tendencia else None, damped_trend=tendencia, seasonal="add",
                        seasonal_periods=12, initialization_method="estimated",
                    ).fit()
                prevision = ajuste.forecast(len(filas))
                filas["prevision"] = np.clip(np.exp(prevision) if logaritmo else prevision, 0, maximo)
                partes.append(filas)
            return pd.concat(partes, ignore_index=True)

        return prever

    candidatos["ets_5_anios"] = _ets_5_anios(tendencia=True)
    candidatos["ets_5_anios_sin_tendencia"] = _ets_5_anios(tendencia=False)
    if con_log:
        candidatos["ets_5_anios_log"] = _ets_5_anios(tendencia=True, logaritmo=True)
    return candidatos


GRUPOS_RENOVABLES: tuple[str, ...] = ("solar", "eolica", "hidraulica", "otras_renovables")


@lru_cache(maxsize=4096)
def _prevision_tecnologia(historia_bytes: bytes) -> np.ndarray:
    """Reutiliza el ETS solo cuando coinciden los 60 valores ya observados."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    historia = np.frombuffer(historia_bytes, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ajuste = ExponentialSmoothing(
            np.log(np.maximum(historia, 1.0)), trend="add", damped_trend=True, seasonal="add",
            seasonal_periods=12, initialization_method="estimated",
        ).fit()
    prevision = np.exp(ajuste.forecast(HORIZONTE))
    prevision.setflags(write=False)
    return prevision


def candidato_suma_tecnologias(tecnologias: pd.DataFrame, objetivo: str, hoy: dt.date | None = None) -> Candidato:
    """Prevé cada grupo de tecnología de cada comunidad por separado (ETS amortiguada sobre el logaritmo, últimos
    5 años) y los suma. Cada tecnología tiene su propia estacionalidad (la solar alcanza su máximo en verano, la
    eólica en invierno y la hidráulica en primavera) y su propia tendencia (la solar crece mucho), que se mezclan en
    el total.

    Args:
        tecnologias: tabla `ccaa_generacion_tecnologia` (`codigo_ccaa`, `fecha`, `grupo`, `generacion_mwh`).
        objetivo: `mwh` (generación renovable) o `pct` (% renovable = renovable / (renovable + no renovable)).
    """
    en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    datos = tecnologias.assign(
        mes=pd.to_datetime(tecnologias["fecha"]).dt.to_period("M").dt.to_timestamp(),
        serie=tecnologias["codigo_ccaa"].astype(str).str.zfill(2),
    )
    datos = datos[datos["mes"] < en_curso]
    tabla = datos.pivot_table(index=["serie", "grupo"], columns="mes", values="generacion_mwh", aggfunc="sum").fillna(0.0)
    cache: dict[pd.Timestamp, dict[tuple[str, str], np.ndarray]] = {}

    def _componentes(origen: pd.Timestamp) -> dict[tuple[str, str], np.ndarray]:
        if origen not in cache:
            salida = {}
            for clave, fila in tabla.iterrows():
                historia = fila.loc[:origen].iloc[-60:].to_numpy(dtype=float)
                if len(historia) < 60 or historia.sum() <= 0:
                    salida[clave] = np.zeros(HORIZONTE)
                    continue
                salida[clave] = _prevision_tecnologia(historia.tobytes())
            cache[origen] = salida
        return cache[origen]

    def prever(origen: pd.Timestamp) -> pd.DataFrame:
        componentes = _componentes(origen)
        partes = []
        for serie in tabla.index.get_level_values("serie").unique():
            renovable = sum(componentes.get((serie, g), np.zeros(HORIZONTE)) for g in GRUPOS_RENOVABLES)
            no_renovable = componentes.get((serie, "no_renovable"), np.zeros(HORIZONTE))
            filas = _filas_futuras(serie, origen)
            filas["prevision"] = renovable if objetivo == "mwh" else np.clip(100 * renovable / np.maximum(renovable + no_renovable, 1.0), 0, 100)
            partes.append(filas)
        return pd.concat(partes, ignore_index=True)

    return prever


def candidato_tecnologias_hidro_embalses(tecnologias: pd.DataFrame, reserva_nacional: pd.Series, hoy: dt.date | None = None) -> Candidato:
    """Generación renovable (MWh) como suma de tecnologías, pero con la **hidráulica prevista desde los embalses**
    (Ridge sobre anomalías con la reserva nacional, `candidato_ridge_anomalias`): la hidráulica depende sobre todo
    del agua embalsada. Solar, eólica y resto, con su ETS (`candidato_suma_tecnologias`)."""
    datos = tecnologias.assign(codigo_ccaa=tecnologias["codigo_ccaa"].astype(str).str.zfill(2))
    hidro = datos[datos["grupo"] == "hidraulica"]
    reales_hidro = series_renovables(hidro.assign(pct_renovable=hidro["generacion_mwh"]), hoy, columna="pct_renovable")
    prever_hidro = candidato_ridge_anomalias(reales_hidro, reserva_nacional, logaritmo=True)
    prever_resto = candidato_suma_tecnologias(datos[datos["grupo"] != "hidraulica"], "mwh", hoy)
    claves = ["serie", "mes", "horizonte_meses"]

    def prever(origen: pd.Timestamp) -> pd.DataFrame:
        resto = prever_resto(origen).set_index(claves)["prevision"].astype(float)
        agua = prever_hidro(origen).set_index(claves)["prevision"].astype(float)
        return resto.add(agua.reindex(resto.index).fillna(0.0), fill_value=0.0).rename("prevision").reset_index()

    return prever


def candidato_ridge_anomalias(reales: pd.DataFrame, reserva_nacional: pd.Series, logaritmo: bool = False) -> Candidato:
    """Ridge (ML) sobre anomalías: prevé la diferencia entre el mes objetivo y la media de ese mes en los 3 años
    anteriores, con la anomalía del origen (último mes y media de 3 meses), la anomalía de la **reserva nacional de
    los embalses** en el origen (más agua → más hidráulica los meses siguientes), el horizonte, el mes y la comunidad.
    Una sola regresión para todas las comunidades y horizontes, entrenada solo con meses objetivo hasta el origen.

    Args:
        reales: `serie`, `mes`, `real` (% renovable, o MWh con `logaritmo`).
        reserva_nacional: reserva nacional de los embalses (%) por mes (`cpd.features.precio.serie_reserva_nacional`).
        logaritmo: trabajar con el logaritmo (para MWh).
    """
    tabla = reales.pivot(index="mes", columns="serie", values="real").sort_index()
    if logaritmo:
        tabla = np.log(tabla.clip(lower=1.0))
    base = pd.concat([tabla.shift(12), tabla.shift(24), tabla.shift(36)]).groupby(level=0).mean()
    anomalia = tabla - base
    reserva = reserva_nacional.sort_index()
    anomalia_reserva = reserva - reserva.groupby(reserva.index.month).transform(lambda v: v.rolling(10, min_periods=3).mean().shift(1))
    filas = []
    for h in range(1, HORIZONTE + 1):
        for serie in tabla.columns:
            f = pd.DataFrame(
                {
                    "serie": serie, "origen": tabla.index, "h": h, "a1": anomalia[serie].to_numpy(),
                    "a3": anomalia[serie].rolling(3).mean().to_numpy(), "res": anomalia_reserva.reindex(tabla.index).to_numpy(),
                }
            )
            f["mes"] = f["origen"] + pd.DateOffset(months=h)
            # Media del mes objetivo en los 3 años anteriores: usa meses ≤ objetivo − 12 ≤ origen (h ≤ 12).
            f["base"] = base[serie].reindex(f["mes"]).to_numpy()
            f["real"] = tabla[serie].reindex(f["mes"]).to_numpy()
            filas.append(f)
    X = pd.concat(filas, ignore_index=True)
    X["y"] = X["real"] - X["base"]
    X["mes_sin"], X["mes_cos"] = np.sin(2 * np.pi * X["mes"].dt.month / 12), np.cos(2 * np.pi * X["mes"].dt.month / 12)
    X["a1_h"], X["res_h"] = X["a1"] / X["h"], X["res"] / X["h"]
    ficticias = pd.get_dummies(X["serie"], prefix="s", dtype=float)
    X = pd.concat([X, ficticias], axis=1)
    columnas = ["a1", "a3", "res", "h", "mes_sin", "mes_cos", "a1_h", "res_h", *ficticias.columns]

    def prever(origen: pd.Timestamp) -> pd.DataFrame:
        entrenamiento = X[X["mes"] <= origen].dropna(subset=[*columnas, "y"])
        filas_origen = X[X["origen"] == origen].dropna(subset=[*columnas, "base"])
        if len(entrenamiento) < 200 or filas_origen.empty:
            return pd.DataFrame({"serie": pd.Series(dtype=str), "mes": pd.Series(dtype="datetime64[ns]"), "horizonte_meses": pd.Series(dtype=int), "prevision": pd.Series(dtype=float)})
        modelo = make_pipeline(StandardScaler(), Ridge(alpha=10.0)).fit(entrenamiento[columnas].to_numpy(), entrenamiento["y"].to_numpy())
        valor = filas_origen["base"].to_numpy() + modelo.predict(filas_origen[columnas].to_numpy())
        return pd.DataFrame(
            {
                "serie": filas_origen["serie"].to_numpy(), "mes": filas_origen["mes"].to_numpy(),
                "horizonte_meses": filas_origen["h"].to_numpy(), "prevision": np.exp(valor) if logaritmo else np.clip(valor, 0, 100),
            }
        )

    return prever


def candidatos_temperatura(reales: pd.DataFrame) -> dict[str, Candidato]:
    """Candidatos para la temperatura media mensual de cada provincia (°C): los mismos que las reservas
    (`candidatos_estacionales`), sin recortar y con 5 años de historia mínima (NASA POWER empieza en 2015)."""
    return candidatos_estacionales(reales, limites=None, min_meses=60, nombre_propio="anomalia_por_provincia")


# ------------------------------------------------------------------------------------------------------ evaluación


def _metricas(datos: pd.DataFrame) -> dict[str, float]:
    return {"n": len(datos), **metricas_regresion(datos["real"], datos["prevision"])}


def evaluar(candidatos: dict[str, Candidato], reales: pd.DataFrame, origenes: Origenes, metrica: str) -> dict[str, Any]:
    """Backtesting de 1 año de todos los candidatos, combinación de los mejores y elección con la validación.

    Args:
        candidatos: nombre → función de previsión desde un origen.
        reales: `serie`, `mes`, `real`.
        origenes: salida de `definir_origenes`.
        metrica: `mape_pct` o `mae` (la que decide).

    Returns:
        `predicciones` (todas, con `real`), `metricas` (modelo × partición), `por_horizonte` (modelo × partición × h),
        `ranking` (validación), `miembros` de la combinación, `elegido` y `residuos_log` (por horizonte, elegido).
    """
    partes = []
    for nombre, prever in candidatos.items():
        for particion, lista in (("validacion", origenes.validacion), ("test", (origenes.test,))):
            for origen in lista:
                p = prever(origen)
                if p is not None and not p.empty:
                    partes.append(p.assign(modelo=nombre, origen=origen, particion=particion))
    pred = pd.concat(partes, ignore_index=True).merge(reales, on=["serie", "mes"], how="inner").dropna(subset=["prevision", "real"])
    pred["prevision"] = pred["prevision"].astype(float)
    # Mismas filas para todos: solo (serie, mes, origen) que tienen todos los modelos.
    claves = ["serie", "mes", "origen", "particion"]
    completos = pred.groupby(claves)["modelo"].nunique() == len(candidatos)
    pred = pred.set_index(claves).loc[completos[completos].index].reset_index()

    ranking = pred[pred["particion"] == "validacion"].groupby("modelo").apply(lambda d: _metricas(d)[metrica], include_groups=False).sort_values()
    miembros = list(ranking.index[:MIEMBROS_COMBINACION])
    combinacion = (
        pred[pred["modelo"].isin(miembros)]
        .groupby([*claves, "horizonte_meses"], as_index=False)
        .agg(prevision=("prevision", "mean"), real=("real", "first"))
        .assign(modelo="combinacion")
    )
    pred = pd.concat([pred, combinacion], ignore_index=True)

    metricas = pred.groupby(["modelo", "particion"]).apply(lambda d: pd.Series(_metricas(d)), include_groups=False).reset_index()
    por_horizonte = (
        pred.groupby(["modelo", "particion", "horizonte_meses"]).apply(lambda d: pd.Series(_metricas(d)), include_groups=False).reset_index()
    )
    en_validacion = metricas[metricas["particion"] == "validacion"].set_index("modelo")[metrica].sort_values()
    # Regla: la combinación, salvo que un modelo solo la mejore claramente (más de MARGEN_COMBINACION) en validación.
    mejor_individual = en_validacion.drop("combinacion")
    if mejor_individual.iloc[0] < en_validacion["combinacion"] * (1 - MARGEN_COMBINACION):
        elegido = str(mejor_individual.index[0])
    else:
        elegido = "combinacion"
    val = pred[(pred["modelo"] == elegido) & (pred["particion"] == "validacion")]
    por_h = val["horizonte_meses"]
    with np.errstate(invalid="ignore", divide="ignore"):  # el log solo tiene sentido con valores > 0 (no en °C)
        residuos = (np.log(val["real"]) - np.log(val["prevision"])).groupby(por_h).apply(lambda r: r.to_numpy())
    diferencias = (val["real"] - val["prevision"]).groupby(por_h).apply(lambda r: r.to_numpy())
    return {
        "predicciones": pred,
        "metricas": metricas,
        "por_horizonte": por_horizonte,
        "ranking": en_validacion,
        "miembros": miembros,
        "elegido": elegido,
        "residuos_log": residuos.to_dict(),
        "residuos_abs": diferencias.to_dict(),
        "metrica": metrica,
        "origenes": origenes.como_texto(),
    }


def intervalo_media_anual(resultado: dict[str, Any], cuantiles: tuple[float, float] = (0.1, 0.9), aditivo: bool = False) -> pd.DataFrame:
    """Rango de la media de los 12 meses: cuantiles, por serie, del cociente real / previsto de la media anual del
    modelo elegido en los orígenes de validación (con todas las series juntas si una tiene pocos orígenes).

    Args:
        aditivo: usar la diferencia real − previsto en lugar del cociente (para magnitudes sin cero natural, como
            la temperatura en °C).

    Returns:
        `serie`, `factor_inferior`, `factor_superior` (multiplican la media prevista; si `aditivo`, se le suman).
    """
    pred = resultado["predicciones"]
    val = pred[(pred["modelo"] == resultado["elegido"]) & (pred["particion"] == "validacion")]
    medias = val.groupby(["serie", "origen"]).agg(real=("real", "mean"), prevision=("prevision", "mean"), n=("real", "size"))
    medias = medias[medias["n"] == HORIZONTE]
    cociente = medias["real"] - medias["prevision"] if aditivo else medias["real"] / medias["prevision"]
    global_bajo, global_alto = np.quantile(cociente, cuantiles)
    filas = []
    for serie, c in cociente.groupby(level="serie"):
        bajo, alto = (np.quantile(c, cuantiles) if len(c) >= 6 else (global_bajo, global_alto))
        filas.append({"serie": serie, "factor_inferior": float(bajo), "factor_superior": float(alto)})
    return pd.DataFrame(filas)


def acierto_media_anual(resultado: dict[str, Any]) -> dict[str, float]:
    """Acierto (100 − WAPE, %) de la media de los 12 meses previstos frente a la media real, del modelo elegido y por
    partición (`validacion`, `test`). Mide la cifra anual, no cada mes: los errores de meses sueltos se compensan."""
    pred = resultado["predicciones"]
    pred = pred[pred["modelo"] == resultado["elegido"]]
    medias = pred.groupby(["particion", "serie", "origen"]).agg(real=("real", "mean"), prevision=("prevision", "mean"), n=("real", "size"))
    medias = medias[medias["n"] == HORIZONTE]
    return {
        str(particion): float(100 * (1 - (d["real"] - d["prevision"]).abs().sum() / d["real"].abs().sum()))
        for particion, d in medias.groupby(level="particion")
    }


def prevision_final(
    candidatos: dict[str, Candidato],
    resultado: dict[str, Any],
    origen_por_serie: dict[str, pd.Timestamp],
    cuantiles: tuple[float, float] = (0.1, 0.9),
    aditivo: bool = False,
) -> pd.DataFrame:
    """Previsión de los 12 meses siguientes al último dato de cada serie con el modelo elegido (o la combinación).

    El intervalo sale de los cuantiles del error de validación por horizonte: relativo (log real − log previsto)
    o, si `aditivo`, en la unidad de la serie (real − previsto), que es lo correcto para la temperatura en °C.

    Returns:
        `serie`, `mes`, `horizonte_meses`, `prevision`, `inferior`, `superior`, `modelo`, `origen`, `generado_en`.
    """
    nombres = resultado["miembros"] if resultado["elegido"] == "combinacion" else [resultado["elegido"]]
    partes = []
    for origen in sorted(set(origen_por_serie.values())):
        series = [s for s, o in origen_por_serie.items() if o == origen]
        juntas = pd.concat([candidatos[n](origen).assign(miembro=n) for n in nombres])
        juntas = juntas[juntas["serie"].isin(series)]
        partes.append(juntas.groupby(["serie", "mes", "horizonte_meses"], as_index=False)["prevision"].mean().assign(origen=origen))
    salida = pd.concat(partes, ignore_index=True)
    salida["prevision"] = salida["prevision"].astype(float)
    residuos = resultado["residuos_abs" if aditivo else "residuos_log"]
    bajo = salida["horizonte_meses"].map(lambda h: np.quantile(residuos[h], cuantiles[0]))
    alto = salida["horizonte_meses"].map(lambda h: np.quantile(residuos[h], cuantiles[1]))
    return salida.assign(
        inferior=salida["prevision"] + bajo if aditivo else salida["prevision"] * np.exp(bajo),
        superior=salida["prevision"] + alto if aditivo else salida["prevision"] * np.exp(alto),
        modelo=resultado["elegido"],
        generado_en=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    )
