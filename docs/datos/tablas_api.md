# Tablas por API · provincias de España

Capa de datos **actualizable por API**. Cada tabla se obtiene de una fuente pública programática, se cachea en
`data/raw/api/<fuente>/` y se guarda como tabla larga en `data/curated/tablas/`. Las dos salidas son
`panel_provincia_mes` (provincia × mes, historia desde 2015-01) y `provincias_actual` (52 filas, último valor
disponible y tiempo real).

Actualizar:
- `python -m cpd.fuentes.actualizar` — refresco completo: tiempo real + historia (incremental: los años cerrados
  salen de caché; el bloque en curso se vuelve a pedir).
- `python -m cpd.fuentes.actualizar --rapido` — solo tiempo real (clima actual, previsión de 7 días, demanda y precios).
  No actualiza la historia ni las reservas hídricas (el zip del MITECO se renueva con el refresco completo).

Clave común: `codigo_provincia` (código INE de dos dígitos, `01`–`52`, incluidos Ceuta `51` y Melilla `52`).
Granularidad: **P** = provincia (capital como punto representativo), **CCAA** = comunidad autónoma (se hereda a sus
provincias), **Á** = ámbito hidrográfico (se hereda a las provincias asignadas), **N** = nacional.

## 1. Tablas base

| Tabla | Columnas | Fuente | Gran. | Actualización | Historia |
|---|---|---|---|---|---|
| `provincias` | codigo_provincia, provincia, codigo_ccaa, ccaa, ree_geo_id, lat_punto, lon_punto | Tabla maestra INE 01–52; puntos = capitales | P | estática | — |
| *(polígonos)* `data/raw/api/provincias/poligonos_provincias.geojson` | geometría por provincia | GISCO LAU 2024 disuelto por provincia | P | estática | — |

## 2. Clima histórico y en tiempo real

### 2.1 Historia: NASA POWER (`power.larc.nasa.gov`, sin clave)

| Tabla | Columnas | Unidades | Endpoint | Gran. | Actualización | Historia |
|---|---|---|---|---|---|---|
| `clima_diario` | fecha, codigo_provincia, tmedia_c, tmax_c, tmin_c, humedad_relativa_media_pct, precipitacion_mm, viento_medio_kmh, radiacion_solar_kwh_m2_dia, et0_hargreaves_mm | °C, %, mm, km/h, kWh/m²/día, mm | `temporal/daily/point`, comunidad AG (T2M, T2M_MAX, T2M_MIN, RH2M, PRECTOTCORR, WS10M, ALLSKY_SFC_SW_DWN) | P | diaria (hasta hace 2 días) | desde 2015-01-01 |
| `free_cooling` | mes, codigo_provincia, horas_free_cooling, horas_con_dato, pct_horas_free_cooling | h, % | `temporal/hourly/point` (T2M), hora local estándar | P | mensual | desde 2015-01 |

- **Free-cooling** = horas del mes con temperatura del aire < 18 °C (serie horaria).
- **ET0 de referencia** = Hargreaves-Samani (FAO-56, ec. 52) con Ra calculada desde la latitud de la capital. Se
  eligió en lugar de `EVPTRNS` de POWER, que es evapotranspiración real del reanálisis y da valores anuales bajos
  para Madrid (≈100 mm); la ET0 Hargreaves da 1.239 mm en 2024 para Madrid (precipitación 486 mm ese año).
- Malla MERRA-2 (~0,5°): cada capital toma la celda más cercana. Es clima regional, no medición de estación.
- Los valores -999 de POWER se tratan como ausencia (NaN), nunca como cero.

### 2.2 Historia previa de Open-Meteo (ya no se usa)

La descarga de ERA5 de Open-Meteo (`archive-api`) devolvió HTTP 429 (límite diario). Las funciones
`meteo.clima_diario` y `meteo.free_cooling_mensual` se conservan, pero **no** se usan en el refresco; los años
2015–2020 que quedaron en caché (`data/raw/api/meteo/diario/`) no entran en el panel.

