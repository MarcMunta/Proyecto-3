"""Actualización de la capa de datos por API.

Uso (desde la raíz del proyecto, con el venv activado):

    python -m cpd.fuentes.actualizar            # refresco completo e incremental (historia + tiempo real)
    python -m cpd.fuentes.actualizar --rapido   # solo campos de tiempo real (clima actual, demanda, precios)

Cada fuente se ejecuta de forma aislada: si una falla, se registra, se conserva la última copia
guardada en data/curated/tablas/ (si existe) y el resto sigue. Al final se reconstruyen
``panel_provincia_mes`` y ``provincias_actual`` y se imprime un resumen.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from cpd.fuentes import curado
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


def _guardar(nombre: str, tabla: pd.DataFrame) -> None:
    curado.CARPETA_TABLAS.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(curado.CARPETA_TABLAS / f"{nombre}.csv", index=False, encoding="utf-8")


def _paso(acta: Actualizacion, nombre: str, funcion: Callable[[], pd.DataFrame | dict]) -> None:
    """Ejecuta una fuente aislando sus errores; guarda la tabla si funciona."""
    inicio = time.monotonic()
    try:
        salida = funcion()
        if isinstance(salida, dict):
            tabla = salida.get("tabla", pd.DataFrame())
            if "tabla_aux" in salida:
                tabla = pd.DataFrame(salida["tabla_aux"])
        else:
            tabla = salida
        acta.tablas[nombre] = tabla
        _guardar(nombre, tabla)
        desde, hasta = _rango_fechas(tabla)
        acta.resultados.append(Resultado(nombre, "ok", len(tabla), desde, hasta, segundos=time.monotonic() - inicio))
    except Exception as error:  # una fuente nunca debe parar a las demás
        ruta = curado.CARPETA_TABLAS / f"{nombre}.csv"
        if ruta.exists():
            copia = pd.read_csv(ruta, dtype={"codigo_provincia": str, "codigo_ccaa": str})
            acta.tablas[nombre] = copia
            desde, hasta = _rango_fechas(copia)
            acta.resultados.append(
                Resultado(nombre, "copia_anterior", len(copia), desde, hasta, detalle=str(error)[:200],
                          segundos=time.monotonic() - inicio)
            )
        else:
            acta.resultados.append(Resultado(nombre, "fallo", detalle=str(error)[:200], segundos=time.monotonic() - inicio))


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
        nasa_power,
        natura,
        padron,
        peeringdb,
        provincias,
        red_capacidad,
        ree,
        sepe,
        sismicidad,
        subestaciones,
    )

    _paso(acta, "provincias", lambda: provincias.tabla_provincias())
    poligonos = provincias.cargar_poligonos()
    _paso(acta, "clima_diario", lambda: nasa_power.clima_diario_power(ANIO_INICIO, anio_fin))
    _paso(acta, "free_cooling", lambda: nasa_power.free_cooling_mensual_power(ANIO_INICIO, anio_fin))
    _paso(acta, "reservas_ambito_mensual", lambda: embalses.reservas_mensuales_desde_zip())
    _paso(acta, "estres_hidrico_wri", lambda: agua.estres_hidrico_wri())
    _paso(acta, "ccaa_demanda", lambda: ree.demanda_ccaa_mensual(ANIO_INICIO, anio_fin))
    _paso(acta, "ccaa_generacion", lambda: ree.resumen_renovable(ree.generacion_ccaa_mensual(ANIO_INICIO, anio_fin)))
    _paso(acta, "co2", lambda: ree.co2_nacional_mensual(ANIO_INICIO, anio_fin))
    _paso(acta, "precios_diarios", lambda: ree.precios_diarios_historicos(ANIO_INICIO, anio_fin))
    def poblacion() -> pd.DataFrame:
        try:
            tempus = ine.poblacion_provincias()
        except ErrorFuente:
            tempus = pd.DataFrame()  # sin Tempus3 se usa solo el padrón
        ruta = padron.asegurar_fichero()
        return padron.combinar_poblacion(tempus, padron.leer_padron(ruta))

    _paso(acta, "poblacion", poblacion)
    _paso(acta, "renta", lambda: ine.renta_provincias())
    _paso(acta, "paro", lambda: sepe.paro_provincias_mensual(ANIO_INICIO, anio_fin))

    def conectividad() -> pd.DataFrame:
        fac = peeringdb.asignar_fac(peeringdb.centros_de_datos(), poligonos)
        return peeringdb.resumen_por_provincia(fac, peeringdb.ixp())

    _paso(acta, "conectividad", conectividad)
    _paso(acta, "capacidad_ccaa", lambda: red_capacidad.leer_capacidad(red_capacidad.descargar_ultimo()))
    _paso(acta, "subestaciones", lambda: subestaciones.subestaciones_por_provincia(poligonos))
    _paso(acta, "sismos", lambda: sismicidad.sismos_por_provincia_anual(
        sismicidad.terremotos(ANIO_INICIO, anio_fin), poligonos))
    _paso(acta, "natura", lambda: natura.superficie_natura_por_provincia(poligonos))


def _construir(acta: Actualizacion) -> None:
    """Reconstruye panel y provincias_actual con las tablas disponibles (en memoria o de la última copia)."""
    tablas = dict(acta.tablas)
    for nombre in ("tiempo_real_provincia", "energia_tiempo_real"):
        if nombre not in tablas:
            ruta = curado.CARPETA_TABLAS / f"{nombre}.csv"
            if ruta.exists():
                tablas[nombre] = pd.read_csv(ruta, dtype={"codigo_provincia": str})
    if "provincias" not in tablas:
        from cpd.fuentes import provincias

        tablas["provincias"] = provincias.tabla_provincias()
    tablas.update({k: v for k, v in curado.leer_tablas().items() if k not in tablas})
    if "tiempo_real_provincia" in tablas and "codigo_provincia" not in tablas["tiempo_real_provincia"]:
        tablas.pop("tiempo_real_provincia")
    panel = curado.construir_panel(tablas)
    actual = curado.provincias_actual(panel, tablas)
    rutas = curado.escribir_salidas(panel, actual)
    acta.tablas["_panel"] = panel
    acta.tablas["_actual"] = actual
    acta.resultados.append(
        Resultado("panel_provincia_mes", "ok", len(panel), str(panel["mes"].min())[:10], str(panel["mes"].max())[:10],
                  detalle=f"{panel['codigo_provincia'].nunique()} provincias, {panel.shape[1]} columnas")
    )
    acta.resultados.append(
        Resultado("provincias_actual", "ok", len(actual), detalle=f"{actual['codigo_provincia'].nunique()} provincias, {actual.shape[1]} columnas")
    )
    acta.tablas["_rutas"] = pd.DataFrame([{"salida": k, "ruta": str(v)} for k, v in rutas.items()])


def imprimir_resumen(acta: Actualizacion) -> None:
    """Imprime el resumen de la ejecución: filas, rango, provincias y fuentes fallidas."""
    print("\n=== Resumen de la actualización de datos por API ===")
    for r in acta.resultados:
        rango = f"  {r.desde} -> {r.hasta}" if r.desde or r.hasta else ""
        print(f"[{r.estado:>14}] {r.nombre:<26} filas={r.filas:<8}{rango}  ({r.segundos:.0f} s)")
        if r.detalle and r.estado != "ok":
            print(f"                   motivo: {r.detalle}")
    actual = acta.tablas.get("_actual")
    if actual is not None:
        con_dato = int(actual.drop(columns=["codigo_provincia", "provincia", "codigo_ccaa", "ccaa", "lat_punto", "lon_punto"], errors="ignore").notna().any(axis=1).sum())
        print(f"\nProvincias en provincias_actual: {len(actual)}  (con al menos un dato: {con_dato})")
    fallidas = [r.nombre for r in acta.resultados if r.estado == "fallo"]
    copias = [r.nombre for r in acta.resultados if r.estado == "copia_anterior"]
    print(f"Fuentes fallidas sin copia: {', '.join(fallidas) if fallidas else 'ninguna'}")
    print(f"Fuentes que usan la última copia guardada: {', '.join(copias) if copias else 'ninguna'}")
    rutas = acta.tablas.get("_rutas")
    if rutas is not None:
        print("Salidas:")
        for _, fila in rutas.iterrows():
            print(f"  {fila['salida']}: {fila['ruta']}")


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada. Devuelve 0 si se han generado las salidas, 1 si no."""
    parser = argparse.ArgumentParser(description="Actualiza la capa de datos por API (provincias).")
    parser.add_argument("--rapido", action="store_true", help="Solo campos de tiempo real (clima actual, demanda y precios)")
    parser.add_argument("--anio-fin", type=int, default=dt.date.today().year, help="Último año de historia (por defecto, el actual)")
    args = parser.parse_args(argumentos)
    acta = Actualizacion()
    inicio = time.monotonic()
    _tiempo_real(acta)
    if not args.rapido:
        _historia(acta, args.anio_fin)
    _construir(acta)
    imprimir_resumen(acta)
    print(f"\nTiempo total: {time.monotonic() - inicio:.0f} s")
    return 0 if "_panel" in acta.tablas else 1


if __name__ == "__main__":
    sys.exit(main())
