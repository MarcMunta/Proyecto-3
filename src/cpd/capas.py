"""
Arquitectura de datos por capas (Bronze / Silver / Gold) y capa Gold para el dashboard.

Aplica la clase 27/11/2026 «Data Mining & Data Engineering with Python»:

- **Bronze** = lo que pasó: `data/raw/` (descargas originales y caché de las APIs en `data/raw/api/`), sin tocar (R-2).
- **Silver** = lo que es correcto: `data/clean/` y `data/curated/tablas/` (limpio, tipado, validado, sin duplicados).
- **Gold** = lo que es útil: `data/curated/` (panel provincia-mes, provincias actual, salidas de modelos) y el
  almacén DuckDB (`dw`, `gold`), listo para analizar y para el producto.

Este módulo:
1. Guarda cada tabla Silver también en Parquet (columnar, binario, comprimido y con tipos), solo si el CSV ha
   cambiado desde la última conversión (no se repite trabajo ya hecho).
2. Calcula el *watermark* de cada tabla (última fecha con dato) y lo añade a un historial (trazabilidad).
3. Mide CSV frente a Parquet y pandas frente a DuckDB sobre la misma tabla.
4. Construye el esquema `gold` del almacén con tablas ya agregadas para el dashboard de Streamlit, que solo
   las lee: el producto nunca hace ingeniería de datos.

Se ejecuta desde `cpd.almacen.construir()` (`python -m cpd.almacen`).
"""
from __future__ import annotations

import csv
import datetime as dt
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import duckdb
import pandas as pd

# Nombres posibles de la columna temporal de una tabla, por orden de preferencia.
COLUMNAS_TIEMPO: tuple[str, ...] = ("fecha", "mes", "momento", "fecha_mes", "periodo", "semana", "anio")
# Fichero de historial de watermarks (una fila por tabla y construcción del almacén).
NOMBRE_HISTORIAL: str = "historial_watermarks.csv"


@dataclass(frozen=True)
class Capa:
    """Una capa del lago de datos."""

    nombre: str
    rutas: tuple[str, ...]
    que_es: str
    formatos: str


CAPAS: tuple[Capa, ...] = (
    Capa("bronze", ("data/raw",),
         "Lo que pasó: descargas originales y respuestas de las APIs tal cual llegaron (JSON, CSV, XLSX, ZIP). "
         "Inmutable (R-2); permite reconstruir todo lo demás.", "JSON, CSV, XLSX, ZIP, PDF"),
    Capa("silver", ("data/clean", "data/curated/tablas"),
         "Lo que es correcto: tablas limpias, tipadas, validadas y sin duplicados, una por fuente.",
         "CSV + Parquet"),
    Capa("gold", ("data/curated", "data/almacen"),
         "Lo que es útil: panel provincia-mes, provincias actual, salidas de los modelos y el almacén DuckDB "
         "(modelo en estrella `dw` y tablas `gold` del dashboard).", "Parquet, CSV, DuckDB"),
)


@dataclass(frozen=True)
class FuenteApi:
    """Ficha de una fuente del registro de descargas: cómo se obtiene y cómo se cachea."""

    modulo: str
    acceso: str
    naturaleza: str  # estático | semiestático | dinámico
    cache: str


