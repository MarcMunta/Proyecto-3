# Tablas por API · provincias de España

Capa de datos **actualizable por API** (no depende de descargas puntuales). Cada tabla se obtiene de una
fuente pública programática, se cachea en `data/raw/api/<fuente>/` y se guarda como tabla larga en
`data/curated/tablas/`. Las dos salidas para modelar son `panel_provincia_mes` y `provincias_actual`.

Actualizar: `python -m cpd.fuentes.actualizar` (completo, incremental) o `--rapido` (solo tiempo real).

Clave común: `codigo_provincia` (código INE de dos dígitos, `01`–`52`, incluidos Ceuta `51` y Melilla `52`).
Granularidad de cada tabla: **P** = provincia, **CCAA** = comunidad autónoma (se hereda a sus provincias),
**N** = nacional (se repite en todas las provincias).

## 1. Tablas base

| Tabla (`data/curated/tablas/`) | Columnas | Unidades | Fuente / endpoint | Gran. | Actualización | Historia obtenida | Filas | Modelos |
|---|---|---|---|---|---|---|---|---|
| `provincias` | codigo_provincia, provincia, codigo_ccaa, ccaa, ree_geo_id, lat_punto, lon_punto | — | Tabla maestra (INE 01–52, GISCO) | P | estática | — | 52 | Clave de todo |
| *(polígonos)* `data/raw/api/provincias/poligonos_provincias.geojson` | geometría por provincia | WGS84 | GISCO LAU 2024, disuelto por provincia | P | estática | — | 52 | Asignación de puntos |

## 2. Clima (Open-Meteo)

| Tabla | Columnas | Unidades | Endpoint | Gran. | Actualización | Historia | Modelos |
|---|---|---|---|---|---|---|---|
| `clima_diario` | fecha, codigo_provincia, tmax_c, tmin_c, tmedia_c, humedad_relativa_media_pct, precipitacion_mm, viento_medio_kmh, et0_mm | °C, %, mm, km/h, mm | `archive-api.open-meteo.com/v1/archive` (ERA5, daily) | P | diaria (hasta ayer) | desde 2015 | M2, M6, M10 |
| `free_cooling` | mes, codigo_provincia, horas_free_cooling, horas_con_dato, pct_horas_free_cooling | h, % | `archive-api` (ERA5, hourly `temperature_2m`) | P | mensual | desde 2015 | M1, M6 |
| `clima_actual` | codigo_provincia, momento_observacion, temperatura_actual_c, humedad_relativa_actual_pct, viento_actual_kmh, precipitacion_actual_mm | °C, %, km/h, mm | `api.open-meteo.com/v1/forecast` (`current`) | P | tiempo real | — | Predicción en vivo |

Free-cooling = horas del mes con temperatura del aire < 18 °C (serie horaria ERA5).

## 3. Energía (Red Eléctrica · REData, `apidatos.ree.es`)

| Tabla | Columnas | Unidades | Endpoint | Gran. | Actualización | Historia | Modelos |
|---|---|---|---|---|---|---|---|
| `ccaa_demanda` | codigo_ccaa, ree_geo_id, ccaa, fecha, demanda_mwh | MWh | `demanda/evolucion` (`geo_limit=ccaa`, mensual) | CCAA | mensual | desde 2015 | M2 |
| `ccaa_generacion` | codigo_ccaa, fecha, generacion_total_mwh, generacion_renovable_mwh, pct_renovable | MWh, % | `generacion/estructura-generacion` (`geo_limit=ccaa`) | CCAA | mensual | desde 2015 | M2, M9 |
| `co2` | fecha, emisiones_co2_tco2eq | tCO2 eq. | `generacion/no-renovables-detalle-emisiones-CO2` | N | mensual | desde 2015 | M9 |
| `precios_diarios` | fecha, precio_spot_eur_mwh, precio_pvpc_eur_mwh | €/MWh | `mercados/precios-mercados-tiempo-real` (`time_trunc=hour`, por meses; medias diarias) | N | diaria | desde 2015 | M2, M7 |
| `energia_tiempo_real` | momento_consulta, demanda_tiempo_real_mw, momento_demanda, precio_spot_actual_eur_mwh, precio_spot_manana_medio_eur_mwh | MW, €/MWh | `demanda/demanda-tiempo-real`; spot de REData; OMIE `marginalpdbc` (día siguiente) | N | tiempo real | — | M2 (predicción de precio y demanda) |
| `capacidad_ccaa` | codigo_ccaa, ccaa, nudos, capacidad_demanda_rdt_disponible_mw | MW | CSV de REE "capacidad de acceso" (`*_GRT_demanda.csv`), columna *demanda, criterio general RdT* | CCAA | mensual (REE) | última publicación | M1 |

