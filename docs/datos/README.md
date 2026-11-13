# Datos del proyecto · Informe de origen de datos (borrador)

Fase actual: **ingesta** (la "E" de ETL). Los datos se descargan **tal cual** de fuentes oficiales y se
guardan en `data/raw/` (capa *raw* del Data Lake). No se limpian ni se transforman en esta fase.

- Descarga realizada el **09/11/2026**.
- Registro de cada descarga (fuente, URL, fecha y tamaño): [`data/raw/_registro_descargas.csv`](../../data/raw/_registro_descargas.csv).
- Huella SHA-256 de cada fichero: [`manifiesto_raw_2026-11-09.csv`](manifiesto_raw_2026-11-09.csv) (472 ficheros, 490 MB).
- Llave común para unir las fuentes: **código INE del municipio** (5 dígitos: 2 de provincia + 3 de municipio).

## Cómo obtener los datos

Los ficheros raw no están en el repositorio: el mayor pesa 260 MB y GitHub no admite ficheros de más de
100 MB. Hay dos formas de tenerlos en `data/raw/`:

1. **Descargar la copia del 09/11/2026** publicada como Release del repositorio (zip de 103 MB):

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\descargar_datos_raw.ps1
   ```

   El script comprueba la huella SHA-256 del zip antes de descomprimirlo.

2. **Volver a descargar desde las fuentes** (datos más recientes; no repite lo que ya existe):

   ```powershell
   .\.venv\Scripts\python.exe src\ingesta\01_municipios.py
   .\.venv\Scripts\python.exe src\ingesta\02_demografia.py
   .\.venv\Scripts\python.exe src\ingesta\03_energia.py
   .\.venv\Scripts\python.exe src\ingesta\04_agua.py
   ```

## Fuentes descargadas

| Bloque | Fuente | Fichero en `data/raw/` | Cobertura | Formato | Modelos |
|---|---|---|---|---|---|
| Municipios | INE · Relación de municipios 2026 | `municipios/ine_diccionario_municipios_2026.xlsx` | 8.132 municipios (CODAUTO, CPRO, CMUN, DC, NOMBRE) | XLSX | Clave de todo |
| Municipios | Eurostat GISCO · LAU 2024 | `municipios/gisco_lau_2024_4326.shp.zip`, `gisco_lau_2024_atributos.csv` | 8.132 municipios de España, polígonos y superficie (504.722 km²) | SHP (EPSG:4326) + CSV | Centroides, densidad, distancias |
| Demografía | INE · Padrón (tabla 29005) | `demografia/ine_padron_municipios_29005.csv` | 1996–2025; 49.114.494 habitantes en 2025 | CSV `;` | M8, M9 |
| Demografía | INE · Atlas de Renta ADRH (30824) | `demografia/ine_adrh_renta_30824.csv` | 2015–2024; 6 indicadores de renta media y mediana | CSV `;` | M8, M9 |
| Demografía | INE · ADRH indicadores demográficos (30832) | `demografia/ine_adrh_demograficos_30832.csv` | 2015–2024; edad media, % ≥ 65, % < 18, tamaño del hogar… | CSV `;` | M8, M9 |
| Demografía | INE · Censo 2021, nivel de estudios (66620, 66623) | `demografia/ine_censo2021_estudios_*.csv` | 2021–2024; 4.144 municipios ≥ 500 hab. + 3.419 de 50–500 hab.; 5 niveles | CSV `;` | M8 |
| Demografía | SEPE · Paro registrado por municipio | `demografia/sepe_paro_municipios_2023…2026.csv` | Mensual, ene-2023 a sep-2026; unos 8.135 municipios; por sexo, edad y sector | CSV `;` (latin-1) | M8 |
| Energía | Red Eléctrica · Capacidad de acceso de demanda | `energia/ree_capacidad_acceso_demanda_2026_11_03_GRT_demanda.csv` | 937 nudos de la red de transporte, 18 CCAA (publicación 03/11/2026) | CSV `;` | **M1** (filtro eléctrico) |
| Energía | Red Eléctrica · REData, demanda | `energia/ree/demanda/<ccaa>_<año>.json` | Mensual por CCAA, 2015–2026 (228 ficheros) | JSON | M2, M9 |
| Energía | Red Eléctrica · REData, estructura de generación | `energia/ree/generacion/<ccaa>_<año>.json` | Mensual por CCAA y tecnología, 2015–2026 (228 ficheros) | JSON | M2 (% renovable), M9 |
| Agua | MITECO · Boletín Hidrológico, embalses | `agua/miteco_bd_embalses_1988_hoy.zip` | Reserva semanal de embalses peninsulares > 5 hm³ desde 1988 | Access `.mdb` (223 MB) en zip | M6 |
| Agua | WRI Aqueduct 4.0 | `agua/wri_aqueduct40_rankings_pais_provincia.zip` | Estrés hídrico actual y proyecciones 2030–2080 por país y por CCAA | XLSX en zip | M6 |

## Avisos para la fase de transformación

- **Códigos de municipio:** el padrón y el ADRH traen unos 8.138 códigos (municipios desaparecidos o
  fusionados). Hay que filtrar con el diccionario INE 2026 (8.132).
- **GISCO:** la población de 2024 viene a 0 para España; usar el padrón del INE.
- **CSV del INE:** separador `;`, miles con punto y decimales con coma (`17.698`, `40,8`). El código y el
  nombre del municipio van juntos en una columna (`01001 Alegría-Dulantzi`).
- **SEPE:** codificación latin-1, una primera línea de título antes de la cabecera y valores `<5`
  (secreto estadístico) que hay que tratar como dato ausente o rango 0–4.
- **Embalses:** formato Microsoft Access; para leerlo hace falta `mdbtools` o el controlador ODBC de Access.
- **Energía:** no hay consumo eléctrico abierto por municipio para toda España; se trabaja por comunidad
  autónoma y por nudo de la red de transporte.
- **WRI Aqueduct:** el nivel "province" equivale a comunidad autónoma en España, no a provincia.

## Datos por API (capa actualizable)

Tablas por provincia (52) obtenidas por API, con histórico y tiempo real: ver [`tablas_api.md`](tablas_api.md)
(columnas, unidades, endpoints, granularidad, cobertura y limitaciones).

## Fuentes en tiempo real

Qué fuentes se actualizan en minutos, horas o días, cuáles se pueden recopilar sin clave y qué problemas
tienen: [`fuentes_tiempo_real.md`](fuentes_tiempo_real.md). El sondeo en vivo se repite con
`.\.venv\Scripts\python.exe src\ingesta\sondeo_fuentes.py` y deja el resultado en
[`sondeo_fuentes.csv`](sondeo_fuentes.csv).

## Pendiente de descargar

- Clima: AEMET OpenData u Open-Meteo (temperatura, humedad, días de calor extremo).
- OpenStreetMap: subestaciones, aeropuertos, puertos, autopistas y CPD existentes.
- Telecomunicaciones: cobertura de fibra y 5G; puntos neutros (PeeringDB).
- Suelo y riesgos: zonas inundables (SNCZI; el servidor del MITECO tiene el certificado SSL roto),
  peligrosidad sísmica (IGN) y Red Natura 2000.
- El registro de centrales del MITECO (RAIPEE) no ofrece descarga masiva.

## Condiciones de reutilización (resumen; comprobar en cada portal)

| Fuente | Condición |
|---|---|
| INE | Reutilización libre citando la fuente ("Fuente: INE"). |
| SEPE | Datos abiertos; reutilización citando la fuente. |
| Red Eléctrica (REE / REData) | Reutilización citando a Red Eléctrica como fuente. |
| MITECO | Datos abiertos; reutilización citando la fuente. |
| Eurostat GISCO (LAU) | © EuroGeographics for the administrative boundaries. |
| WRI Aqueduct 4.0 | Licencia CC BY 4.0 (World Resources Institute). |