### 2.3 Tiempo real y previsión: Open-Meteo (`api.open-meteo.com`)

| Tabla | Columnas | Endpoint | Gran. | Actualización |
|---|---|---|---|---|
| `clima_actual` | codigo_provincia, momento_observacion, temperatura_actual_c, humedad_relativa_actual_pct, viento_actual_kmh, precipitacion_actual_mm, temp_prevision_7d_media_c, temp_prevision_7d_max_c, precipitacion_prevision_7d_mm | `forecast` (`current` y `daily` con `forecast_days=7`), 2 peticiones por refresco | P | tiempo real |

## 3. Agua

| Tabla | Columnas | Fuente | Gran. | Actualización | Historia |
|---|---|---|---|---|---|
| `reservas_ambito_mensual` | mes, ambito, reserva_pct_media_mes, volumen_hm3_media_mes, capacidad_hm3_media_mes, semanas_con_dato | MITECO, BD de embalses semanal (`BD-Embalses.zip`, Access) leída con `access-parser` 0.0.6 | Á | semanal (los martes); el zip se vuelve a bajar si tiene más de 6 días | desde 1987-10 |
| `estres_hidrico_wri` | codigo_provincia, estres_hidrico_wri_0_1, comunidad_wri | WRI Aqueduct 4.0, indicador `bws` (ponderación `Tot`), hoja `province_baseline`, zip local | CCAA | estática | — |

Cómo se calcula:
- **Reserva semanal por ámbito** = Σ volumen actual / Σ capacidad, usando solo los embalses que informan esa semana.
  **Mensual** = media de las semanas del mes (`semanas_con_dato` indica cuántas hay).
- **Asignación provincia → ámbito** (`AMBITO_POR_PROVINCIA` en `fuentes/embalses.py`): tabla estática y aproximada.
  Cada provincia toma el ámbito que cubre la mayor parte de su territorio. Baleares, Canarias, Ceuta y Melilla no
  tienen embalses en la base del MITECO y quedan sin ámbito (NaN).
- **Estrés hídrico WRI**: la hoja trae 6 esquemas de ponderación por comunidad; se usa `Tot` (demanda total) y se
  divide entre 5 (escala del indicador) para tener 0–1. Es a nivel de comunidad; Ceuta y Melilla comparten valor.

Derivadas en el panel (ver sección 7): `balance_hidrico_mes_mm` (precipitación − ET0 Hargreaves),
`precipitacion_12m_mm` e `indice_sequia_12m`.

## 4. Energía (Red Eléctrica · REData, `apidatos.ree.es`)

| Tabla | Columnas | Unidades | Endpoint | Gran. | Actualización | Historia |
|---|---|---|---|---|---|---|
| `ccaa_demanda` | codigo_ccaa, ccaa, fecha, demanda_mwh | MWh | `demanda/evolucion` (`geo_limit=ccaa`, mensual) | CCAA | mensual | desde 2015 |
| `ccaa_generacion` | codigo_ccaa, fecha, generacion_total_mwh, generacion_renovable_mwh, pct_renovable | MWh, % | `generacion/estructura-generacion` | CCAA | mensual | desde 2015 |
| `co2` | fecha, emisiones_co2_tco2eq | tCO2 eq. | `generacion/no-renovables-detalle-emisiones-CO2` | N | mensual | desde 2015 |
| `precios_diarios` | fecha, precio_spot_eur_mwh, precio_pvpc_eur_mwh | €/MWh | `mercados/precios-mercados-tiempo-real` (`time_trunc=hour`) | N | diaria | desde 2015 |
| `energia_tiempo_real` | momento_consulta, demanda_tiempo_real_mw, precio_spot_actual_eur_mwh, precio_spot_manana_medio_eur_mwh | MW, €/MWh | `demanda-tiempo-real`; spot; OMIE `marginalpdbc` | N | tiempo real | — |
| `capacidad_ccaa` | codigo_ccaa, ccaa, nudos, capacidad_demanda_rdt_disponible_mw | MW | CSV de REE "capacidad de acceso" | CCAA | mensual (REE) | última publicación |