Notas: la API de REData responde 400/502 "Error interno" de forma intermitente (se reintenta). Los precios
solo funcionan con `time_trunc=hour`. Las emisiones de CO2 no tienen desglose por CCAA (se usa el total nacional).
Melilla no aparece en la capacidad de acceso (sin nudos en el fichero).

## 4. Demografía, economía y empleo (INE, SEPE)

| Tabla | Columnas | Unidades | Fuente | Gran. | Actualización | Historia | Modelos |
|---|---|---|---|---|---|---|---|
| `poblacion` | codigo_provincia, anio, poblacion | habitantes | INE Tempus3, tabla 2852 | P | anual | desde 1996 | M8, M9 |
| `renta` | codigo_provincia, anio, renta_neta_media_persona_eur, renta_neta_media_hogar_eur, mediana_renta_unidad_consumo_eur | € | INE Tempus3, tabla 53689 (ADRH) | P | anual | 2015–2024 | M8, M9 |
| `paro` | codigo_provincia, mes, paro_registrado, municipios | personas | SEPE datos abiertos (`Paro_por_municipios_AÑO_csv`), suma de municipios | P | mensual | desde 2015 | M8 |

El paro es **paro registrado** (oficina de empleo), no la tasa EPA. `paro_por_1000_hab` = paro / población del año × 1000.

## 5. Conectividad y red

| Tabla | Columnas | Unidades | Fuente | Gran. | Actualización | Modelos |
|---|---|---|---|---|---|---|
| `conectividad` | codigo_provincia, n_centros_datos, n_ixp, distancia_ixp_km | nº, km | PeeringDB `api/fac?country=ES` (asignación por coordenadas o ciudad) y `api/ix?country=ES` (por ciudad) | P | semanal (estática) | M3 (etiqueta `cpd_existentes`) |
| `subestaciones` | codigo_provincia, subestaciones_220_400kv, subestaciones_400kv | nº | OpenStreetMap vía Overpass (`power=substation`, voltaje 220/400 kV) | P | estática | M1, M3 |

Los IXP no tienen coordenadas en PeeringDB: se asignan a provincia por ciudad y la distancia es aproximada
(de la capital de la provincia a la capital donde está el IXP más cercano).

## 6. Riesgos naturales y suelo

| Tabla | Columnas | Unidades | Fuente | Gran. | Actualización | Historia | Modelos |
|---|---|---|---|---|---|---|---|
| `sismos` | codigo_provincia, anio, n_terremotos, magnitud_max, n_terremotos_m3_plus | nº, Mw/ML | EMSC FDSN `fdsnws/event/1/query` (M≥1.5 en una caja que cubre España), asignación por polígono | P | anual | desde 2015 | M5 |
| `natura` | codigo_provincia, pct_superficie_natura2000, espacios_natura_2000 | %, nº | EEA Natura 2000, ArcGIS REST (`ProtectedSites/Natura2000Sites`), recorte con el polígono provincial | P | estática | — | M4 (restricción Natura 2000) |

Los terremotos fuera de cualquier polígono provincial (mar, Portugal, Marruecos, Argelia) no se asignan.
Dentro del rango descargado, la ausencia de eventos cuenta como 0 y no como dato faltante.

## 7. Tablas de salida

### 7.1 `panel_provincia_mes` (entrenamiento)

Filas: 52 provincias × meses desde **2015-01** hasta el último mes con datos. Columnas: `codigo_provincia`, `mes`,
`provincia`, `ccaa`, `codigo_ccaa` y las variables de las secciones anteriores. Donde una fuente no tiene dato → **NaN**.

Tipos de variable (ver diccionario en `data/curated/diccionario_panel_provincia_mes.csv`):
- **Mensual** (clima, demanda, paro): varía cada mes.
- **Ccaa/nacional**: la demanda y generación son de la comunidad; CO2 y precios son nacionales y se repiten en todas las provincias.
- **Anual** (población, renta, sismos): se repite en los meses de su año.
- **Estática** (centros de datos, subestaciones, capacidad, Natura 2000): foto de la descarga; se repite en todos los meses.
  Úsese como variable de corte, no como serie temporal.

### 7.2 `provincias_actual` (predicción y etiquetas)

52 filas. Para cada variable, el **último valor disponible** de la provincia (puede venir de meses distintos según la fuente;
la columna `mes_referencia_panel` indica el último mes del panel). Campos de tiempo real: `temperatura_actual_c`,
`humedad_relativa_actual_pct`, `viento_actual_kmh`, `precipitacion_actual_mm`, `momento_observacion` (por capital),
`demanda_tiempo_real_mw`, `precio_spot_actual_eur_mwh`, `precio_spot_manana_medio_eur_mwh` (nacionales).
`cpd_existentes` = centros de datos en PeeringDB (etiqueta positiva).