# Clave: el texto de la columna `fuente` de data/raw/_registro_descargas.csv.
CATALOGO_APIS: dict[str, FuenteApi] = {
    "Red Eléctrica (REData API)": FuenteApi(
        "cpd.fuentes.ree", "API REST JSON, sin clave", "dinámico",
        "Un JSON por CCAA y año; los años cerrados se leen de caché y solo se repide el año en curso."),
    "NASA POWER": FuenteApi(
        "cpd.fuentes.nasa_power", "API REST JSON, sin clave", "dinámico",
        "Bloques de años por provincia; los bloques cerrados no se repiden. 52 provincias en paralelo (4 hilos)."),
    "Open-Meteo": FuenteApi(
        "cpd.fuentes.meteo", "API REST JSON, sin clave", "dinámico",
        "Varias coordenadas por petición (batching); años cerrados en caché; estado actual en tiempo real."),
    "EEA Natura 2000": FuenteApi(
        "cpd.fuentes.natura", "ArcGIS REST, sin clave", "estático",
        "Una consulta por provincia; caché sin caducidad (la red cambia muy poco)."),
    "PeeringDB": FuenteApi(
        "cpd.fuentes.peeringdb", "API REST JSON, sin clave (límite anónimo por minuto)", "semiestático",
        "Caché con TTL de 7 días: dentro de ese plazo no se hace ninguna petición."),
    "EMSC (FDSN)": FuenteApi(
        "cpd.fuentes.sismicidad", "Servicio FDSN JSON, sin clave", "dinámico",
        "Un año por petición; los años cerrados se leen de caché."),
    "INE (Tempus3 API)": FuenteApi(
        "cpd.fuentes.ine", "API REST JSON, sin clave", "semiestático",
        "Una tabla por petición, guardada en data/raw/api/ine/."),
    "INE": FuenteApi("descarga de fichero", "Fichero CSV/XLSX", "estático", "Descarga única registrada."),
    "INE padrón municipal (29005)": FuenteApi(
        "cpd.fuentes.padron", "Fichero CSV (;)", "semiestático", "Descarga única registrada; se reutiliza."),
    "INE (Tablas Input-Output)": FuenteApi(
        "cpd.fuentes.ine_tio", "Fichero XLSX", "estático", "Descarga única registrada."),
    "MIBGAS": FuenteApi(
        "cpd.fuentes.mibgas", "Ficheros XLSX anuales públicos", "dinámico",
        "Un fichero por año; los años cerrados no se vuelven a descargar."),
    "SEPE": FuenteApi(
        "cpd.fuentes.sepe", "Ficheros CSV anuales (latin-1, ;)", "dinámico",
        "Un fichero por año; solo se repide el año en curso."),
    "OpenStreetMap (Overpass)": FuenteApi(
        "cpd.fuentes.subestaciones", "Overpass API (POST), varios servidores espejo", "estático",
        "Una respuesta por caja geográfica, cacheada sin caducidad."),
    "Eurostat GISCO": FuenteApi("descarga de fichero", "Fichero SHP/CSV", "estático", "Descarga única registrada."),
    "WRI Aqueduct 4.0": FuenteApi("descarga de fichero", "Fichero XLSX en ZIP", "estático", "Descarga única."),
    "Red Eléctrica (capacidad de acceso)": FuenteApi(
        "cpd.fuentes.red_capacidad", "Fichero CSV mensual", "semiestático", "Se descarga el CSV más reciente."),
    "Red Eléctrica": FuenteApi("descarga de fichero", "Fichero CSV", "semiestático", "Descarga única registrada."),
    "Ministerio de Transportes (precios de suelo)": FuenteApi(
        "cpd.fuentes.suelo", "Fichero XLS", "semiestático", "Descarga única registrada; trimestral."),
    "MITECO embalses": FuenteApi(
        "cpd.fuentes.embalses", "Fichero Access (.mdb) en ZIP", "dinámico", "Descarga registrada; semanal."),
    "MITECO": FuenteApi("descarga de fichero", "Fichero ZIP", "dinámico", "Descarga registrada."),
    "BOE (NCSE-02, anejo 1)": FuenteApi(
        "cpd.fuentes.norma_sismica", "PDF oficial", "estático", "Descarga única; la norma no cambia."),
}


def _literal(ruta: Path) -> str:
    """Ruta como literal SQL (barras normales y comillas escapadas)."""
    return "'" + ruta.as_posix().replace("'", "''") + "'"


# ---------------------------------------------------------------------------------------------- Silver → Parquet


