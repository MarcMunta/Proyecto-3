---
tags: [fuente, clase, data-engineering, ingesta, almacenamiento, p3]
estado: revisada
actualizado: 2026-11-27
---

# Fuente · Clase 27/11/2026 · Data Mining & Data Engineering with Python

Archivo: `C:\Users\marcm\Downloads\20261127_Data_Mining_Data_Engineering_4_Analytics.pptx.pdf` (37 páginas; leídas en texto completo). Volver a [[00_Indice]]. Código de las filas de la checklist: **C5**.

## Resumen

La clase trata cómo construir un sistema que lee datos todo el día sin caerse («Modern systems read data all day and don't die»). Sigue el camino completo del dato en seis bloques:

```
INTERNET / SENSORES → API → INGESTA (reintentos · caché · límite de ritmo) → RAW
   → ETL / LIMPIEZA → PARQUET → DUCKDB → ANALÍTICA → STREAMLIT → DASHBOARD
```

1. **Ingesta** (p. 3-8): recogida frente a ingesta; *batch* (cada noche o cada 6 h: barato y fácil de mantener) frente a continua; *polling* (preguntar cada X segundos) frente a *streaming* (la fuente empuja: Kafka, RabbitMQ, WebSockets; próxima clase). ETL (extraer → transformar → cargar) frente a ELT (extraer → cargar → transformar). El gran problema son las peticiones: 5.000 estaciones × 0,3 s = 25 minutos por pasada si se piden una a una.
2. **Optimización** (p. 10-20): no descargar basura (filtrar en la API); **paginación** (offset, página, cursor); **batching** (pedir 100 elementos por petición en vez de 1); **paralelizar** peticiones con un límite; **rate limiting** (HTTP 429, máximo de peticiones por minuto); **reintentos** con *fallback* ante 429/500/502; **backoff exponencial** (espera = base × 2ⁿ: 1, 2, 4, 8 s) con *jitter* (azar para que no reintente todo el mundo a la vez); **caché**: la mejor petición es la que no se hace; separar lo estático (nombres, ids, coordenadas) de lo dinámico y usar un **TTL** (metadatos cada semana, tiempo cada minuto).
3. **Almacenamiento** (p. 22-25): `all_data.csv` solo sirve para datos pequeños (sin tipos, lento, sin compresión). **Parquet**: binario, columnar, comprimido y con tipos; para `AVG(temperatura)` solo se lee esa columna. Comparación CSV, JSON y Parquet.
4. **Consultas y arquitectura** (p. 27-35): **DuckDB** = SQL analítico embebido (sin servidor, credenciales, Docker ni puertos) que consulta Parquet directamente; pandas no es malo, pero no conviene cargar 80 M de filas para un `GROUP BY`; combinar ambos (DuckDB reduce, pandas para ML y gráficos). **OLTP** (muchas operaciones pequeñas: altas, pedidos) frente a **OLAP** (consultas sobre muchas filas). **ORM / SQLAlchemy** para datos transaccionales. **Data lake por capas: Bronze / Silver / Gold**.
5. **Pipelines y calidad** (p. 35): el paso de Bronze a Silver es la calidad de datos de las clases anteriores; de Silver a Gold, la agregación.
6. **Reglas y producto** (p. 36): dejar rastro de qué se hizo y cuándo; no descargar dos veces lo que ya se tiene; actualizar siempre los *watermarks*; decidir entre *at least once* y *exactly once*; **el dashboard nunca hace ingeniería de datos**, solo consulta; quien abre Streamlit ya tiene la información lista.

## Términos clave

Recogida de datos · ingesta · batch · continua · polling · streaming · ETL · ELT · paginación (offset, page, cursor) · batching · paralelización · I/O-bound · CPU-bound · `asyncio` · `httpx` · `ThreadPoolExecutor` · `aiohttp` · rate limiting · HTTP 429 · reintentos · fallback · backoff exponencial · jitter · caché · TTL · CSV · JSON · Parquet · formato columnar · DuckDB · `read_parquet` · OLTP · OLAP · ORM · SQLAlchemy · data lake · Bronze / Silver / Gold · calidad de datos · carga incremental · watermark · at least once · exactly once · Streamlit · dashboard. Definiciones en [[02_Conceptos_clave]], sección 14.

## Acciones (lo que pide la clase)

**Obligatorias del proyecto (según la clase):**
1. Ingesta automática y reproducible, sin pasos manuales; batch o continua según la frescura que haga falta (p. 4-6).
2. Pedir solo lo necesario: filtrar en la API y agrupar elementos por petición (p. 13-14).
3. Paralelizar peticiones independientes, con un límite de simultaneidad y respetando el *rate limit* (p. 15-17).
4. Reintentar con backoff exponencial y jitter, con un máximo de intentos (p. 18-19).
5. Cachear: lo estático una vez; lo semiestático con TTL; lo dinámico, solo lo nuevo (p. 20).
6. Guardar en Parquet en vez de CSV cuando los datos crecen, y consultar con DuckDB (p. 23-28).
7. Organizar los datos en capas Bronze, Silver y Gold (p. 34).
8. Dejar trazabilidad, no repetir descargas y actualizar los watermarks (p. 36).
9. El dashboard (DuckDB + Streamlit) solo lee datos ya preparados (p. 36).

**Recomendaciones (no viene de clase):**
- Respetar la cabecera `Retry-After` del servidor en los 429 y 503: es mejor que adivinar la espera.
- Una sesión HTTP por hilo (`requests.Session` no es segura entre hilos) y una pausa mínima global protegida con un cerrojo.
- Escribir siempre en un fichero temporal (`.part`, `.tmp.duckdb`) y renombrarlo al final: una ejecución que falla a medias no deja datos corruptos y repetirla no duplica nada (idempotencia; sirve como *exactly once* a nivel de fichero).
- **Corrección de la diapositiva 16:** la paralelización con hilos o `asyncio` sirve precisamente para el trabajo **I/O-bound** (esperar a la red), que es el caso de la ingesta. El trabajo CPU-bound en Python necesita procesos (`ProcessPoolExecutor`) por el GIL.

## Enlaces

La presentación no contiene enlaces externos (las páginas «Text» son portadas de sección).

## Cómo se aplica a P3

| Clase | En P3 | Dónde |
|---|---|---|
| Batch e incremental | Refresco batch completo e incremental; los periodos cerrados salen de la caché y solo se pide lo nuevo. `--rapido` = solo los campos de tiempo real | `src/cpd/fuentes/actualizar.py` |
| Polling frente a streaming | Polling (el mapa consulta Open-Meteo y REData cada pocos minutos). Streaming no hace falta: ninguna variable del CPD cambia en segundos | `frontend/src/live/usePolling.ts` |
| Filtrar antes de descargar | Solo España (`country=ES`), cajas geográficas (EMSC, Overpass, Natura 2000) y solo las variables necesarias (NASA POWER) | `src/cpd/fuentes/*.py` |
| Paginación | Ninguna API usada pagina; las series largas se piden por bloques de años (REData, EMSC, NASA POWER) | `ree.py`, `sismicidad.py`, `nasa_power.py` |
| Batching | Open-Meteo: las 52 capitales en una sola petición (`TAMANO_LOTE = 52`, coordenadas separadas por comas) | `src/cpd/fuentes/meteo.py` |
| Paralelización | `http.en_paralelo` (hilos con límite); NASA POWER pide las 52 provincias con 4 hilos | `src/cpd/fuentes/http.py`, `nasa_power.py` |
| Rate limiting y 429 | Pausa mínima de 0,4 s entre peticiones, también entre hilos; ante un 429, la espera de `Retry-After` o 65 s | `http.pedir` |
| Reintentos con backoff | `espera_backoff`: 2, 4, 8… s (tope 60 s) + hasta un 25 % de jitter | `http.espera_backoff` |
| Caché con TTL | `leer_cache_json(ruta, ttl_horas)`: estático sin caducidad (Natura, Overpass, BOE); PeeringDB 7 días; los años cerrados nunca se repiden | `http.py`, `peeringdb.py` |
| Parquet | Las tablas Silver se guardan también en Parquet (zstd) si su CSV cambió; el panel ya lo estaba | `src/cpd/capas.py` (`tablas_a_parquet`) |
| DuckDB frente a pandas | Almacén DuckDB con modelo en estrella y comparación medida CSV/Parquet × pandas/DuckDB | `src/cpd/almacen.py`, `gold.formatos` |
| OLTP frente a OLAP | P3 es OLAP puro (lecturas analíticas, sin transacciones): DuckDB; no hacen falta PostgreSQL ni un ORM | [[04_Reglas_de_datos]], R-21 |
| Bronze / Silver / Gold | Bronze = `data/raw`; Silver = `data/clean`, `data/curated/tablas`; Gold = `data/curated` y el almacén (`dw`, `gold`) | `capas.CAPAS` |
| Trazabilidad y watermarks | Registro de descargas, `meta.carga` y `historial_watermarks.csv` (qué tabla avanzó en cada construcción) | `capas.guardar_historial` |
| Dashboard que solo lee | La clase usa Streamlit; en P3 el producto es el mapa web, así que el dashboard es su panel «Datos» (`#/datos`), con la misma estética. Lee `datos.json`, exportado del esquema `gold` en modo lectura | `frontend/src/components/CatalogoDatos.tsx`, `cpd.capas.exportar_web` |

Medición real (27/11/2026, `panel_provincia_mes`, media de `tmedia_mes_c`): CSV 3,38 MB frente a Parquet 0,87 MB (**3,9 veces menos**); DuckDB tarda 74 ms sobre el CSV y 1,3 ms sobre el Parquet (**unas 57 veces menos**). Los cuatro cálculos dan la misma media. Los tiempos dependen del equipo.

## Notas de estado en el repo

Ver [[06_Checklist_entrega]], filas I71 a I89. Reglas nuevas R-17 a R-21 en [[04_Reglas_de_datos]]. Fases 1 y 10 de [[03_Flujo_de_trabajo]] actualizadas.
