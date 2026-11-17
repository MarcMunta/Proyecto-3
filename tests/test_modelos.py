"""Tests de features, particiones, métricas y modelos (fases 6 a 8).

Usan series y tablas SINTÉTICAS generadas aquí (solo para el test): no dependen de `data/curated/`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cpd.features.demanda import (
    columnas_features,
    construir_features_demanda,
    marcar_atipicos_demanda,
    preparar_serie_modelo,
)
from cpd.features.provincia import EXCLUIDAS_POR_FUGA, FEATURES_PROVINCIA
from cpd.modelos import prob_cpd
from cpd.modelos.demanda import (
    Periodos,
    asignar_particion,
    comprobar_particiones,
    definir_periodos,
    evaluar_horizonte,
    prevision_baseline,
)
from cpd.modelos.metricas import mae, mape, matriz_confusion, metricas_clasificacion, rmse, umbral_youden


def serie_sintetica(meses: int = 72, comunidades: tuple[str, ...] = ("01", "13"), semilla: int = 0) -> pd.DataFrame:
    """Demanda SINTÉTICA con nivel, estacionalidad y ruido (MWh). Solo para tests."""
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range("2018-01-01", periods=meses, freq="MS")
    filas = []
    for i, codigo in enumerate(comunidades):
        nivel = 1e6 * (i + 1)
        estacional = 1 + 0.1 * np.sin(2 * np.pi * fechas.month / 12)
        valores = nivel * estacional * (1 + 0.02 * rng.standard_normal(meses))
        filas.append(pd.DataFrame({"codigo_ccaa": codigo, "ccaa": f"Comunidad {codigo}", "mes": fechas, "demanda_mwh": valores}))
    return pd.concat(filas, ignore_index=True)


# ---------- Features sin fuga (R-8) ----------


@pytest.mark.parametrize("horizonte", [1, 12])
def test_features_no_usan_datos_posteriores_a_t_menos_h(horizonte):
    serie = serie_sintetica()
    corte = pd.Timestamp("2021-06-01")
    original = construir_features_demanda(serie, horizonte)
    alterada = serie.copy()
    alterada.loc[alterada["mes"] > corte, "demanda_mwh"] *= 3.0  # cambio enorme en el "futuro"
    cambiada = construir_features_demanda(alterada, horizonte)
    columnas = [*columnas_features(original), "nivel_mwh"]
    # Las filas cuyo mes de referencia (t − h) es anterior o igual al corte no pueden cambiar.
    claves = ["codigo_ccaa", "mes"]
    a = original[original["mes_referencia"] <= corte].set_index(claves)[columnas]
    b = cambiada.set_index(claves).loc[a.index, columnas]
    pd.testing.assert_frame_equal(a, b)


def test_features_solo_usan_lags_iguales_o_mayores_que_el_horizonte():
    tabla = construir_features_demanda(serie_sintetica(), 12)
    lags = [int(c.split("_")[-1]) for c in columnas_features(tabla) if c.startswith("f_lag_")]
    assert lags and min(lags) >= 12
    assert "objetivo_log_ratio" not in columnas_features(tabla)


def test_objetivo_reconstruye_la_demanda():
    tabla = construir_features_demanda(serie_sintetica(), 1)
    reconstruida = np.exp(tabla["objetivo_log_ratio"]) * tabla["nivel_mwh"]
    np.testing.assert_allclose(reconstruida, tabla["demanda_mwh"], rtol=1e-9)


# ---------- Atípicos (R-10) ----------


def test_marca_negativos_y_saltos_pero_no_la_estacionalidad():
    serie = serie_sintetica(meses=48)
    i_negativo = serie.index[(serie["codigo_ccaa"] == "01") & (serie["mes"] == "2020-03-01")][0]
    i_salto = serie.index[(serie["codigo_ccaa"] == "13") & (serie["mes"] == "2021-02-01")][0]
    serie.loc[i_negativo, "demanda_mwh"] = -5.0
    serie.loc[i_salto, "demanda_mwh"] *= 5
    marcada = marcar_atipicos_demanda(serie)
    assert set(marcada.index[marcada["atipico"]]) == {i_negativo, i_salto}


def test_preparar_serie_recorta_el_final_e_imputa_solo_huecos_intermedios():
    serie = serie_sintetica(meses=48)
    ultimo = serie["mes"].max()
    serie.loc[(serie["codigo_ccaa"] == "01") & (serie["mes"] == ultimo), "demanda_mwh"] = -1.0
    serie.loc[(serie["codigo_ccaa"] == "01") & (serie["mes"] == "2020-06-01"), "demanda_mwh"] = -1.0
    preparada = preparar_serie_modelo(serie)
    c01 = preparada[preparada["codigo_ccaa"] == "01"]
    assert c01["mes"].max() == ultimo - pd.DateOffset(months=1)
    imputada = c01[c01["mes"] == "2020-06-01"].iloc[0]
    assert imputada["imputado"]
    anterior = serie[(serie["codigo_ccaa"] == "01") & (serie["mes"] == "2019-06-01")]["demanda_mwh"].iloc[0]
    assert imputada["demanda_mwh"] == pytest.approx(anterior)
    # Un mes imputado nunca es objetivo.
    tabla = construir_features_demanda(preparada, 1)
    fila = tabla[(tabla["codigo_ccaa"] == "01") & (tabla["mes"] == "2020-06-01")]
    assert fila.empty or fila["objetivo_log_ratio"].isna().all()


# ---------- Particiones temporales (R-6) ----------


def test_particiones_son_temporales_y_no_se_solapan():
    serie = serie_sintetica(meses=84).assign(imputado=False)
    periodos = definir_periodos(serie)
    assert periodos.inicio_validacion < periodos.inicio_test <= periodos.fin_test
    tabla = construir_features_demanda(serie, 1)
    tabla["particion"] = asignar_particion(tabla["mes"], periodos)
    comprobar_particiones(tabla)
    rango = tabla.groupby("particion")["mes"].agg(["min", "max"])
    assert rango.loc["entrenamiento", "max"] < rango.loc["validacion", "min"]
    assert rango.loc["validacion", "max"] < rango.loc["test", "min"]
    assert tabla[tabla["particion"] == "test"]["mes"].nunique() == 12


def test_comprobar_particiones_detecta_solapes():
    tabla = pd.DataFrame(
        {"mes": pd.to_datetime(["2020-01-01", "2020-03-01", "2020-02-01", "2020-04-01"]), "particion": ["entrenamiento", "entrenamiento", "validacion", "test"]}
    )
    with pytest.raises(AssertionError):
        comprobar_particiones(tabla)


def test_baseline_estacional_es_el_mismo_mes_del_anio_anterior():
    serie = serie_sintetica()
    tabla = construir_features_demanda(serie, 1)
    prevision = prevision_baseline("estacional", tabla, serie, 1)
    indice = serie.set_index(["codigo_ccaa", "mes"])["demanda_mwh"]
    esperado = [indice[(c, m - pd.DateOffset(months=12))] for c, m in zip(tabla["codigo_ccaa"], tabla["mes"])]
    np.testing.assert_allclose(prevision, esperado, rtol=1e-9)


def test_evaluar_horizonte_compara_todos_los_modelos_con_las_mismas_filas():
    serie = serie_sintetica(meses=84).assign(imputado=False)
    resultado = evaluar_horizonte(serie, 1, definir_periodos(serie))
    metricas = resultado["metricas"]
    assert set(metricas["modelo"]) == {"naive", "estacional", "tendencia_estacionalidad", "ridge", "gradient_boosting"}
    assert metricas.groupby("particion")["n"].nunique().max() == 1  # mismas filas para todos
    assert resultado["elegido"]["modelo"] in set(metricas["modelo"])


# ---------- Métricas (fase 8) ----------


def test_metricas_de_regresion():
    real, prevision = [100.0, 200.0, 300.0], [110.0, 190.0, 330.0]
    assert mae(real, prevision) == pytest.approx(50 / 3)
    assert rmse(real, prevision) == pytest.approx(np.sqrt((100 + 100 + 900) / 3))
    assert mape(real, prevision) == pytest.approx((10 + 5 + 10) / 3)
    with pytest.raises(ValueError):
        mape([0.0, 1.0], [1.0, 1.0])


def test_metricas_de_clasificacion_y_paradoja_de_la_exactitud():
    real = np.array([0] * 8 + [1] * 2)
    siempre_cero = np.full(10, 0.1)
    m = metricas_clasificacion(real, siempre_cero)
    assert m["accuracy"] == pytest.approx(0.8)  # acierta mucho...
    assert m["recall"] == 0.0  # ...pero no detecta ningún positivo
    assert matriz_confusion(real, siempre_cero >= 0.5) == {"vp": 0, "fp": 0, "fn": 2, "vn": 8}
    separable = np.array([0.1] * 8 + [0.9] * 2)
    assert metricas_clasificacion(real, separable)["roc_auc"] == pytest.approx(1.0)
    assert 0.1 < umbral_youden(real, separable) <= 0.9


# ---------- prob_cpd ----------


def tabla_provincias_sintetica(n: int = 30, semilla: int = 1) -> pd.DataFrame:
    """Provincias SINTÉTICAS (solo para el test): la etiqueta depende de la población."""
    rng = np.random.default_rng(semilla)
    datos = {c: rng.normal(size=n) for c in FEATURES_PROVINCIA}
    datos["log_poblacion"] = np.sort(rng.normal(13, 1, size=n))
    tabla = pd.DataFrame(datos, index=pd.Index([f"{i:02d}" for i in range(n)], name="codigo_provincia"))
    tabla["tiene_cpd"] = (np.arange(n) >= n * 0.7).astype(int)
    tabla["provincia"] = [f"P{i}" for i in range(n)]
    tabla["ccaa"] = "X"
    tabla["n_centros_datos"] = tabla["tiene_cpd"] * 2
    return tabla


def test_features_de_provincia_no_incluyen_columnas_con_fuga():
    assert not set(EXCLUIDAS_POR_FUGA) & set(FEATURES_PROVINCIA)


def test_probabilidades_fuera_de_pliegue(monkeypatch):
    monkeypatch.setattr(prob_cpd, "REPETICIONES", 2)
    tabla = tabla_provincias_sintetica()
    modelo, columnas = prob_cpd.modelos_candidatos()["solo_poblacion"]
    prob = prob_cpd.probabilidades_fuera_de_pliegue(tabla, modelo, columnas)
    assert prob.between(0, 1).all() and prob.index.equals(tabla.index)
    # La etiqueta depende de la población: las provincias con CPD reciben más probabilidad de media.
    assert prob[tabla["tiene_cpd"] == 1].mean() > prob[tabla["tiene_cpd"] == 0].mean()


def test_periodos_como_texto():
    p = Periodos(pd.Timestamp("2024-07-01"), pd.Timestamp("2025-07-01"), pd.Timestamp("2026-06-01"))
    assert p.como_texto() == {"entrenamiento_hasta": "2024-06", "validacion": "2024-07 a 2025-06", "test": "2025-07 a 2026-06"}


def test_preparar_serie_rellena_meses_sin_fila():
    serie = serie_sintetica(meses=48)
    hueco = (serie["codigo_ccaa"] == "13") & (serie["mes"] == "2020-10-01")
    preparada = preparar_serie_modelo(serie[~hueco])  # el curado ya dejó ese mes sin dato
    fila = preparada[(preparada["codigo_ccaa"] == "13") & (preparada["mes"] == "2020-10-01")].iloc[0]
    assert fila["imputado"] and fila["sin_dato_valido"]
    anterior = serie[(serie["codigo_ccaa"] == "13") & (serie["mes"] == "2019-10-01")]["demanda_mwh"].iloc[0]
    assert fila["demanda_mwh"] == pytest.approx(anterior)
    assert preparada.groupby("codigo_ccaa")["mes"].apply(lambda m: m.diff().dropna().dt.days.max() <= 31).all()


# ---------- Precio de la luz (cpd.features.precio, cpd.modelos.precio) ----------


def mensual_sintetico(meses: int = 84, semilla: int = 3) -> pd.DataFrame:
    """Precio, reserva y CO2 mensuales SINTÉTICOS (solo para tests)."""
    from cpd.features import precio as fp

    rng = np.random.default_rng(semilla)
    fechas = pd.date_range("2017-01-01", periods=meses, freq="MS")
    precio = 60 * (1 + 0.2 * np.sin(2 * np.pi * fechas.month / 12)) * np.exp(0.05 * rng.standard_normal(meses))
    reserva = 50 + 10 * np.cos(2 * np.pi * fechas.month / 12)
    co2 = 4e6 * (1 + 0.1 * rng.standard_normal(meses))
    return fp.tabla_mensual(
        pd.Series(precio, index=fechas, name="precio_eur_mwh"),
        pd.Series(reserva, index=fechas, name="reserva_nacional_pct"),
        pd.Series(co2, index=fechas, name="co2_tco2eq"),
    )


def test_precio_mensual_quita_el_mes_en_curso_y_los_incompletos():
    import datetime as dt

    from cpd.features import precio as fp

    dias = pd.date_range("2026-08-01", "2026-11-14", freq="D").delete(5)  # falta el 6 de agosto
    diarios = pd.DataFrame({"fecha": dias.strftime("%Y-%m-%d"), "precio_spot_eur_mwh": 100.0})
    serie = fp.serie_precio_mensual(diarios, hoy=dt.date(2026, 11, 17))
    assert list(serie.index.strftime("%Y-%m")) == ["2026-09", "2026-10"]


def test_features_de_precio_no_usan_datos_posteriores_al_origen():
    from cpd.features import precio as fp

    mensual = mensual_sintetico()
    corte = pd.Timestamp("2020-06-01")
    original = fp.construir_features_precio(mensual)
    alterado = mensual.copy()
    alterado.loc[alterado.index > corte, :] *= 2.5
    cambiado = fp.construir_features_precio(alterado)
    columnas = [*fp.columnas_features(original), "nivel_eur_mwh"]
    claves = ["mes", "horizonte_meses"]
    a = original[original["mes_origen"] <= corte].set_index(claves)[columnas]
    b = cambiado.set_index(claves).loc[a.index, columnas]
    pd.testing.assert_frame_equal(a, b)


def test_baselines_de_precio():
    from cpd.features import precio as fp
    from cpd.modelos import precio as mp

    mensual = mensual_sintetico()
    filas = fp.construir_features_precio(mensual).dropna(subset=["objetivo_log_ratio"]).head(30)
    p = mensual["precio_eur_mwh"]
    np.testing.assert_allclose(mp.prevision_baseline("naive", filas, mensual), p.loc[filas["mes_origen"]].to_numpy())
    media = [p.loc[o - pd.DateOffset(months=11) : o].mean() for o in filas["mes_origen"]]
    np.testing.assert_allclose(mp.prevision_baseline("media_12m", filas, mensual), media)
    np.testing.assert_allclose(mp.prevision_baseline("estacional", filas, mensual), p.loc[filas["mes"] - pd.DateOffset(months=12)].to_numpy())


def test_evaluar_precio_y_prevision_final():
    from cpd.modelos import precio as mp

    mensual = mensual_sintetico()
    periodos = mp.definir_periodos(mensual)
    resultado = mp.evaluar(mensual, periodos)
    metricas = resultado["metricas"]
    assert set(metricas["modelo"]) == {*mp.BASELINES, "ridge", "gradient_boosting"}
    todos = metricas[metricas["horizonte"] == "todos"]
    assert todos.groupby("particion")["n"].nunique().max() == 1  # mismas filas para todos
    prevision, _ = mp.prevision_final(mensual, resultado)
    assert len(prevision) == 12 and (prevision["inferior_eur_mwh"] <= prevision["superior_eur_mwh"]).all()
    assert prevision["mes"].min() == mensual.index.max() + pd.DateOffset(months=1)
    backtest = mp.media_anual_por_origen(mensual, {"ridge": "alpha=100"}, [pd.Timestamp("2021-01-01")])
    resumen = mp.resumen_anual(prevision, backtest, mensual)
    assert resumen["ultimo_mes"] == mensual.index.max().strftime("%Y-%m")


# ---------- Previsión a 1 año (cpd.modelos.anual) ----------


def test_origenes_de_1_anio_no_se_solapan_con_el_test():
    from cpd.modelos import anual

    o = anual.definir_origenes(pd.Timestamp("2026-06-01"))
    assert len(o.validacion) == anual.ORIGENES_VALIDACION
    ultimo_mes_validacion = o.validacion[-1] + pd.DateOffset(months=anual.HORIZONTE)
    assert ultimo_mes_validacion <= o.test  # ningún mes objetivo de validación cae en el test
    assert o.test == pd.Timestamp("2025-06-01")


def test_candidatos_de_demanda_solo_usan_datos_hasta_el_origen():
    from cpd.modelos import anual

    serie = serie_sintetica(meses=96).assign(imputado=False)
    origen = pd.Timestamp("2022-06-01")
    alterada = serie.copy()
    alterada.loc[alterada["mes"] > origen, "demanda_mwh"] *= 4  # el futuro cambia mucho
    a = {n: f(origen) for n, f in anual.candidatos_demanda(serie).items()}
    b = {n: f(origen) for n, f in anual.candidatos_demanda(alterada).items()}
    for nombre in a:
        np.testing.assert_allclose(a[nombre]["prevision"].to_numpy(), b[nombre]["prevision"].to_numpy(), rtol=1e-6, err_msg=nombre)
        assert a[nombre]["mes"].min() == origen + pd.DateOffset(months=1)
        assert a[nombre]["horizonte_meses"].between(1, 12).all()


def test_evaluar_1_anio_elige_con_validacion_y_combina():
    from cpd.modelos import anual

    serie = serie_sintetica(meses=120).assign(imputado=False)
    candidatos = anual.candidatos_demanda(serie)
    origenes = anual.definir_origenes(serie["mes"].max(), n_validacion=6)
    resultado = anual.evaluar(candidatos, anual.reales_demanda(serie), origenes, "mape_pct")
    assert "combinacion" in set(resultado["metricas"]["modelo"])
    assert len(resultado["miembros"]) == anual.MIEMBROS_COMBINACION
    n = resultado["metricas"].query("particion == 'validacion'").set_index("modelo")["n"]
    assert n.nunique() == 1  # mismas filas para todos los modelos
    prevision = anual.prevision_final(candidatos, resultado, {"01": serie["mes"].max(), "13": serie["mes"].max()})
    assert len(prevision) == 24 and (prevision["inferior"] <= prevision["superior"]).all()
    intervalos = anual.intervalo_media_anual(resultado)
    assert (intervalos["factor_inferior"] <= intervalos["factor_superior"]).all()


def test_series_de_gas_mensuales_y_ultimo_valor_conocido():
    import datetime as dt

    from cpd.features import precio as fp

    # Datos de PRUEBA: gas diario y futuros sintéticos.
    diario = pd.DataFrame({"fecha": pd.date_range("2024-01-01", "2024-04-30", freq="D").strftime("%Y-%m-%d"), "gas_mibgas_es_eur_mwh": 30.0})
    futuros = pd.DataFrame(
        {"fecha": ["2024-01-10", "2024-01-11", "2024-03-05"], "producto": ["Y+1", "Y+1", "Q+1"], "precio_eur_mwh": [40.0, 42.0, 35.0]}
    )
    gas = fp.series_gas(diario, futuros, hoy=dt.date(2024, 4, 15))
    assert list(gas.index.strftime("%Y-%m")) == ["2024-01", "2024-02", "2024-03"]  # sin el mes en curso
    assert gas.loc["2024-01-01", "gas_y1_eur_mwh"] == pytest.approx(41.0)
    assert gas.loc["2024-03-01", "gas_y1_eur_mwh"] == pytest.approx(41.0)  # último valor conocido (hasta 2 meses)
    assert pd.isna(gas.loc["2024-01-01", "gas_q1_eur_mwh"])


# ---------- Requisito de acierto, demanda a 10 años y reservas ----------


def test_acierto_y_control_del_requisito():
    from cpd.modelos.metricas import acierto_pct, control_acierto

    assert acierto_pct([100.0, 100.0], [90.0, 110.0]) == pytest.approx(90.0)
    # Un mes con valor muy bajo no dispara el acierto como haría el MAPE.
    assert acierto_pct([100.0, 1.0], [100.0, 11.0]) == pytest.approx(100 * (1 - 10 / 101))
    assert control_acierto(84.9) == "no cumple (< 85 %)"
    assert control_acierto(85.0) == "cumple"
    assert control_acierto(92.0) == "cumple (objetivo 90 %)"
    assert control_acierto(99.9) == "sospechoso (≥ 99,9 %)"


def test_10_anios_sin_fuga_e_intervalo_que_no_se_estrecha():
    from cpd.modelos import largo_plazo as lp

    # Demanda anual SINTÉTICA (solo para el test).
    rng = np.random.default_rng(5)
    anual = pd.Series(260 + np.cumsum(rng.normal(0, 3, 19)), index=range(2007, 2026), name="demanda_twh")
    bt = lp.backtesting(anual)
    alterada = anual.copy()
    alterada.loc[2020:] *= 1.5
    bt2 = lp.backtesting(alterada)
    # Las previsiones hechas desde un origen anterior a 2020 no pueden cambiar si cambia el futuro.
    a = bt[bt["origen"] < 2020].set_index(["modelo", "origen", "anio"])["prevision_twh"]
    b = bt2[bt2["origen"] < 2020].set_index(["modelo", "origen", "anio"])["prevision_twh"]
    pd.testing.assert_series_equal(a, b)
    resultado = lp.evaluar(anual)
    prevision = lp.prevision(anual, resultado)
    ancho = prevision["superior_twh"] / prevision["prevision_twh"] - prevision["inferior_twh"] / prevision["prevision_twh"]
    assert len(prevision) == 10 and prevision["anio"].iloc[0] == 2026
    assert (ancho.diff().dropna() >= -1e-9).all()


def test_candidatos_de_reservas_solo_usan_datos_hasta_el_origen():
    from cpd.modelos import anual

    # Reservas SINTÉTICAS de dos cuencas (solo para el test).
    meses = pd.date_range("2005-01-01", "2024-12-01", freq="MS")
    filas = []
    for i, cuenca in enumerate(("A", "B")):
        valor = 50 + 20 * np.sin(2 * np.pi * meses.month / 12 + i) + np.random.default_rng(i).normal(0, 3, len(meses))
        filas.append(pd.DataFrame({"serie": cuenca, "mes": meses, "real": valor}))
    reales = pd.concat(filas, ignore_index=True)
    origen = pd.Timestamp("2020-06-01")
    alterada = reales.copy()
    alterada.loc[alterada["mes"] > origen, "real"] = 99.0
    a = {n: f(origen) for n, f in anual.candidatos_reservas(reales).items()}
    b = {n: f(origen) for n, f in anual.candidatos_reservas(alterada).items()}
    for nombre in a:
        np.testing.assert_allclose(a[nombre]["prevision"].to_numpy(), b[nombre]["prevision"].to_numpy(), rtol=1e-6, err_msg=nombre)
        assert a[nombre]["prevision"].between(0, 100).all()


def _resultado_precio_sintetico(error: float) -> dict:
    """Resultado de `anual.evaluar` SINTÉTICO (solo para el test): precio real 100 €/MWh y previsión 100 + error."""
    meses = pd.date_range("2023-01-01", periods=12, freq="MS")
    pred = pd.DataFrame(
        {"modelo": "ets", "particion": "validacion", "mes": meses, "horizonte_meses": range(1, 13), "real": 100.0, "prevision": 100.0 + error}
    )
    acierto = 100 - abs(error)
    metricas = pd.DataFrame([{"modelo": "ets", "particion": "validacion", "mae": abs(error), "acierto_pct": acierto}])
    por_h = pred.assign(acierto_pct=acierto)[["modelo", "particion", "horizonte_meses", "acierto_pct"]]
    return {"elegido": "ets", "metricas": metricas, "por_horizonte": por_h, "predicciones": pred}


def test_explicacion_del_precio_solo_si_no_cumple_el_acierto():
    from cpd.modelos.informe import _por_que_precio

    assert _por_que_precio(_resultado_precio_sintetico(5.0)) == ""
    texto = _por_que_precio(_resultado_precio_sintetico(40.0))
    assert "¿Por qué no llega al 85 %?" in texto
    assert "60 % a 1 mes" in texto and "escenario orientativo" in texto


def test_serie_de_temperatura_solo_con_meses_completos():
    from cpd.modelos import anual

    # Clima diario SINTÉTICO de una provincia (solo para el test): enero completo y febrero a medias.
    dias = pd.date_range("2024-01-01", "2024-02-10", freq="D")
    clima = pd.DataFrame({"fecha": dias.strftime("%Y-%m-%d"), "codigo_provincia": 5, "tmedia_c": np.where(dias.month == 1, 2.0, 6.0)})
    serie = anual.series_temperatura(clima, hoy=pd.Timestamp("2024-06-01").date())
    assert serie["serie"].tolist() == ["05"]
    assert serie["mes"].tolist() == [pd.Timestamp("2024-01-01")]
    assert serie["real"].iloc[0] == pytest.approx(2.0)


def test_candidatos_de_temperatura_sin_fuga_y_sin_recortar_bajo_cero():
    from cpd.modelos import anual

    # Temperaturas mensuales SINTÉTICAS (solo para el test) con inviernos bajo cero.
    meses = pd.date_range("2015-01-01", "2024-12-01", freq="MS")
    rng = np.random.default_rng(7)
    reales = pd.DataFrame({"serie": "42", "mes": meses, "real": 10 - 12 * np.cos(2 * np.pi * (meses.month - 1) / 12) + rng.normal(0, 1, len(meses))})
    origen = pd.Timestamp("2021-06-01")
    alterada = reales.copy()
    alterada.loc[alterada["mes"] > origen, "real"] = 40.0
    a = {n: f(origen) for n, f in anual.candidatos_temperatura(reales).items()}
    b = {n: f(origen) for n, f in anual.candidatos_temperatura(alterada).items()}
    for nombre in a:
        np.testing.assert_allclose(a[nombre]["prevision"].to_numpy(), b[nombre]["prevision"].to_numpy(), rtol=1e-6, err_msg=nombre)
    assert (a["climatologia"]["prevision"] < 0).any()  # enero bajo cero: no se recorta a 0
    assert "anomalia_por_provincia" in a and "anomalia_por_cuenca" not in a


def test_serie_de_renovables_sin_mes_en_curso_ni_series_siempre_a_cero():
    from cpd.modelos import anual

    # Generación SINTÉTICA (solo para el test): una comunidad con renovables y otra siempre a 0 (como Ceuta).
    meses = pd.date_range("2024-01-01", "2024-04-01", freq="MS")
    gen = pd.concat(
        [
            pd.DataFrame({"codigo_ccaa": 7, "fecha": meses.strftime("%Y-%m-%d"), "pct_renovable": [60.0, 70.0, 80.0, 50.0]}),
            pd.DataFrame({"codigo_ccaa": 18, "fecha": meses.strftime("%Y-%m-%d"), "pct_renovable": 0.0}),
        ]
    )
    serie = anual.series_renovables(gen, hoy=pd.Timestamp("2024-04-15").date())
    assert serie["serie"].unique().tolist() == ["07"]
    assert serie["mes"].max() == pd.Timestamp("2024-03-01")  # abril está en curso


def test_candidatos_de_renovables_sin_fuga_y_entre_0_y_100():
    from cpd.modelos import anual

    # % renovable SINTÉTICO (solo para el test): estacional y creciente.
    meses = pd.date_range("2015-01-01", "2024-12-01", freq="MS")
    rng = np.random.default_rng(3)
    valor = np.clip(40 + 0.25 * np.arange(len(meses)) + 15 * np.sin(2 * np.pi * meses.month / 12) + rng.normal(0, 4, len(meses)), 0, 100)
    reales = pd.DataFrame({"serie": "07", "mes": meses, "real": valor})
    origen = pd.Timestamp("2021-06-01")
    alterada = reales.copy()
    alterada.loc[alterada["mes"] > origen, "real"] = 5.0
    a = {n: f(origen) for n, f in anual.candidatos_renovables(reales).items()}
    b = {n: f(origen) for n, f in anual.candidatos_renovables(alterada).items()}
    for nombre in a:
        np.testing.assert_allclose(a[nombre]["prevision"].to_numpy(), b[nombre]["prevision"].to_numpy(), rtol=1e-6, err_msg=nombre)
        assert a[nombre]["prevision"].between(0, 100).all(), nombre
    assert {"ets_5_anios", "ets_5_anios_sin_tendencia", "anomalia_por_comunidad"} <= set(a)


def test_acierto_de_la_media_anual():
    from cpd.modelos import anual

    # Predicciones SINTÉTICAS (solo para el test): el error de cada mes se compensa en la media de 12 meses.
    meses = pd.date_range("2023-01-01", periods=12, freq="MS")
    pred = pd.DataFrame(
        {"modelo": "ets", "particion": "validacion", "serie": "07", "origen": pd.Timestamp("2022-12-01"), "mes": meses,
         "real": 50.0, "prevision": np.where(np.arange(12) % 2 == 0, 40.0, 60.0)}
    )
    acierto = anual.acierto_media_anual({"elegido": "ets", "predicciones": pred})
    assert acierto == {"validacion": pytest.approx(100.0)}


def test_metricas_con_un_real_igual_a_cero_dejan_el_mape_vacio():
    from cpd.modelos.metricas import metricas_regresion

    m = metricas_regresion([0.0, 10.0], [1.0, 9.0])
    assert np.isnan(m["mape_pct"])
    assert m["mae"] == pytest.approx(1.0)
    assert m["acierto_pct"] == pytest.approx(100 * (1 - 2 / 10))