La API de REData responde 400/502 de forma intermitente (se reintenta). Los precios solo funcionan con
`time_trunc=hour`. Las emisiones de CO2 no tienen desglose por CCAA.

## 5. Demografía, economía y empleo (INE, SEPE)

| Tabla | Columnas | Unidades | Fuente | Gran. | Actualización | Historia |
|---|---|---|---|---|---|---|
| `poblacion` | codigo_provincia, anio, poblacion, fuente_poblacion, diferencia_padron_vs_tempus_pct | habitantes, % | INE Tempus3 tabla 2852 (≤ 2021) + **padrón municipal 29005** (2022 en adelante) | P | anual (padrón: el fichero se renueva si tiene > 30 días) | 1996–2025 |
| `renta` | codigo_provincia, anio, renta_neta_media_persona_eur, renta_neta_media_hogar_eur, mediana_renta_unidad_consumo_eur | € | INE Tempus3 tabla 53689 (ADRH) | P | anual | 2015–2024 |
| `paro` | codigo_provincia, mes, paro_registrado, municipios | personas | SEPE datos abiertos, suma de municipios | P | mensual | desde 2015 |

**Población.** Tempus3 llega hasta 2021. El padrón municipal (`https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/29005.csv`,
separador `;`, miles con punto) suma los municipios de cada provincia (sexo "Total"). Se prefiere Tempus cuando
existe el año y el padrón para 2022–2025. Control: en 2020 y 2021 la diferencia padrón − Tempus es 0,00 % en las
52 provincias. Los municipios que faltan en un año porque se fusionaron (p. ej. Cerdedo + Cotobade → Cerdedo-Cotobade
en 2023) se cuentan en `municipios_sin_dato`; su población ya figura en el municipio nuevo, así que no se estima ni se
duplica ningún hueco.

El paro es **paro registrado** (oficina de empleo), no la tasa EPA. `paro_por_1000_hab` = paro / población × 1000.

## 6. Conectividad, red, riesgos y suelo

| Tabla | Columnas | Fuente | Gran. | Actualización |
|---|---|---|---|---|
| `conectividad` | codigo_provincia, n_centros_datos, n_ixp, distancia_ixp_km | PeeringDB `api/fac` y `api/ix` (país ES) | P | semanal (estática) |
| `subestaciones` | codigo_provincia, subestaciones_220_400kv, subestaciones_400kv | OpenStreetMap vía Overpass (`power=substation`) | P | estática |
| `sismos` | codigo_provincia, anio, n_terremotos, magnitud_max, n_terremotos_m3_plus | EMSC FDSN (M ≥ 1,5), asignación por polígono | P | anual, desde 2015 |
| `natura` | codigo_provincia, pct_superficie_natura2000, espacios_natura_2000 | EEA Natura 2000, ArcGIS REST | P | estática |

Los IXP no tienen coordenadas en PeeringDB: se asignan por ciudad y la distancia es aproximada.
Los terremotos fuera de cualquier polígono provincial no se asignan. Dentro del rango descargado, la ausencia de
eventos cuenta como 0.

## 7. Tablas de salida

### 7.1 `panel_provincia_mes` (entrenamiento)

Filas: 52 provincias × meses desde **2015-01** hasta **2026-10** (7.384 filas, 51 columnas). Donde una fuente no tiene
dato → **NaN**. Diccionario en `data/curated/diccionario_panel_provincia_mes.csv`.

