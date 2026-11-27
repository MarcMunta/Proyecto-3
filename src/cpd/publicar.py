"""Construye y activa una versión local coherente de DuckDB y del mapa."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from uuid import uuid4

import duckdb
import pandas as pd

from cpd import almacen
from cpd.config import RUTA_RAIZ, RUTA_RAW
from cpd.fuentes import territorio, validacion

RUTA_PUBLICACIONES = RUTA_RAIZ / "data" / "publicaciones"
RUTA_WEB = RUTA_RAIZ / "frontend" / "public" / "data"
VERSION_SEGURA = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
ESQUEMA = 1


def _leer_json(ruta: Path) -> dict:
    with ruta.open(encoding="utf-8") as fichero:
        datos = json.load(fichero)
    if not isinstance(datos, dict):
        raise ValueError(f"Se esperaba un objeto JSON en {ruta.name}")
    return datos


def _json(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"


def _activar(puntero: Path, datos: dict) -> None:
    """El puntero es el único fichero mutable de una publicación."""
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=puntero.parent, delete=False) as fichero:
        temporal = Path(fichero.name)
        try:
            fichero.write(_json(datos))
            fichero.flush()
            os.fsync(fichero.fileno())
        except BaseException:
            fichero.close()
            temporal.unlink(missing_ok=True)
            raise
    try:
        temporal.replace(puntero)
    finally:
        temporal.unlink(missing_ok=True)


def _sha256(ruta: Path) -> str:
    with ruta.open("rb") as fichero:
        return hashlib.file_digest(fichero, "sha256").hexdigest()


def _hashes(carpeta: Path) -> dict[str, str]:
    hashes = {}
    for ruta in sorted(carpeta.rglob("*")):
        if ruta.is_file():
            hashes[ruta.relative_to(carpeta).as_posix()] = _sha256(ruta)
    return hashes


def _regenerar(espacio: Path, curado: Path) -> None:
    """Ejecuta el pipeline sin sobrescribir artefactos, informes ni modelos del proyecto."""
    shutil.copytree(RUTA_RAIZ / "src", espacio / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    shutil.copytree(RUTA_RAIZ / "config", espacio / "config")
    shutil.copytree(RUTA_RAIZ / "data" / "clean", espacio / "data" / "clean", dirs_exist_ok=True)
    origen = dict(os.environ, PYTHONPATH=str(espacio / "src"), MPLCONFIGDIR=str(espacio / ".matplotlib"))
    if curado != espacio / "data" / "curated":
        raise ValueError("La regeneración necesita la carpeta curada de la publicación")
    subprocess.run([sys.executable, "-B", "-m", "cpd.modelos", "--sin-eda"],
                   cwd=espacio, env=origen, check=True)


def ruta_almacen_publicado(raiz_datos: Path = RUTA_PUBLICACIONES, raiz_web: Path = RUTA_WEB) -> Path:
    """Resuelve la BBDD referenciada por el mismo puntero que utiliza el frontend."""
    datos = _leer_json(raiz_web / "publicacion.json")
    version = datos.get("version")
    if datos.get("schema_version") != ESQUEMA or not isinstance(version, str) or not VERSION_SEGURA.fullmatch(version):
        raise ValueError("Puntero de publicación inválido")
    ruta = raiz_datos / version / "p3_cpd.duckdb"
    if not ruta.is_file():
        raise FileNotFoundError(f"Falta la base de datos de la versión {version}")
    return ruta


def _cargar_territorio(con: duckdb.DuckDBPyConnection, raw: Path | None) -> tuple[dict, dict]:
    """Añade fuentes municipales y nudos con granularidades distintas y sin uniones inferidas."""
    filas, huellas = {}, {}
    if raw is None:
        return filas, huellas

    rutas = (
        raw / "municipios" / "ine_diccionario_municipios_2026.xlsx",
        raw / "municipios" / "gisco_lau_2024_atributos.csv",
        raw / "demografia" / "ine_padron_municipios_29005.csv",
    )
    if all(ruta.is_file() for ruta in rutas):
        huellas.update({ruta.relative_to(raw).as_posix(): _sha256(ruta) for ruta in rutas})
        municipios = territorio.construir_contexto_municipal(*rutas)
        if municipios.empty or not municipios["codigo_municipio"].str.fullmatch(r"[0-9]{5}").fillna(False).all():
            raise ValueError("Códigos INE municipales ausentes o inválidos")
        con.register("municipios", municipios)
        con.execute("CREATE TABLE dw.dim_municipio AS SELECT * FROM municipios")
        con.execute("ALTER TABLE dw.dim_municipio ADD PRIMARY KEY (codigo_municipio)")
        con.unregister("municipios")
        filas["dw.dim_municipio"] = len(municipios)
    candidatas = sorted((raw / "energia").glob("ree_capacidad_acceso_demanda_*_GRT_demanda.csv"))
    if candidatas:
        ruta = candidatas[-1]
        huellas[ruta.relative_to(raw).as_posix()] = _sha256(ruta)
        nudos = territorio.leer_nudos_ree_por_ccaa(ruta)
        if nudos.empty:
            raise ValueError("El fichero REE no contiene nudos reconocidos")
        con.register("nudos", nudos)
        con.execute("CREATE TABLE dw.fact_capacidad_nudo AS SELECT * FROM nudos")
        con.unregister("nudos")
        filas["dw.fact_capacidad_nudo"] = len(nudos)
    if any(_sha256(raw / ruta) != digest for ruta, digest in huellas.items()):
        raise ValueError("Los ficheros territoriales cambiaron durante la publicación")
    return filas, huellas


def publicar(
    carpeta_curado: Path, *, raiz_datos: Path = RUTA_PUBLICACIONES, raiz_web: Path = RUTA_WEB,
    reentrenar: bool = False, permitir_historico: bool = False, permitir_demanda_incompleta: bool = False,
    raiz_raw: Path | None = None,
) -> dict:
    """Valida, genera y activa el lote en el mismo sistema de archivos de cada destino."""
    carpeta_curado = carpeta_curado.resolve()
    raiz_datos = raiz_datos.resolve()
    raiz_web = raiz_web.resolve()
    if not carpeta_curado.is_dir():
        raise FileNotFoundError(f"Falta la carpeta curada: {carpeta_curado}")

    ahora = dt.datetime.now(dt.timezone.utc)
    version = f"{ahora:%Y%m%dT%H%M%SZ}-{uuid4().hex[:12]}"
    raiz_datos.mkdir(parents=True, exist_ok=True)
    versiones_web = raiz_web / "versiones"
    versiones_web.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".preparar-", dir=raiz_datos) as temp_local, \
         TemporaryDirectory(prefix=".preparar-cpd-", dir=raiz_web.parent.parent) as temp_web:
        espacio = Path(temp_local) / "proyecto"
        curado = espacio / "data" / "curated"
        preparados = Path(temp_local) / "version"
        preparados.mkdir()
        web = Path(temp_web) / "version"
        web.mkdir()

        hashes_origen = _hashes(carpeta_curado)
        shutil.copytree(carpeta_curado, curado, ignore=shutil.ignore_patterns("modelos") if reentrenar else None)
        esperados = {ruta: sha for ruta, sha in hashes_origen.items()
                     if not reentrenar or not ruta.startswith("modelos/")}
        if _hashes(curado) != esperados:
            raise ValueError("Los datos de origen cambiaron durante la copia")
        panel = pd.read_parquet(curado / "panel_provincia_mes.parquet")
        actual = pd.read_parquet(curado / "provincias_actual.parquet")
        calidad = validacion.validar(panel, actual, permitir_historico=permitir_historico,
                                     permitir_demanda_incompleta=permitir_demanda_incompleta)

        if reentrenar:
            _regenerar(espacio, curado)
        elif not (curado / "modelos" / "previsiones_1_anio.json").is_file():
            raise ValueError("La instantánea carece de previsiones. Ejecuta con --reentrenar")

        ruta_db = preparados / "p3_cpd.duckdb"
        tablas = almacen.construir(ruta_db, curado)
        with duckdb.connect(str(ruta_db)) as con:
            tablas_territorio, fuentes_territorio = _cargar_territorio(con, raiz_raw)
            tablas.update(tablas_territorio)
            con.execute("CREATE TABLE meta.publicacion (version VARCHAR, fecha_panel VARCHAR, generado_en TIMESTAMPTZ)")
            con.execute("INSERT INTO meta.publicacion VALUES (?, ?, ?)", [version, calidad["fecha_panel"], ahora])
            n, claves = con.execute(
                "SELECT count(*), count(DISTINCT (codigo_provincia, mes)) FROM dw.fact_provincia_mes"
            ).fetchone()
            if n != claves or n != len(panel):
                raise ValueError("El almacén debe conservar las claves y filas del panel validado")

        exportador = runpy.run_path(str(RUTA_RAIZ / "frontend" / "scripts" / "simular_provincias.py"))
        simulacion = exportador["simular"](curado=curado)
        codigos = [p["codigo_provincia"] for p in simulacion["provincias"]]
        if len(codigos) != 52 or set(codigos) != validacion.CODIGOS_PROVINCIA:
            raise ValueError("La simulación debe contener los 52 códigos de provincia una sola vez")
        if simulacion["mes_referencia"] != calidad["fecha_panel"]:
            raise ValueError("La simulación está desalineada del mes del panel")
        archivo_prev = web / "previsiones.json"
        if exportador["copiar_previsiones"](curado=curado, salida=archivo_prev) is None:
            raise ValueError("Falta el artefacto de previsiones de la publicación")
        previsiones = _leer_json(archivo_prev)
        if not {"precio", "demanda", "reservas", "temperatura"}.issubset(previsiones):
            raise ValueError("Las previsiones carecen de sus bloques principales")
        cabecera = {"schema_version": ESQUEMA, "version": version}
        (web / "provincias_simuladas.json").write_text(_json({**simulacion, **cabecera}), encoding="utf-8")
        archivo_prev.write_text(_json({**previsiones, **cabecera}), encoding="utf-8")

        origen_modelos = "regenerados" if reentrenar else "importados"
        avisos = list(calidad["avisos"])
        if not reentrenar:
            avisos.append("Previsiones importadas de la instantánea. La fecha del panel y la del modelo pueden diferir.")
        puntero = {**cabecera, "generado_en": ahora.isoformat(timespec="seconds"), "origen_modelos": origen_modelos,
                   "fecha_panel": calidad["fecha_panel"], "avisos": avisos}
        if (curado / "actualizacion.json").is_file():
            (preparados / "actualizacion.json").write_text(_json(_leer_json(curado / "actualizacion.json")), encoding="utf-8")
        if reentrenar:
            # El resto del entorno de ejecución es temporal. Conservamos la evidencia y los artefactos regenerados.
            shutil.copytree(curado / "modelos", preparados / "resultados_modelos")
            for nombre in ("models", "docs"):
                ruta = espacio / nombre
                if ruta.is_dir():
                    shutil.copytree(ruta, preparados / nombre)
        manifiesto = {**puntero, **calidad, "avisos": avisos, "tablas": tablas, "entradas_sha256": esperados,
                      "entradas_territorio_sha256": fuentes_territorio, "version_web_sha256": _hashes(web), "version_local_sha256": _hashes(preparados)}
        (preparados / "manifiesto.json").write_text(_json(manifiesto), encoding="utf-8")
        preparados.rename(raiz_datos / version)
        web.rename(versiones_web / version)
        _activar(raiz_web / "publicacion.json", puntero)
    return puntero


def main(argumentos: list[str] | None = None) -> int:
    """Ejecuta una publicación local y señala los rechazos al llamante."""
    parser = argparse.ArgumentParser(description="Construye y activa una publicación local CPD")
    parser.add_argument("--curado", type=Path, default=almacen.CARPETA_CURADO)
    parser.add_argument("--raw", type=Path, default=RUTA_RAW, help="fuentes locales para el contexto territorial")
    parser.add_argument("--actualizar", action="store_true", help="obtiene una nueva instantánea antes de regenerar y publicar")
    parser.add_argument("--reentrenar", action="store_true", help="regenera los modelos en un entorno aislado")
    parser.add_argument("--permitir-historico", action="store_true", help="acepta un panel archivado")
    parser.add_argument("--permitir-demanda-incompleta", action="store_true",
                        help="activa en modo degradado si la cobertura de demanda reciente es insuficiente")
    args = parser.parse_args(argumentos)
    try:
        if args.actualizar:
            from cpd.fuentes import actualizar

            # Si la actualización o el entrenamiento fallan, el puntero anterior sigue sirviendo.
            with TemporaryDirectory(prefix="cpd-candidato-") as temporal:
                carpeta = Path(temporal) / "curado"
                opciones = ["--copia", str(args.curado), "--salida", str(carpeta)]
                if args.permitir_demanda_incompleta:
                    opciones.append("--permitir-demanda-incompleta")
                if actualizar.main(opciones):
                    return 1
                datos = publicar(carpeta, reentrenar=True,
                                 permitir_demanda_incompleta=args.permitir_demanda_incompleta, raiz_raw=args.raw)
        else:
            datos = publicar(args.curado, reentrenar=args.reentrenar, permitir_historico=args.permitir_historico,
                             permitir_demanda_incompleta=args.permitir_demanda_incompleta, raiz_raw=args.raw)
    except (ValueError, KeyError, OSError, duckdb.Error, subprocess.CalledProcessError) as error:
        print(f"Publicación rechazada: {error}", file=sys.stderr)
        return 1
    print(f"Versión activa {datos['version']} | panel {datos['fecha_panel']} | modelos {datos['origen_modelos']}")
    for aviso in datos["avisos"]:
        print(f"Aviso: {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