def tablas_a_parquet(carpeta: Path, lector_csv: Callable[[Path], str]) -> list[Path]:
    """Escribe `<tabla>.parquet` junto a cada `<tabla>.csv` de `carpeta` si falta o el CSV es más nuevo.

    Args:
        carpeta: carpeta Silver (data/curated/tablas).
        lector_csv: función que devuelve la expresión DuckDB `read_csv(...)` del CSV (con los códigos como texto).

    Returns:
        Las rutas Parquet escritas en esta llamada (vacía si todas estaban al día).
    """
    escritas: list[Path] = []
    if not carpeta.exists():
        return escritas
    with duckdb.connect() as con:
        for ruta_csv in sorted(carpeta.glob("*.csv")):
            ruta_pq = ruta_csv.with_suffix(".parquet")
            if ruta_pq.exists() and ruta_pq.stat().st_mtime >= ruta_csv.stat().st_mtime:
                continue
            tmp = ruta_pq.with_name(ruta_pq.name + ".part")
            con.execute(f"COPY (SELECT * FROM {lector_csv(ruta_csv)}) TO {_literal(tmp)} "
                        "(FORMAT parquet, COMPRESSION zstd)")
            tmp.replace(ruta_pq)
            escritas.append(ruta_pq)
    return escritas


# ------------------------------------------------------------------------------------------------- Watermarks


def columna_tiempo(columnas: list[str]) -> str | None:
    """Primera columna temporal reconocida de una tabla (ver COLUMNAS_TIEMPO), o None."""
    return next((c for c in COLUMNAS_TIEMPO if c in columnas), None)


def watermarks(con: duckdb.DuckDBPyConnection, esquemas: tuple[str, ...] = ("fuentes", "modelo")) -> pd.DataFrame:
    """Último periodo con dato (watermark) de cada tabla con columna temporal.

    Returns:
        DataFrame: esquema, tabla, columna, watermark (texto ISO o año), filas.
    """
    filas = []
    marcadores = ", ".join("?" for _ in esquemas)
    tablas = con.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        f"WHERE table_schema IN ({marcadores}) ORDER BY 1, 2", list(esquemas)).fetchall()
    for esquema, tabla in tablas:
        cols = [c[0] for c in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
            [esquema, tabla]).fetchall()]
        col = columna_tiempo(cols)
        if col is None:
            continue
        maximo, n = con.execute(f'SELECT max("{col}"), count(*) FROM {esquema}."{tabla}"').fetchall()[0]
        if maximo is None:
            continue
        valor = maximo.isoformat()[:19] if hasattr(maximo, "isoformat") else str(maximo)
        filas.append({"esquema": esquema, "tabla": tabla, "columna": col, "watermark": valor, "filas": int(n)})
    return pd.DataFrame(filas, columns=["esquema", "tabla", "columna", "watermark", "filas"])


def fecha_de_watermark(valor: str) -> pd.Timestamp | None:
    """Convierte un watermark (fecha ISO, mes `AAAA-MM` o año `AAAA`) en fecha. Un año cuenta como su 31/12."""
    texto = str(valor).strip()
    if texto.isdigit() and len(texto) == 4:
        return pd.Timestamp(int(texto), 12, 31)
    fecha = pd.to_datetime(texto, errors="coerce")
    if pd.isna(fecha):
        return None
    fecha = pd.Timestamp(fecha)
    return fecha.tz_localize(None) if fecha.tzinfo is not None else fecha


def guardar_historial(marcas: pd.DataFrame, ruta: Path, momento: dt.datetime | None = None) -> pd.DataFrame:
    """Añade las marcas al historial CSV y marca qué tablas han avanzado desde la construcción anterior.

    Returns:
        Las marcas con las columnas `anterior` (watermark previo o vacío) y `avanza` (bool).
    """
    momento = momento or dt.datetime.now()
    anteriores: dict[tuple[str, str], str] = {}
    if ruta.exists():
        previo = pd.read_csv(ruta, dtype=str, keep_default_na=False)
        for fila in previo.itertuples(index=False):
            anteriores[(fila.esquema, fila.tabla)] = fila.watermark  # gana la última construcción
    salida = marcas.copy()
    salida["anterior"] = [anteriores.get((e, t), "") for e, t in zip(salida["esquema"], salida["tabla"])]
    salida["avanza"] = salida["watermark"] != salida["anterior"]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8") as fichero:
        escritor = csv.writer(fichero)
        if nuevo:
            escritor.writerow(["construido_en", "esquema", "tabla", "columna", "watermark", "filas"])
        for fila in marcas.itertuples(index=False):
            escritor.writerow([momento.isoformat(timespec="seconds"), fila.esquema, fila.tabla, fila.columna,
                               fila.watermark, fila.filas])
    return salida


