"""Regresiones de fiabilidad con datos de prueba explícitamente sintéticos."""
import datetime as dt
import json

import duckdb
import pandas as pd
import pytest

from cpd import publicar
from cpd.fuentes import actualizar, validacion


@pytest.fixture
def lote(tmp_path):
    hoy = dt.date.today()
    fin = (pd.Period(hoy, freq="M") - 1).start_time
    provincias = sorted(validacion.CODIGOS_PROVINCIA)
    meses = pd.date_range(end=fin, periods=12, freq="MS")
    panel = pd.MultiIndex.from_product([provincias, meses], names=["codigo_provincia", "mes"]).to_frame(index=False)
    panel["codigo_ccaa"] = panel["codigo_provincia"].map(lambda c: f"{(int(c) - 1) % 19 + 1:02d}")
    panel["demanda_ccaa_mwh"] = 10.0
    panel["tmedia_mes_c"] = 20.0
    panel["precio_spot_medio_mes_eur_mwh"] = -2.0
    actual = pd.DataFrame({"codigo_provincia": provincias, "mes_referencia_panel": fin})
    carpeta = tmp_path / "curado"
    (carpeta / "modelos").mkdir(parents=True)
    (carpeta / "modelos" / "previsiones_1_anio.json").write_text("{}", encoding="utf-8")
    panel.to_parquet(carpeta / "panel_provincia_mes.parquet")
    actual.to_parquet(carpeta / "provincias_actual.parquet")
    return carpeta, panel, actual


def test_control_impide_publicar_un_panel_sin_demanda_reciente(lote):
    _, panel, actual = lote
    panel.loc[panel["mes"].eq(panel["mes"].max()), "demanda_ccaa_mwh"] = float("nan")
    with pytest.raises(validacion.DatosNoPublicables, match="Cobertura insuficiente"):
        validacion.validar(panel, actual)
    degradado = validacion.validar(panel, actual, permitir_demanda_incompleta=True)
    assert degradado["cobertura_ultimo_mes"]["demanda_ccaa_mwh"] == 0
    assert degradado["avisos"]


def test_actualizacion_sin_fuentes_no_crea_instantanea(monkeypatch, tmp_path):
    monkeypatch.setattr(actualizar, "_tiempo_real", lambda acta: None)
    monkeypatch.setattr(actualizar, "_historia", lambda acta, _: None)
    destino = tmp_path / "nueva"
    assert actualizar.main(["--copia", str(tmp_path / "sin_copia"), "--salida", str(destino)]) == 1
    assert not destino.exists()


def test_publicacion_fallida_conserva_el_puntero_y_la_bbdd(lote, monkeypatch, tmp_path):
    carpeta, panel, _ = lote
    rutas = {"raiz_datos": tmp_path / "publicaciones", "raiz_web": tmp_path / "frontend" / "public" / "data"}
    fecha = str(panel["mes"].max().to_period("M"))
    codigos = sorted(validacion.CODIGOS_PROVINCIA)

    def copiar_previsiones(*, curado, salida):
        salida.write_text(json.dumps({k: {} for k in ("precio", "demanda", "reservas", "temperatura")}), encoding="utf-8")
        return salida

    simulacion = {"mes_referencia": fecha, "provincias": [{"codigo_provincia": x} for x in codigos]}
    monkeypatch.setattr(publicar.runpy, "run_path", lambda _: {
        "simular": lambda *, curado: simulacion,
        "copiar_previsiones": copiar_previsiones,
    })

    primera = publicar.publicar(carpeta, **rutas)
    puntero = rutas["raiz_web"] / "publicacion.json"
    anterior = puntero.read_bytes()
    bd = publicar.ruta_almacen_publicado(**rutas)
    with duckdb.connect(str(bd), read_only=True) as con:
        assert con.execute("SELECT version FROM meta.publicacion").fetchone() == (primera["version"],)
        # Se suma una vez por CCAA, aunque se repita para todas las provincias.
        total = con.execute(
            "SELECT sum(demanda_ccaa_mwh) FROM dw.fact_energia_ccaa_mes WHERE mes = (SELECT max(mes) FROM dw.dim_tiempo)"
        ).fetchone()
        assert total == (190.0,)

    simulacion["provincias"].pop()
    with pytest.raises(ValueError, match="52 códigos"):
        publicar.publicar(carpeta, **rutas)

    assert puntero.read_bytes() == anterior
    assert publicar.ruta_almacen_publicado(**rutas) == bd
    assert list((rutas["raiz_web"] / "versiones").iterdir()) == [
        rutas["raiz_web"] / "versiones" / primera["version"]
    ]

