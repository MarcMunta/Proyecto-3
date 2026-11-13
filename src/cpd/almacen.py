"""
Almacén de datos del proyecto en DuckDB (Data Warehouse local).

Centraliza en un único fichero, data/almacen/p3_cpd.duckdb, todas las tablas que genera la capa de
datos por API (src/cpd/fuentes) para poder consultarlas con SQL, ordenarlas, cruzarlas y verlas en la
interfaz web de DuckDB. El fichero se reconstruye entero cada vez (es reproducible a partir de las
tablas curadas), así que no hay que mantenerlo a mano.

Esquemas:
  fuentes  una tabla por cada fichero de data/curated/tablas/ (clima, energía, paro, sismicidad...)
  modelo   tablas listas para entrenar y predecir: panel_provincia_mes, provincias_actual y sus diccionarios
  dw       modelo en estrella: dim_provincia, dim_tiempo, dim_fuente y fact_provincia_mes
  meta     registro de la carga (qué fichero, cuántas filas, cuándo)

Uso:
  python -m cpd.almacen          reconstruye el almacén
  python -m cpd.almacen --ui     lo reconstruye y abre la interfaz web de DuckDB en el navegador
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from pathlib import Path

import duckdb

from cpd.config import RUTA_RAIZ

CARPETA_CURADO = RUTA_RAIZ / "data" / "curated"
REGISTRO_DESCARGAS = RUTA_RAIZ / "data" / "raw" / "_registro_descargas.csv"
RUTA_ALMACEN = RUTA_RAIZ / "data" / "almacen" / "p3_cpd.duckdb"

# Columnas que son códigos con ceros a la izquierda ("01", "08019"): se leen siempre como texto.
_ES_CODIGO = re.compile(r"^(codigo|cod_|cpro|cmun)|(_ine|_codigo)$", re.IGNORECASE)
# Nombres posibles de la columna temporal del panel (mes).
_COLUMNAS_MES = ("mes", "fecha", "periodo", "fecha_mes")


def _ident(nombre: str) -> str:
    """Convierte un nombre de fichero en un identificador SQL seguro (minúsculas, guiones bajos)."""
    limpio = re.sub(r"[^0-9a-zA-Z_]", "_", nombre).strip("_").lower()
    return limpio if limpio and not limpio[0].isdigit() else f"t_{limpio}"


def _literal(ruta: Path) -> str:
    """Ruta como literal SQL (barras normales y comillas escapadas)."""
    return "'" + ruta.as_posix().replace("'", "''") + "'"


def _lector_csv(ruta: Path) -> str:
    """Expresión read_csv que fuerza a texto las columnas de código para no perder los ceros."""
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        cabecera = next(csv.reader(f), [])
    tipos = {c: "VARCHAR" for c in cabecera if _ES_CODIGO.search(c)}
    if not tipos:
        return f"read_csv({_literal(ruta)}, auto_detect = true, header = true)"
    tipos_sql = ", ".join(f"'{c}': 'VARCHAR'" for c in tipos)
    return f"read_csv({_literal(ruta)}, auto_detect = true, header = true, types = {{{tipos_sql}}})"


def _lector(ruta: Path) -> str:
    return f"read_parquet({_literal(ruta)})" if ruta.suffix == ".parquet" else _lector_csv(ruta)


def _cargar(con: duckdb.DuckDBPyConnection, esquema: str, tabla: str, ruta: Path) -> int:
    con.execute(f"CREATE OR REPLACE TABLE {esquema}.{tabla} AS SELECT * FROM {_lector(ruta)}")
    filas = con.execute(f"SELECT count(*) FROM {esquema}.{tabla}").fetchone()[0]
    con.execute("INSERT INTO meta.carga VALUES (?, ?, ?, ?, ?)",
                [esquema, tabla, str(ruta), filas, dt.datetime.now()])
    return filas


def _preferir_parquet(carpeta: Path, nombre: str) -> Path | None:
    """Devuelve <nombre>.parquet si existe (conserva los tipos), si no <nombre>.csv, si no None."""
    for ext in (".parquet", ".csv"):
        ruta = carpeta / f"{nombre}{ext}"
        if ruta.exists():
            return ruta
    return None


def _columnas(con: duckdb.DuckDBPyConnection, esquema: str, tabla: str) -> list[str]:
    filas = con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
        [esquema, tabla]).fetchall()
    return [f[0] for f in filas]


def _existe(con: duckdb.DuckDBPyConnection, esquema: str, tabla: str) -> bool:
    return bool(_columnas(con, esquema, tabla))


def construir(ruta_almacen: Path = RUTA_ALMACEN, carpeta_curado: Path = CARPETA_CURADO,
              registro: Path = REGISTRO_DESCARGAS) -> dict[str, int]:
    """Reconstruye el almacén DuckDB y devuelve {esquema.tabla: filas}."""
    ruta_almacen.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta_almacen.with_suffix(".tmp.duckdb")
    tmp.unlink(missing_ok=True)
    resumen: dict[str, int] = {}

    # Se construye en un fichero temporal y se renombra al final: si algo falla, el almacén anterior sigue intacto.
    with duckdb.connect(str(tmp)) as con:
        for esquema in ("fuentes", "modelo", "dw", "meta"):
            con.execute(f"CREATE SCHEMA IF NOT EXISTS {esquema}")
        con.execute("CREATE TABLE meta.carga (esquema VARCHAR, tabla VARCHAR, origen VARCHAR, "
                    "filas BIGINT, cargado_en TIMESTAMP)")

        # 1) Tablas fuente: cada fichero de data/curated/tablas/ (Parquet si lo hay, si no CSV)
        carpeta_tablas = carpeta_curado / "tablas"
        nombres = sorted({p.stem for p in carpeta_tablas.glob("*") if p.suffix in (".csv", ".parquet")})
        for nombre in nombres:
            ruta = _preferir_parquet(carpeta_tablas, nombre)
            resumen[f"fuentes.{_ident(nombre)}"] = _cargar(con, "fuentes", _ident(nombre), ruta)

        # 2) Tablas del modelo (entrenamiento y predicción) y sus diccionarios de datos
        for nombre in ("panel_provincia_mes", "provincias_actual",
                       "diccionario_panel_provincia_mes", "diccionario_provincias_actual"):
            ruta = _preferir_parquet(carpeta_curado, nombre)
            if ruta:
                resumen[f"modelo.{nombre}"] = _cargar(con, "modelo", nombre, ruta)

        # 3) Modelo en estrella
        if _existe(con, "fuentes", "provincias"):
            con.execute("CREATE OR REPLACE TABLE dw.dim_provincia AS SELECT * FROM fuentes.provincias")
            resumen["dw.dim_provincia"] = con.execute("SELECT count(*) FROM dw.dim_provincia").fetchone()[0]

        col_mes = None
        if _existe(con, "modelo", "panel_provincia_mes"):
            cols = _columnas(con, "modelo", "panel_provincia_mes")
            col_mes = next((c for c in _COLUMNAS_MES if c in cols), None)
        if col_mes:
            rango = (f"SELECT date_trunc('month', min(CAST({col_mes} AS DATE))) AS ini, "
                     f"date_trunc('month', max(CAST({col_mes} AS DATE))) AS fin FROM modelo.panel_provincia_mes")
        else:
            rango = "SELECT DATE '2015-01-01' AS ini, date_trunc('month', current_date) AS fin"
        con.execute(f"""
            CREATE OR REPLACE TABLE dw.dim_tiempo AS
            WITH r AS ({rango})
            SELECT CAST(mes AS DATE)                    AS mes,
                   year(mes)                            AS anio,
                   quarter(mes)                         AS trimestre,
                   month(mes)                           AS mes_num,
                   strftime(mes, '%Y-%m')               AS etiqueta
            FROM r, generate_series(r.ini, r.fin, INTERVAL 1 MONTH) AS g(mes)
            ORDER BY mes
        """)
        resumen["dw.dim_tiempo"] = con.execute("SELECT count(*) FROM dw.dim_tiempo").fetchone()[0]

        if registro.exists():
            con.execute(f"""
                CREATE OR REPLACE TABLE dw.dim_fuente AS
                SELECT row_number() OVER (ORDER BY fuente, descripcion) AS id_fuente,
                       fuente, descripcion, url,
                       max(CAST(fecha_descarga AS TIMESTAMP)) AS ultima_descarga,
                       count(*) AS descargas
                FROM {_lector_csv(registro)}
                GROUP BY fuente, descripcion, url
            """)
            resumen["dw.dim_fuente"] = con.execute("SELECT count(*) FROM dw.dim_fuente").fetchone()[0]

        if col_mes and _existe(con, "modelo", "panel_provincia_mes"):
            con.execute(f"""
                CREATE OR REPLACE VIEW dw.fact_provincia_mes AS
                SELECT CAST(p.{col_mes} AS DATE) AS mes, p.* EXCLUDE ({col_mes})
                FROM modelo.panel_provincia_mes AS p
            """)

    tmp.replace(ruta_almacen)
    return resumen


def abrir_ui(ruta_almacen: Path = RUTA_ALMACEN) -> None:
    """Abre la interfaz web de DuckDB (http://localhost:4213) sobre el almacén, de solo lectura."""
    con = duckdb.connect(str(ruta_almacen), read_only=True)
    print(con.execute("CALL start_ui()").fetchall()[0][0])
    print("Interfaz abierta en el navegador. Pulsa Enter para cerrarla.")
    try:
        input()
    finally:
        con.execute("CALL stop_ui_server()")
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Construye el almacén DuckDB del proyecto.")
    parser.add_argument("--ui", action="store_true", help="abrir la interfaz web de DuckDB al terminar")
    args = parser.parse_args()

    resumen = construir()
    ancho = max(len(k) for k in resumen) if resumen else 10
    for tabla, filas in resumen.items():
        print(f"  {tabla:<{ancho}}  {filas:>10,} filas")
    print(f"Almacén: {RUTA_ALMACEN.relative_to(RUTA_RAIZ)}")
    if args.ui:
        abrir_ui()


if __name__ == "__main__":
    main()