# ------------------------------------------------------------------------------------- Bronze: inventario de raw


def inventario_bronze(ruta_raw: Path) -> pd.DataFrame:
    """Ficheros y tamaño por carpeta de la capa Bronze (`data/raw/<carpeta>` y `data/raw/api/<fuente>`).

    Returns:
        DataFrame: carpeta, ficheros, megabytes, formatos (extensiones separadas por comas).
    """
    grupos: dict[str, dict] = {}
    if ruta_raw.exists():
        for ruta in ruta_raw.rglob("*"):
            if not ruta.is_file() or ruta.name == ".gitkeep":
                continue
            partes = ruta.relative_to(ruta_raw).parts
            if len(partes) == 1:
                clave = "(raíz)"
            elif partes[0] == "api" and len(partes) > 2:
                clave = f"api/{partes[1]}"
            else:
                clave = partes[0]
            g = grupos.setdefault(clave, {"ficheros": 0, "bytes": 0, "formatos": set()})
            g["ficheros"] += 1
            g["bytes"] += ruta.stat().st_size
            g["formatos"].add(ruta.suffix.lower().lstrip(".") or "sin extensión")
    filas = [{"carpeta": k, "ficheros": v["ficheros"], "megabytes": round(v["bytes"] / 1e6, 2),
              "formatos": ", ".join(sorted(v["formatos"]))} for k, v in grupos.items()]
    tabla = pd.DataFrame(filas, columns=["carpeta", "ficheros", "megabytes", "formatos"])
    return tabla.sort_values("megabytes", ascending=False, ignore_index=True)


def _tam_carpetas(raiz: Path, rutas: tuple[str, ...], excluir: tuple[str, ...] = ()) -> tuple[int, int]:
    """Ficheros y bytes de varias carpetas, sin contar dos veces ni las subcarpetas de `excluir`."""
    vistos: set[Path] = set()
    fuera = [(raiz / e).resolve() for e in excluir]
    for rel in rutas:
        carpeta = raiz / rel
        if not carpeta.exists():
            continue
        for p in carpeta.rglob("*"):
            if p.is_file() and p.name != ".gitkeep":
                r = p.resolve()
                if not any(r.is_relative_to(f) for f in fuera):
                    vistos.add(r)
    return len(vistos), sum(p.stat().st_size for p in vistos)


# -------------------------------------------------------------------- CSV frente a Parquet, pandas frente a DuckDB


def comparar_formatos(ruta_csv: Path, ruta_parquet: Path, columna: str, repeticiones: int = 3) -> pd.DataFrame:
    """Mide tamaño y tiempo de calcular la media de `columna` con cada formato y motor.

    Es la comparación de la clase (CSV vs Parquet, pandas vs DuckDB) sobre una tabla real del proyecto.
    Los tiempos son el mínimo de `repeticiones` (segundos) y dependen del equipo: son orientativos.

    Returns:
        DataFrame: formato, motor, operacion, megabytes, segundos, media (para comprobar que coinciden).
    """
    col_sql = '"' + columna.replace('"', '""') + '"'

    def medir(funcion: Callable[[], float]) -> tuple[float, float]:
        mejor, valor = float("inf"), float("nan")
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            valor = funcion()
            mejor = min(mejor, time.perf_counter() - inicio)
        return mejor, float(valor)

    casos = [
        ("CSV", "pandas", "read_csv (todas las columnas) + mean",
         ruta_csv, lambda: pd.read_csv(ruta_csv, low_memory=False)[columna].mean()),
        ("Parquet", "pandas", "read_parquet (solo la columna) + mean",
         ruta_parquet, lambda: pd.read_parquet(ruta_parquet, columns=[columna])[columna].mean()),
        ("CSV", "DuckDB", "SELECT avg() FROM read_csv",
         ruta_csv, lambda: duckdb.execute(f"SELECT avg({col_sql}) FROM read_csv({_literal(ruta_csv)})").fetchall()[0][0]),
        ("Parquet", "DuckDB", "SELECT avg() FROM read_parquet",
         ruta_parquet,
         lambda: duckdb.execute(f"SELECT avg({col_sql}) FROM read_parquet({_literal(ruta_parquet)})").fetchall()[0][0]),
    ]
    filas = []
    for formato, motor, operacion, ruta, funcion in casos:
        segundos, media = medir(funcion)
        filas.append({"formato": formato, "motor": motor, "operacion": operacion,
                      "megabytes": round(ruta.stat().st_size / 1e6, 3), "segundos": round(segundos, 4),
                      "media": media})
    return pd.DataFrame(filas)