Reglas de agregación del clima mensual:
- Medias (temperaturas, humedad, viento, radiación) con los días disponibles.
- Acumulados (`precipitacion_mes_mm`, `et0_hargreaves_mes_mm`) solo si el mes está completo; si no, NaN.
- `balance_hidrico_mes_mm` = precipitación − ET0 (NaN si falta alguno de los dos).
- `precipitacion_12m_mm` e `indice_sequia_12m`: ventana móvil de 12 meses; el índice es un z-score del acumulado
  frente a su mismo mes del calendario (requiere ≥ 3 años de referencia). Valores < −1 indican sequía moderada.
- `dias_mas_35c` = días con temperatura máxima ≥ 35 °C.

Tipos de variable: **mensual** (clima, reservas, demanda, paro); **Á** (reservas: se repiten en las provincias de su
ámbito); **CCAA/nacional** (demanda, generación, CO2, precios); **anual** (población, renta, sismos); **estática**
(centros de datos, subestaciones, Natura 2000, WRI, ámbito): foto de la descarga, úsese como variable de corte.

### 7.2 `provincias_actual` (último valor y tiempo real)

52 filas × 66 columnas. Para cada variable, el último valor disponible de la provincia (`mes_referencia_panel` indica
el último mes del panel). Tiempo real: `temperatura_actual_c`, `humedad_relativa_actual_pct`, `viento_actual_kmh`,
`precipitacion_actual_mm`, `momento_observacion`, `temp_prevision_7d_media_c`, `temp_prevision_7d_max_c`,
`precipitacion_prevision_7d_mm` (capital) y `demanda_tiempo_real_mw`, `precio_spot_actual_eur_mwh`,
`precio_spot_manana_medio_eur_mwh` (nacionales). `cpd_existentes` = centros de datos en PeeringDB.

### 7.3 Almacén DuckDB

`python -m cpd.almacen` reconstruye `data/almacen/p3_cpd.duckdb`: esquema `fuentes` (una tabla por CSV de
`data/curated/tablas/`, incluidas `reservas_ambito_mensual` y `estres_hidrico_wri`), `modelo` (panel y actual con sus
diccionarios), `dw` (estrella) y `meta`.

## 8. Fuentes no usadas o pendientes

| Fuente | Motivo |
|---|---|
| Open-Meteo ERA5 (historia) | Límite diario de la API (HTTP 429). Sustituido por NASA POWER. |
| ESIOS (REE) | Requiere token. Mejora opcional. |
| AEMET | Requiere clave de API. Mejora opcional. |
| MITECO · SNCZI (zonas inundables) | Certificado SSL roto en el servidor. No se desactiva la verificación TLS. Pendiente. |
| Polígonos oficiales de demarcaciones hidrográficas (EEA WISE) | No se descargaron; la asignación provincia→ámbito es estática (sección 3). |
| Renta por municipio, EPA por provincia | No incluidas. |

## 9. Limitaciones

- **Clima**: reanálisis MERRA-2 a ~0,5° (la capital toma la celda más cercana); las temperaturas extremas pueden estar
  suavizadas y `dias_mas_35c` puede subestimar el calor local. ET0 por Hargreaves, no Penman-Monteith.
- **Free-cooling**: calculado con temperatura del aire, sin punto de rocío ni humedad; es una cota optimista del
  uso de aire exterior.
- **Sequía**: el índice usa solo 2015 en adelante (poca referencia: un mes necesita ≥ 3 años); es orientativo.
- **Reservas**: asignación provincia→ámbito aproximada; la reserva de una provincia es la de su ámbito, no la de sus
  embalses. Los meses recientes tienen menos semanas (`semanas_reserva_mes`).
