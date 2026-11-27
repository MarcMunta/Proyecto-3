"""Pruebas del piloto municipal con ficheros sintéticos, nunca datos raw reales."""

from pathlib import Path

import pandas as pd
import pytest

from cpd.fuentes import territorio


def _escribir_fuentes_sinteticas(carpeta: Path) -> tuple[Path, Path, Path]:
    """Crea fixtures SINTÉTICOS con la forma de INE y GISCO."""
    diccionario = carpeta / "ine_diccionario_sintetico.xlsx"
    with pd.ExcelWriter(diccionario) as escritor:
        pd.DataFrame([["Relación SINTÉTICA de municipios"]]).to_excel(escritor, index=False, header=False)
        pd.DataFrame(
            [["16", "01", "001", "4", "Alegría"], ["16", "01", "002", "9", "Amurrio"]],
            columns=["CODAUTO", "CPRO", "CMUN", "DC", "NOMBRE"],
        ).to_excel(escritor, index=False, startrow=1)
    gisco = carpeta / "gisco_sintetico.csv"
    gisco.write_text(
        "GISCO_ID,CNTR_CODE,LAU_NAME,POP_2024,POP_DENS_2024,AREA_KM2,YEAR\n"
        "ES_01001,ES,Alegria,0,0,10.0,2024\nES_01002,ES,Amurrio,0,0,20.0,2024\n"
        "FR_01001,FR,No unir,1,1,5.0,2024\n",
        encoding="utf-8",
    )
    padron = carpeta / "padron_sintetico.csv"
    padron.write_text(
        "Municipios;Sexo;Periodo;Total\n01001 Alegría;Total;2025;1.000\n"
        "01001 Alegría;Total;2024;900\n01002 Amurrio;Total;2025;500\n"
        "01002 Amurrio;Hombres;2025;250\n",
        encoding="utf-8",
    )
    return diccionario, gisco, padron


def test_contexto_municipal_usa_codigos_oficiales_y_calcula_densidad(tmp_path):
    diccionario, gisco, padron = _escribir_fuentes_sinteticas(tmp_path)
    tabla = territorio.construir_contexto_municipal(diccionario, gisco, padron)
    alegria = tabla.set_index("codigo_municipio").loc["01001"]
    assert list(tabla["codigo_municipio"]) == ["01001", "01002"]
    assert alegria["codigo_provincia"] == "01"
    assert alegria["poblacion_habitantes"] == 1000
    assert alegria["anio_poblacion"] == 2025
    assert alegria["superficie_km2"] == 10.0
    assert alegria["densidad_hab_km2"] == 100.0
    assert alegria["fuente_poblacion"] == territorio.FUENTE_INE_PADRON


def test_padron_permite_exigir_un_anio_y_falla_si_no_existe(tmp_path):
    _, _, padron = _escribir_fuentes_sinteticas(tmp_path)
    tabla = territorio.leer_padron_municipal(padron, anio=2024)
    assert tabla["codigo_municipio"].tolist() == ["01001"]
    with pytest.raises(ValueError, match="2023"):
        territorio.leer_padron_municipal(padron, anio=2023)


def test_nudos_ree_se_mantienen_por_ccaa_sin_enlace_municipal(tmp_path):
    ruta = tmp_path / "ree_sintetico.csv"
    ruta.write_text(
        "Nombre y tensión del nudo;Código de subestación;Comunidad Autónoma;SITUACIÓN NUDO CAPACIDAD DE ACCESO OTORGADA;SITUACIÓN NUDO CAPACIDAD DE ACCESO EN CURSO Y PENDIENTE DE RESOLVER;CAPACIDAD DE ACCESO DISPONIBLE PARA SOLICITUDES CRITERIO GENERAL RDT\n"
        ";;;Capacidad de acceso otorgada demanda RdT;Capacidad de acceso solicitada en curso y pendiente resolver demanda RdT;DEMANDA\n"
        "NUDO A 400;123;Aragón;40;10;80\n",
        encoding="utf-8",
    )
    tabla = territorio.leer_nudos_ree_por_ccaa(ruta)
    fila = tabla.iloc[0]
    assert fila["codigo_ccaa"] == "02"
    assert fila["nudo_ree"] == "NUDO A 400"
    assert fila["capacidad_demanda_rdt_disponible_mw"] == 80
    assert "codigo_municipio" not in tabla.columns
    assert fila["archivo_origen"] == "ree_sintetico.csv"