def columna_numerica(ruta_parquet: Path) -> str | None:
    """Primera columna numérica de un Parquet que no sea un código ni el tiempo (para la comparación)."""
    esquema = duckdb.execute(f"DESCRIBE SELECT * FROM read_parquet({_literal(ruta_parquet)})").fetchall()
    for nombre, tipo, *_ in esquema:
        if nombre in COLUMNAS_TIEMPO or nombre.startswith(("codigo", "cod_")):
            continue
        if any(t in tipo.upper() for t in ("DOUBLE", "FLOAT", "DECIMAL", "BIGINT", "INTEGER")):
            return nombre
    return None


# ------------------------------------------------------------------------------------------------- Capa Gold


def _registrar_df(con: duckdb.DuckDBPyConnection, tabla: str, df: pd.DataFrame) -> int:
    con.register("_tmp_df", df)
    con.execute(f"CREATE OR REPLACE TABLE gold.{tabla} AS SELECT * FROM _tmp_df")
    con.unregister("_tmp_df")
    return len(df)


def construir_gold(con: duckdb.DuckDBPyConnection, raiz: Path, registro: Path, carpeta_curado: Path,
                   ruta_historial: Path, lector_csv: Callable[[Path], str],
                   hoy: dt.date | None = None) -> dict[str, int]:
    """Crea el esquema `gold` con las tablas que lee el dashboard de datos y APIs.

    Tablas: capas, inventario_bronze, apis, descargas_dia, watermark, tablas, formatos y kpis.

    Returns:
        {gold.tabla: filas}.
    """
    hoy = hoy or dt.date.today()
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    resumen: dict[str, int] = {}

    # Capas (Silver no cuenta data/curated/tablas dentro de Gold, que también cuelga de data/curated)
    filas_capas = []
    for capa in CAPAS:
        excluir = ("data/curated/tablas",) if capa.nombre == "gold" else ()
        n, b = _tam_carpetas(raiz, capa.rutas, excluir)
        filas_capas.append({"capa": capa.nombre, "rutas": ", ".join(capa.rutas), "que_es": capa.que_es,
                            "formatos": capa.formatos, "ficheros": n, "megabytes": round(b / 1e6, 1)})
    resumen["gold.capas"] = _registrar_df(con, "capas", pd.DataFrame(filas_capas))

    resumen["gold.inventario_bronze"] = _registrar_df(con, "inventario_bronze",
                                                      inventario_bronze(raiz / "data" / "raw"))

    # APIs y descargas, desde el registro de descargas (la trazabilidad de la ingesta)
    hay_registro = registro.exists()
    if hay_registro:
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE _registro AS
            SELECT TRY_CAST(fecha_descarga AS TIMESTAMP) AS momento, fuente, descripcion, url, archivo,
                   TRY_CAST(tam_kb AS DOUBLE) AS tam_kb
            FROM {lector_csv(registro)}
            WHERE TRY_CAST(fecha_descarga AS TIMESTAMP) IS NOT NULL
        """)
        apis = con.execute("""
            SELECT fuente,
                   count(*)                                                    AS descargas,
                   count(DISTINCT archivo)                                     AS ficheros,
                   any_value(regexp_extract(url, '^https?://([^/]+)', 1))      AS dominio,
                   round(sum(coalesce(tam_kb, 0)) / 1024, 2)                   AS megabytes,
                   min(momento)                                                AS primera_descarga,
                   max(momento)                                                AS ultima_descarga
            FROM _registro GROUP BY fuente ORDER BY descargas DESC
        """).df()
        sin_ficha = FuenteApi("sin catalogar", "", "", "")
        fichas = [CATALOGO_APIS.get(f, sin_ficha) for f in apis["fuente"]]
        apis["modulo"] = [f.modulo for f in fichas]
        apis["acceso"] = [f.acceso for f in fichas]
        apis["naturaleza"] = [f.naturaleza for f in fichas]
        apis["estrategia_cache"] = [f.cache for f in fichas]
        resumen["gold.apis"] = _registrar_df(con, "apis", apis)
        con.execute("""
            CREATE OR REPLACE TABLE gold.descargas_dia AS
            SELECT CAST(momento AS DATE) AS dia, fuente, count(*) AS descargas,
                   round(sum(coalesce(tam_kb, 0)) / 1024, 2) AS megabytes
            FROM _registro GROUP BY 1, 2 ORDER BY 1, 2
        """)
        resumen["gold.descargas_dia"] = con.execute("SELECT count(*) FROM gold.descargas_dia").fetchall()[0][0]

    # Watermarks (y su historial)
    marcas = guardar_historial(watermarks(con), ruta_historial)
    fechas = [fecha_de_watermark(v) for v in marcas["watermark"]]
    # Un año en curso (p. ej. «2026» → 31/12/2026) aún no ha terminado: cuenta como fresco (0 días), no negativo.
    marcas["dias_desde"] = pd.array([max(0, (pd.Timestamp(hoy) - f).days) if f is not None else None
                                     for f in fechas], dtype="Int64")
    resumen["gold.watermark"] = _registrar_df(con, "watermark", marcas)

    # Catálogo de tablas del almacén con su capa
    tablas = con.execute("""
        SELECT c.esquema, c.tabla, c.filas, c.origen, c.cargado_en, count(i.column_name) AS columnas
        FROM meta.carga AS c
        LEFT JOIN information_schema.columns AS i ON i.table_schema = c.esquema AND i.table_name = c.tabla
        GROUP BY ALL ORDER BY c.esquema, c.tabla
    """).df()
    tablas["capa"] = ["silver" if e == "fuentes" else "gold" for e in tablas["esquema"]]
    tablas["formato"] = [Path(o).suffix.lstrip(".") for o in tablas["origen"]]
    tablas["origen"] = [Path(o).name for o in tablas["origen"]]
    tablas = tablas.merge(marcas[["esquema", "tabla", "columna", "watermark", "dias_desde"]],
                          on=["esquema", "tabla"], how="left")
    resumen["gold.tablas"] = _registrar_df(con, "tablas", tablas)

    # CSV frente a Parquet sobre la tabla más grande del modelo
    csv_panel = carpeta_curado / "panel_provincia_mes.csv"
    pq_panel = carpeta_curado / "panel_provincia_mes.parquet"
    if csv_panel.exists() and pq_panel.exists() and (col := columna_numerica(pq_panel)):
        formatos = comparar_formatos(csv_panel, pq_panel, col)
        formatos["tabla"] = "panel_provincia_mes"
        formatos["columna"] = col
        resumen["gold.formatos"] = _registrar_df(con, "formatos", formatos)

    # Indicadores del dashboard (una fila)
    def uno(sql: str):
        return con.execute(sql).fetchall()[0][0]

    kpis = {
        "fuentes": int(uno("SELECT count(*) FROM gold.apis")) if hay_registro else 0,
        "descargas": int(uno("SELECT coalesce(sum(descargas), 0) FROM gold.apis")) if hay_registro else 0,
        "ultima_descarga": uno("SELECT max(ultima_descarga) FROM gold.apis") if hay_registro else None,
        "tablas": len(tablas),
        "filas": int(tablas["filas"].sum()) if not tablas.empty else 0,
        "megabytes_bronze": next(c["megabytes"] for c in filas_capas if c["capa"] == "bronze"),
        "construido_en": dt.datetime.now().replace(microsecond=0),
    }
    resumen["gold.kpis"] = _registrar_df(con, "kpis", pd.DataFrame([kpis]))
    return resumen