## 8. Fuentes no usadas o pendientes

| Fuente | Motivo |
|---|---|
| ESIOS (REE, precios y demanda oficiales) | Requiere token; no disponible. Mejora opcional. |
| AEMET (observación y climatología oficial) | Requiere clave de API. Mejora opcional. |
| MITECO · embalses (`BD-Embalses.zip`, Access) | El controlador ODBC de Microsoft Access no está instalado en esta máquina (solo SQL Server). Se usa en su lugar el clima (precipitación, ET0) como proxy de agua. |
| MITECO · SNCZI (zonas inundables) | Certificado SSL roto. No se desactiva la verificación TLS. Pendiente. |
| Renta por municipio, EPA por provincia | No incluidas en esta capa. |

## 9. Limitaciones

- Estáticas (conectividad, subestaciones, capacidad, Natura 2000): sin histórico; un modelo no puede aprender su evolución.
- Subestaciones de OpenStreetMap: recuento de lo mapeado, no inventario de REE; cobertura desigual entre provincias.
- Capacidad de acceso: solo nivel CCAA y solo el último mes publicado.
- Demanda y generación por CCAA a nivel mensual: no hay consumo por provincia en las fuentes abiertas.
- Precios: nacionales; no hay precio por zona.
- Paro registrado (SEPE): no es tasa EPA.
- Clima ERA5: reanálisis con ~5 días de retraso; el mes en curso está incompleto (`dias_con_clima`).
- Polígonos provinciales: derivados de municipios LAU 2024 y simplificados (~200 m); las capitales son puntos representativos.
- Overpass, PeeringDB, EMSC y Natura: disponibilidad variable. Si una fuente falla, sus columnas quedan NaN y el resumen lo indica.

## 10. Resultado de la última actualización

Ejecución del 13/11/2026 (`python -m cpd.fuentes.actualizar`, 390 s):

| Tabla | Filas | Rango | Provincias | Estado |
|---|---|---|---|---|
| `provincias` | 52 | — | 52 | OK |
| `clima_actual` (tiempo real) | 52 | 13/11/2026 | 52 | OK |
| `energia_tiempo_real` | 1 | hoy | nacional | OK (demanda 34.283 MW; precio spot de mañana medio 169,5 €/MWh vía OMIE) |
| `clima_diario` (ERA5) | 0 | — | — | **FALLO**: límite diario de Open-Meteo (HTTP 429, "try again tomorrow") |
| `free_cooling` (ERA5 horario) | 0 | — | — | **FALLO**: mismo límite diario |
| `ccaa_demanda` | 2.672 (CCAA × mes) | 2015-01 → 2026-11 | 19 CCAA | OK |
| `ccaa_generacion` | 2.672 | 2015-01 → 2026-11 | 19 CCAA | OK (incluye % renovable) |
| `co2` | 143 | 2015-01 → 2026-11 | nacional | OK |
| `precios_diarios` | 4.336 días | 2015-01-01 → 2026-11-14 | nacional | OK |
| `poblacion` | 1.300 | 1996 → 2021 | 52 | OK (la tabla INE publicada termina en 2021) |
| `renta` | 508 | 2015 → 2024 | 52 | OK |
| `paro` | 7.332 | 2015-01 → 2026-10 | 52 | OK |
| `conectividad` | 52 | estática | 52 | OK (70 centros de datos, 15 IXP asignados) |
| `capacidad_ccaa` | 18 | último CSV de REE (03/11/2026) | 18 CCAA | OK (Melilla sin nudos) |
| `subestaciones` | 52 | estática | 52 | OK (895 de 220/400 kV, 276 de 400 kV; caché de OSM) |
| `sismos` | 452 | 2015 → 2026 | 52 | OK |
| `natura` | 52 | estática | 52 | OK |
| `panel_provincia_mes` | 7.384 (52 × 142 meses) | 2015-01 → 2026-10 | 52 | 30 columnas; sin variables de clima hasta que se complete la descarga |
| `provincias_actual` | 52 | — | 52 | 52 con tiempo real y estáticas |

Cobertura del panel (% de filas con dato): paro 99,3 %; demanda y % renovable por CCAA 98,7 %; capacidad de acceso 98,1 %;
renta 82,6 %; población 59,2 % (límite de la tabla INE). Las columnas de clima y free-cooling quedan vacías hasta la siguiente ejecución.

**Pendiente:** volver a ejecutar `python -m cpd.fuentes.actualizar` cuando se renueve la cuota diaria de Open-Meteo
para completar `clima_diario` y `free_cooling` (las cachés de años cerrados se reutilizan; el resto de fuentes no se vuelve a pedir).

