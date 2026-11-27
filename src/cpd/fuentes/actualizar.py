"""Actualización de la capa de datos por API.

Uso (desde la raíz del proyecto, con el venv activado):

    python -m cpd.fuentes.actualizar            # refresco completo e incremental (historia + tiempo real)
    python -m cpd.fuentes.actualizar --rapido   # solo campos de tiempo real (clima actual, demanda, precios)

Cada fuente se ejecuta de forma aislada. Las tablas, el panel y la ficha se guardan juntos
en una nueva carpeta solo tras validar el conjunto. La copia anterior sirve de respaldo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from typing import Callable

import pandas as pd

from cpd.fuentes import curado, validacion
from cpd.fuentes.http import ErrorFuente

ANIO_INICIO: int = 2015


@dataclass
class Resultado:
    """Resumen de una fuente o tabla tras la actualización."""

    nombre: str
    estado: str  # "ok" | "fallo" | "copia_anterior" | "omitida"
    filas: int = 0
    desde: str = ""
    hasta: str = ""
    detalle: str = ""
    segundos: float = 0.0


@dataclass
class Actualizacion:
    """Estado acumulado de una ejecución."""

    tablas: dict[str, pd.DataFrame] = field(default_factory=dict)
    resultados: list[Resultado] = field(default_factory=list)
    carpeta_copia: Path = curado.CARPETA_CURADO


def _rango_fechas(tabla: pd.DataFrame) -> tuple[str, str]:
    """Primera y última fecha/mes/año de una tabla (texto), para el resumen."""
    for columna in ("fecha", "mes", "anio"):
        if columna in tabla.columns and not tabla.empty:
            serie = tabla[columna].dropna()
            if serie.empty:
                return "", ""
            if columna == "anio":
                return str(int(serie.min())), str(int(serie.max()))
            valores = pd.to_datetime(serie, errors="coerce").dropna()
            return (valores.min().strftime("%Y-%m-%d"), valores.max().strftime("%Y-%m-%d")) if not valores.empty else ("", "")
    return "", ""


def _leer_copia(ruta: Path) -> pd.DataFrame:
    """Lee una copia conservando los códigos territoriales."""
    tabla = pd.read_csv(ruta, dtype={"codigo_provincia": str, "codigo_ccaa": str})
    if tabla.empty:
        raise ValueError("La copia guardada está vacía")
    return tabla


def _paso(acta: Actualizacion, nombre: str, funcion: Callable[[], pd.DataFrame | dict]) -> None:
    """Ejecuta una fuente, con respaldo en la última copia legible."""
    inicio = time.monotonic()
    try:
        salida = funcion()
        tabla = salida.get("tabla_aux", salida.get("tabla")) if isinstance(salida, dict) else salida
        if not isinstance(tabla, pd.DataFrame) or tabla.empty:
            raise ErrorFuente("La fuente no devolvió filas")
        estado, detalle = "ok", ""
    except Exception as error:  # cada fuente debe poder fallar sin detener al resto
        detalle = str(error)[:200]
        ruta = acta.carpeta_copia / "tablas" / f"{nombre}.csv"
        try:
            tabla = _leer_copia(ruta)
        except (OSError, ValueError) as error_copia:
            estado_copia = "sin copia guardada" if isinstance(error_copia, FileNotFoundError) else "copia ilegible"
            acta.resultados.append(Resultado(nombre, "fallo", detalle=f"{detalle}. {estado_copia}",
                                             segundos=time.monotonic() - inicio))
            return
        estado = "copia_anterior"
    acta.tablas[nombre] = tabla
    desde, hasta = _rango_fechas(tabla)
    acta.resultados.append(Resultado(nombre, estado, len(tabla), desde, hasta, detalle,
                                     time.monotonic() - inicio))


def _tiempo_real(acta: Actualizacion) -> None:
    """Campos de tiempo real: clima actual por provincia y energía nacional (demanda, precios)."""
    from cpd.fuentes import meteo, omie, ree

    def clima_y_prevision() -> pd.DataFrame:
        actual = meteo.clima_actual()
        previsto = meteo.prevision_corta(7)
        return actual.merge(previsto, on="codigo_provincia", how="left")

    _paso(acta, "clima_actual", lambda: clima_y_prevision().assign(fecha=dt.date.today().isoformat()))
    _paso(acta, "tiempo_real_provincia", lambda: acta.tablas.get("clima_actual", pd.DataFrame()).drop(columns=["fecha"], errors="ignore"))

    def energia() -> pd.DataFrame:
        demanda = ree.demanda_tiempo_real()
        spot = ree.precios_recientes()
        spot_actual = None
        if not spot.empty:
            pasado = spot[spot["momento"] <= pd.Timestamp.now()]
            spot_actual = float(pasado["precio_spot_eur_mwh"].iloc[-1]) if not pasado.empty else None
        manana = omie.precios_hoy_y_manana()["manana"]
        manana_medio = float(manana["precio_es_eur_mwh"].mean()) if manana is not None else None
        return pd.DataFrame(
            [
                {
                    "momento_consulta": pd.Timestamp.now().isoformat(timespec="minutes"),
                    "demanda_tiempo_real_mw": demanda["demanda_mw"],
                    "momento_demanda": demanda["momento"],
                    "precio_spot_actual_eur_mwh": spot_actual,
                    "precio_spot_manana_medio_eur_mwh": manana_medio,
                }
            ]
        )

    _paso(acta, "energia_tiempo_real", energia)


def _historia(acta: Actualizacion, anio_fin: int) -> None:
    """Series históricas de todas las fuentes (incrementales: los periodos cerrados se leen de caché)."""
    from cpd.fuentes import (
        agua,
        embalses,
        ine,
        ine_tio,
        nasa_power,
        natura,
        padron,
        peeringdb,
        provincias,
        red_capacidad,
        ree,
        sepe,
        sismicidad,
        norma_sismica,
        suelo,
        subestaciones,
    )

    _paso(acta, "provincias", lambda: provincias.tabla_provincias())
    poligonos = None

    def geometria():
        """Carga los límites al necesitarlos y reutiliza el resultado."""
        nonlocal poligonos
        if poligonos is None:
            poligonos = provincias.cargar_poligonos()
        return poligonos
    _paso(acta, "clima_diario", lambda: nasa_power.clima_diario_power(ANIO_INICIO, anio_fin))
    _paso(acta, "free_cooling", lambda: nasa_power.free_cooling_mensual_power(ANIO_INICIO, anio_fin))
    _paso(acta, "clima_mensual_largo", lambda: nasa_power.temperatura_mensual_larga())
    _paso(acta, "reservas_ambito_mensual", lambda: embalses.reservas_mensuales_desde_zip())
    _paso(acta, "estres_hidrico_wri", lambda: agua.estres_hidrico_wri())
    _paso(acta, "ccaa_demanda", lambda: ree.demanda_ccaa_mensual(ANIO_INICIO, anio_fin))
    generacion: dict[str, pd.DataFrame] = {}  # una sola descarga para las dos tablas

    def _generacion() -> pd.DataFrame:
        if "tabla" not in generacion:
            generacion["tabla"] = ree.generacion_ccaa_mensual(ANIO_INICIO, anio_fin)
        return generacion["tabla"]

    _paso(acta, "ccaa_generacion", lambda: ree.resumen_renovable(_generacion()))
    _paso(acta, "ccaa_generacion_tecnologia", lambda: ree.generacion_por_grupo(_generacion()))
    _paso(acta, "generacion_nacional_detalle", lambda: ree.generacion_nacional_detalle(_generacion()))
    _paso(acta, "co2", lambda: ree.co2_nacional_mensual(ANIO_INICIO, anio_fin))
    _paso(acta, "precios_diarios", lambda: ree.precios_diarios_historicos(ANIO_INICIO, anio_fin))
    from cpd.fuentes import mibgas

    _paso(acta, "gas_diario", lambda: mibgas.gas_diario(mibgas.ANIO_INICIO, anio_fin))
    _paso(acta, "gas_futuros", lambda: mibgas.gas_futuros(mibgas.ANIO_INICIO, anio_fin))
    def poblacion() -> pd.DataFrame:
        try:
            tempus = ine.poblacion_provincias()
        except ErrorFuente:
            tempus = pd.DataFrame()  # sin Tempus3 se usa solo el padrón
        ruta = padron.asegurar_fichero()
        return padron.combinar_poblacion(tempus, padron.leer_padron(ruta))

    _paso(acta, "poblacion", poblacion)
    _paso(acta, "renta", lambda: ine.renta_provincias())
    _paso(acta, "agua_ccaa", lambda: ine.agua_ccaa())
    _paso(acta, "pib_provincia", lambda: ine.pib_provincias())
    _paso(acta, "sociedades_provincia", lambda: ine.sociedades_provincias())
    tio: dict[str, pd.DataFrame] = {}

    def _tio() -> dict[str, pd.DataFrame]:
        if not tio:
            tio.update(ine_tio.leer_tio(ine_tio.descargar()))
        return tio

    _paso(acta, "tio_ramas", lambda: _tio()["ramas"])
    _paso(acta, "tio_leontief_interior", lambda: _tio()["leontief"].rename_axis("codigo").reset_index())
    _paso(acta, "paro", lambda: sepe.paro_provincias_mensual(ANIO_INICIO, anio_fin))

    def conectividad() -> pd.DataFrame:
        fac = peeringdb.asignar_fac(peeringdb.centros_de_datos(), geometria())
        return peeringdb.resumen_por_provincia(fac, peeringdb.ixp())

    _paso(acta, "conectividad", conectividad)
    _paso(acta, "capacidad_ccaa", lambda: red_capacidad.leer_capacidad(red_capacidad.descargar_ultimo()))
    _paso(acta, "subestaciones", lambda: subestaciones.subestaciones_por_provincia(geometria()))
    _paso(acta, "sismos", lambda: sismicidad.sismos_por_provincia_anual(
        sismicidad.terremotos(ANIO_INICIO, anio_fin), geometria()))
    _paso(acta, "natura", lambda: natura.superficie_natura_por_provincia(geometria()))
    _paso(acta, "suelo_provincia", lambda: suelo.leer_precio_suelo(suelo.descargar()))
    _paso(acta, "peligrosidad_sismica", lambda: norma_sismica.leer_peligrosidad(norma_sismica.descargar()))


def _construir(acta: Actualizacion, carpeta: Path, *, permitir_demanda_incompleta: bool) -> None:
    """Valida la instantánea antes de guardarla en una carpeta nueva."""
    tablas = dict(acta.tablas)
    nombres_revisados = {r.nombre for r in acta.resultados}
    for ruta in sorted((acta.carpeta_copia / "tablas").glob("*.csv")):
        if ruta.stem in nombres_revisados:
            continue
        try:
            tabla = _leer_copia(ruta)
        except (OSError, ValueError) as error:
            acta.resultados.append(Resultado(ruta.stem, "fallo", detalle=f"Copia ilegible ({type(error).__name__})"))
            continue
        tablas[ruta.stem] = tabla
        desde, hasta = _rango_fechas(tabla)
        acta.resultados.append(Resultado(ruta.stem, "copia_anterior", len(tabla), desde, hasta))
    if "provincias" not in tablas:
        from cpd.fuentes import provincias

        tablas["provincias"] = provincias.tabla_provincias()
    if "tiempo_real_provincia" in tablas and "codigo_provincia" not in tablas["tiempo_real_provincia"]:
        tablas.pop("tiempo_real_provincia")
    panel = curado.construir_panel(tablas)
    actual = curado.provincias_actual(panel, tablas)
    revision = validacion.validar(panel, actual, permitir_demanda_incompleta=permitir_demanda_incompleta)

    carpeta.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".curado-", dir=carpeta.parent) as temporal:
        preparado = Path(temporal) / "curado"
        origen = preparado / "tablas"
        origen.mkdir(parents=True)
        for nombre, tabla in tablas.items():
            tabla.to_csv(origen / f"{nombre}.csv", index=False, encoding="utf-8")
        curado.escribir_salidas(panel, actual, carpeta=preparado, calidad_demanda=curado.registro_calidad_demanda(tablas))
        metadata = {
            "generado_en": dt.datetime.now(dt.timezone.utc).isoformat(),
            **revision,
            "fuentes": [{k: v for k, v in asdict(r).items() if k != "detalle"} for r in acta.resultados],
        }
        (preparado / "actualizacion.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        preparado.rename(carpeta)
    for aviso in revision["avisos"]:
        print(f"Aviso: {aviso}")
    print(f"Instantánea curada: {carpeta}")


def imprimir_resumen(acta: Actualizacion) -> None:
    """Imprime el resumen de la ejecución: filas, rango, provincias y fuentes fallidas."""
    print("\n=== Resumen de la actualización de datos por API ===")
    for r in acta.resultados:
        rango = f"  {r.desde} -> {r.hasta}" if r.desde or r.hasta else ""
        print(f"[{r.estado:>14}] {r.nombre:<26} filas={r.filas:<8}{rango}  ({r.segundos:.0f} s)")
        if r.detalle and r.estado != "ok":
            print(f"                   motivo: {r.detalle}")
    fallidas = [r.nombre for r in acta.resultados if r.estado == "fallo"]
    copias = [r.nombre for r in acta.resultados if r.estado == "copia_anterior"]
    print(f"Fuentes fallidas sin copia: {', '.join(fallidas) if fallidas else 'ninguna'}")
    print(f"Fuentes que usan la última copia guardada: {', '.join(copias) if copias else 'ninguna'}")


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada. Devuelve 0 si se han generado las salidas, 1 si no."""
    parser = argparse.ArgumentParser(description="Actualiza la capa de datos por API (provincias).")
    parser.add_argument("--rapido", action="store_true", help="Solo campos de tiempo real (clima actual, demanda y precios)")
    parser.add_argument("--anio-fin", type=int, default=dt.date.today().year, help="Último año de historia (por defecto, el actual)")
    parser.add_argument("--copia", type=Path, default=curado.CARPETA_CURADO, help="instantánea anterior de respaldo")
    parser.add_argument("--salida", type=Path, help="ruta nueva de la instantánea curada")
    parser.add_argument("--permitir-demanda-incompleta", action="store_true",
                        help="conserva la instantánea en modo degradado si falta demanda reciente")
    args = parser.parse_args(argumentos)
    carpeta = args.salida or curado.CARPETA_CURADO.parent / "actualizaciones" / (
        f"{dt.date.today().isoformat()}-{uuid4().hex[:8]}"
    )
    if carpeta.exists():
        parser.error("--salida debe ser una ruta nueva")
    acta = Actualizacion(carpeta_copia=args.copia)
    inicio = time.monotonic()
    _tiempo_real(acta)
    if not args.rapido:
        _historia(acta, args.anio_fin)
    try:
        _construir(acta, carpeta, permitir_demanda_incompleta=args.permitir_demanda_incompleta)
    except (ValueError, KeyError, OSError) as error:
        imprimir_resumen(acta)
        print(f"Instantánea rechazada: {error}", file=sys.stderr)
        return 1
    imprimir_resumen(acta)
    print(f"\nTiempo total: {time.monotonic() - inicio:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