- **WRI**: foto de 2023 a nivel de comunidad; no tiene evolución temporal.
- **Población**: el padrón es la cifra oficial del INE; los municipios fusionados se tratan como se explica en la sección 5.
- **Estáticas** (conectividad, subestaciones, capacidad, Natura 2000, WRI, ámbito): sin histórico.
- **Subestaciones de OpenStreetMap**: recuento de lo mapeado, cobertura desigual entre provincias.
- **Capacidad de acceso**: solo nivel CCAA y último mes publicado.
- **Precios**: nacionales; no hay precio por zona. `precio_pvpc_medio_mes_eur_mwh` tiene cobertura del 46 % (solo cubre el periodo publicado por REData).
- **Paro registrado** (SEPE): no es tasa EPA.
- Si una fuente falla, sus columnas quedan NaN y el resumen de `actualizar` lo indica. Nunca se inventan valores.

## 10. Resultado de la última actualización

Ejecución del 13/11/2026 (`python -m cpd.fuentes.actualizar`, 790 s, sin fallos ni uso de copias anteriores):

| Tabla | Filas | Rango | Provincias / ámbitos | Estado |
|---|---|---|---|---|
| `provincias` | 52 | — | 52 | OK |
| `clima_actual` (incl. previsión 7 días) | 52 | 13/11/2026 | 52 | OK |
| `energia_tiempo_real` | 1 | hoy | nacional | OK |
| `clima_diario` (NASA POWER) | 225.264 | 2015-01-01 → 2026-11-10 | 52 | OK (249 s) |
| `free_cooling` (NASA POWER horario) | 7.436 | 2015-01 → 2026-11 | 52 | OK (358 s) |
| `reservas_ambito_mensual` (MITECO) | 7.473 | 1987-10 → 2026-11 | 16 ámbitos | OK (48 s) |
| `estres_hidrico_wri` | 52 | estática | 52 (CCAA) | OK |
| `ccaa_demanda` | 2.672 | 2015-01 → 2026-11 | 19 CCAA | OK |
| `ccaa_generacion` | 2.672 | 2015-01 → 2026-11 | 19 CCAA | OK |
| `co2` | 143 | 2015-01 → 2026-11 | N | OK |
| `precios_diarios` | 4.336 | 2015-01-01 → 2026-11-14 | N | OK |
| `poblacion` | 1.560 | 1996 → 2025 (2022–2025 del padrón) | 52 | OK |
| `renta` | 508 | 2015 → 2024 | 52 | OK |
| `paro` | 7.332 | 2015-01 → 2026-10 | 52 | OK |
| `conectividad` | 52 | estática | 52 | OK |
| `capacidad_ccaa` | 18 | último CSV REE | 18 CCAA | OK |
| `subestaciones` | 52 | estática | 52 | OK |
| `sismos` | 452 | 2015 → 2026 | 52 | OK |
| `natura` | 52 | estática | 52 | OK |
| `panel_provincia_mes` | 7.384 (52 × 142) | 2015-01 → 2026-10 | 52 | 51 columnas |
| `provincias_actual` | 52 | — | 52 | 66 columnas |

Cobertura del panel (% de filas con dato): clima mensual (medias, precipitación, ET0, balance, free-cooling) 100 %;
población 93,0 %; reservas de embalses 90,4 % (las 5 provincias sin ámbito quedan vacías: Baleares, Canarias, Ceuta
y Melilla); índice de sequía 92,3 % (los primeros 11 meses de cada provincia no tienen ventana completa); paro 99,3 %;
demanda y % renovable por CCAA 98,7 %; renta 82,6 %; estrés WRI 100 %.

En `provincias_actual` solo quedan vacíos los campos de ámbito y reservas (5 provincias sin ámbito), las 2 provincias
sin dato de magnitud sísmica máxima y 1 sin capacidad de acceso (Melilla).

Pruebas: `python -m pytest -q` → 105 pasan (84 previos y 21 nuevos en `tests/test_datos_nuevos.py`, con fixtures sin conexión).

Dependencias añadidas a `requirements.txt`: `access-parser==0.0.6` (lector Python puro de ficheros Access; ya
se usaba con su dependencia `construct==2.10.70` y `tabulate==0.10.0`).
