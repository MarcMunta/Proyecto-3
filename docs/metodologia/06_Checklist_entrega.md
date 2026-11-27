---
tags: [metodologia, checklist, entrega, p3]
estado: borrador
actualizado: 2026-11-27
---

# 06 · Checklist de entrega

Volver a [[00_Indice]]. Ver también [[07_Estado_actual]] (resumen y plan) y [[03_Flujo_de_trabajo]] (cómo cerrar cada fila).

**Leyenda:** ✅ hecho (hay evidencia verificable) · 🟡 parcial (existe algo incompleto o sin validar) · ❌ pendiente (no encontrado en el repositorio).
**Evidencia:** ruta de archivo en el repo, o "—" si no hay.
**Responsable:** vacío hasta asignar en la fase 0.
**Estado verificado:** 17/11/2026, rama `fix/mapa-revision` (EDA, features, modelos y métricas; sin commit todavía).

Las filas marcadas con `C1`…`C5` son técnicas de las clases (ver [[Clase_2026-10-02_Data_Relation_Modelling]], [[Clase_2026-10-09_Data_Visualization_Correlation]], [[Clase_2026-10-23_Forecasting_Metricas]], [[Clase_2026-11-13_Advanced_Feature_Engineering]], [[Clase_2026-11-27_Data_Engineering]]).

> Cómo se actualiza: al cerrar una tarea, cambiar el estado, poner la evidencia (ruta o commit) y escribir la siguiente acción.
> La columna "Siguiente acción" dice qué hace falta para pasar a ✅.

## Resumen de conteos

| Sección | ✅ | 🟡 | ❌ | Total |
|---|---|---|---|---|
| A. Objetivo general | 1 | 2 | 0 | 3 |
| B. Objetivos específicos (1-10) | 3 | 7 | 0 | 10 |
| C. Preguntas funcionales (P1-P8) | 5 | 3 | 0 | 8 |
| D. Variables del CPD (enunciado) | 13 | 3 | 9 | 25 |
| E. Variables del entorno territorial (enunciado) | 14 | 22 | 11 | 47 |
| F. Entregables y evidencias | 0 | 5 | 4 | 9 |
| G. Rúbrica (nivel 6) | 0 | 2 | 1 | 3 |
| H. Resultados de aprendizaje (RA) | 0 | 2 | 7 | 9 |
| I. Técnicas de clase y de calidad de datos | 63 | 13 | 13 | 89 |
| **Total** | **99** | **59** | **45** | **203** |

Conteos verificados el 27/11/2026 contando las celdas de estado de cada fila (con un script). Si se añaden filas, recalcular.

---

## A. Objetivo general (enunciado, p. 2)

| ID | Requisito | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| A1 | Plataforma Big Data para analizar y predecir la viabilidad de instalar un CPD en cualquier municipio español | 🟡 | `src/cpd/`, `app/streamlit_app.py`, `frontend/` | | Contexto municipal INE/GISCO en DuckDB y mapa. Quedan pendientes elegibilidad y ranking municipal. |
| A2 | Proporcionar una puntuación global de viabilidad | 🟡 | `src/cpd/scoring.py` (`calcular_score_global`) | | Calibrar pesos y umbrales (`config/settings.yaml`) |
| A3 | Generar previsiones a corto y medio plazo sobre la sostenibilidad operativa del CPD | ✅ | Corto plazo: `src/cpd/modelos/operacion.py` (PUE, consumo, emisiones, agua y reserva mínima del ámbito a 1 año por provincia, de punta a punta: consumo 99,7 %, emisiones 90,6 %; figura 14). Medio plazo: `src/cpd/modelos/medio_plazo.py` (10 años: temperatura por provincia 97,7 % validación / 94,8 % test con NASA POWER desde 1981 → PUE → consumo 99,8 % / 99,5 %; reserva media de la década por ámbito 91,1 % / 86,6 %; año a año 83,3 % / 81,9 %, orientativo); figura 16 en `docs/analisis/previsiones_1_anio.md`, línea «A 10 años» en la ficha del mapa; `tests/test_modelos.py` (sin fuga, validación antes del test) | | Emisiones a 10 años no validables (mix por comunidad solo desde 2015) |

## B. Objetivos específicos (enunciado, p. 2-3)

| ID | Requisito | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| B1 | Identificar y recopilar fuentes de datos relevantes | 🟡 | `docs/datos/README.md`, `docs/datos/tablas_api.md`, `src/cpd/fuentes/`; MIBGAS (gas, `src/cpd/fuentes/mibgas.py`) | | Integrar AEMET, Confederaciones Hidrográficas y CNMC o justificar sustitución (D2) |
| B2 | Diseñar procesos ETL para integrar datos heterogéneos | 🟡 | `src/ingesta/01_…04_*.py`, `src/cpd/fuentes/actualizar.py`, `src/cpd/etl/ree.py` | | Publicación versionada en src/cpd/publicar.py y prueba de rechazo en tests/test_publicar.py. |
| B3 | Limpiar, transformar y validar los datos obtenidos | 🟡 | `src/cpd/fuentes/curado.py` (criterio NaN), `src/cpd/fuentes/calidad.py` (control de calidad de la demanda), `tests/test_datos_nuevos.py`, `tests/test_fuentes.py` | | Controles de claves, meses y cobertura por granularidad en src/cpd/fuentes/validacion.py. Queda completar el informe por fuente. |
| B4 | Diseñar un Data Lake y un Data Warehouse | 🟡 | `data/raw/`, `data/almacen/p3_cpd.duckdb`, `src/cpd/almacen.py` | | Vistas por CCAA, cuenca y ámbito nacional en src/cpd/almacen.py. Documento docs/datos/almacenamiento.md. |
| B5 | Realizar análisis exploratorio de datos | 🟡 | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py` (histogramas, box plots, series, barras, dispersión, correlaciones, pair plot; `python -m cpd.modelos`) | | Notebook `notebooks/01_eda_panel.ipynb` que llame a `cpd.modelos.eda` (la fase 4 lo pide) |
| B6 | Detectar correlaciones entre variables territoriales y la viabilidad | ✅ | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py` §5: Pearson y Spearman frente a nº de CPD, score y VAN simulados | | — |
| B7 | Construir modelos predictivos mediante Machine Learning | ✅ | `docs/modelos/demanda_ccaa.md`, `src/cpd/modelos/demanda.py`; `docs/modelos/prob_cpd.md`, `src/cpd/modelos/prob_cpd.py`; `docs/analisis/metricas.md` ; 18/11/2026: PIB provincial y población + renta probados y descartados (bajan el acierto con umbral a 84,6 %); la población con **target encoding de la comunidad** mejora todo (log-loss 0,316, ROC-AUC 0,925, acierto 92,3 %) y es el nuevo elegido | | Validación geográfica de presencia de CPD y diagnóstico por horizonte en src/cpd/modelos/. |
| B8 | Diseñar un simulador capaz de evaluar distintos escenarios | 🟡 | `src/cpd/simulator.py`, `scoring.preparar_escenario`, `app/streamlit_app.py` | | Estado técnico pendiente, auditoría de filtros y punto de equilibrio. Queda ampliar escenarios reales con datos de emplazamiento. |
| B9 | Crear dashboards interactivos para la toma de decisiones | 🟡 | `app/streamlit_app.py` (6 pestañas), `frontend/` (mapa) | | Panel derecho con dictamen, finanzas y modelos de la zona. Catálogo de 25 evaluaciones en el mismo panel. Queda validar con un usuario. |
| B10 | Elaborar predicciones de evolución futura mediante series temporales | ✅ | `docs/analisis/previsiones_1_anio.md`, `src/cpd/modelos/anual.py` (previsión a 1 año de la demanda, el precio, las reservas de agua, la temperatura por provincia y el % renovable por comunidad, backtesting con 24 orígenes, ETS, ML y combinación); `docs/modelos/demanda_ccaa.md`, `docs/modelos/precio_luz.md`; control de acierto D8 (`data/curated/modelos/control_acierto.csv`) | | Cada serie muestra su alcance territorial junto a la salida de la zona. Al desplegar se ven la validación, prueba y fórmulas generales. La fila del precio muestra los dos aciertos retrospectivos. |

## C. Preguntas funcionales (enunciado, p. 3; ver [[01_Objetivo_y_alcance]])

| ID | Pregunta | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| P1 | ¿Qué municipios son los más adecuados? | 🟡 | `src/cpd/scoring.py` (`evaluar`, ranking) | | Dimensión municipal con INE y GISCO. Clasificación real disponible por provincia. |
| P2 | ¿Qué impacto tendrá el CPD sobre los recursos locales? | ✅ | `src/cpd/modelos/impacto_local.py`: consumo previsto del CPD sobre la demanda prevista de su comunidad (validación de punta a punta 96,1 %, 20 orígenes), potencia máxima sobre la capacidad de acceso libre (REE; 0 MW en Madrid, Navarra y Ceuta: no cabe) y agua sobre la distribuida por la red pública de su comunidad (INE tabla 53447, 2024), con habitantes equivalentes; figura 17, ficha del mapa; `tests/test_modelos.py` | | Escala de comunidad: no hay consumo eléctrico ni de agua abierto por municipio (E8, E14) |
| P3 | ¿Existe suficiente disponibilidad energética? | 🟡 | `panel`: `nudos_acceso_ccaa`, `capacidad_demanda_rdt_disponible_mw`, `capacidad_demanda_rdt_otorgada_mw` y `_pendiente_mw` (REE, por comunidad); cobertura renovable prevista (generación renovable / demanda, `docs/analisis/previsiones_1_anio.md`), en el bloque de energía del score | | Nudos REE en DuckDB cuando están los CSV. Enlace a parcelas pendiente. |
| P4 | ¿Existe riesgo hídrico? | ✅ | `panel`: `estres_hidrico_wri_0_1`, `reserva_hidrica_pct`, `indice_sequia_12m`; previsión de reservas a 1 año por ámbito (acierto 85,3 % en test) en `docs/analisis/previsiones_1_anio.md`; reserva media de la próxima década por ámbito (acierto 86,6 % en test, `src/cpd/modelos/medio_plazo.py`) | | Afinar la asignación provincia → ámbito |
| P5 | ¿Cómo evolucionará la demanda eléctrica en los próximos 10 años? | ✅ | `src/cpd/modelos/largo_plazo.py`, `docs/analisis/previsiones_1_anio.md` §10 años (backtesting 2012-2025, acierto 97,3 %, intervalo 10-90 %) ; escenarios con la red otorgada (18.535 MW) y en trámite (23.500 MW) de REE sobre la tendencial (`src/cpd/modelos/escenarios.py`, figura 19): 2035 entre 244 TWh (tendencial) y 374 TWh (100 % de lo otorgado); Aragón tiene otorgado el 243 % de su demanda | | Calibrar la realización de lo otorgado (sin dato abierto) |
| P6 | ¿Cuál será el coste operativo esperado? | ✅ | `simulator.opex_eur`, `desglose_opex`; `tests/test_simulator.py`; precio de la luz previsto y su rango en `docs/modelos/precio_luz.md`; temperatura media por provincia a 1 año (la que usa el PUE; acierto 92,8-93,8 %, error de la media anual 0,5 °C) en `docs/analisis/previsiones_1_anio.md` | | Calibrar precios en `config/settings.yaml` y documentar |
| P7 | ¿Cuál será el retorno de inversión estimado? | ✅ | `simulator.van`, `roi`, `payback_anos`; tests; sensibilidad del VAN al precio de la luz en la ficha del mapa (`frontend/scripts/simular_provincias.py`) | | Sensibilidad del VAN y precio de equilibrio en mapa y Streamlit. Documentar supuestos comerciales. |
| P8 | ¿Qué zonas presentan menor riesgo regulatorio o ambiental? | 🟡 | `scoring.aplicar_filtros` (Natura 2000, inundación, sísmico); peligrosidad sísmica oficial (NCSE-02) por provincia en el filtro y el score; modelo de riesgo sísmico anual (`src/cpd/modelos/sismico.py`, no cumple, no se usa) | | Verificar la fuente de zonas inundables |

## D. Variables del CPD (enunciado, p. 2-4)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| D1 | Superficie construida (m²) | ❌ | — | | Añadir a `CPDParams` y al cálculo de ocupación |
| D2 | Número de salas técnicas | ❌ | — | | Añadir a `CPDParams` |
| D3 | Número de racks | ❌ | — | | Añadir a `CPDParams` |
| D4 | Número de servidores | ❌ | — | | Añadir a `CPDParams` |
| D5 | Potencia TI instalada (MW) | ✅ | `simulator.CPDParams.potencia_ti_mw` | | — |
| D6 | Capacidad de almacenamiento (PB) | ❌ | — | | Añadir a `CPDParams` |
| D7 | Capacidad de proceso (TFLOPS) | ❌ | — | | Añadir a `CPDParams` |
| D8 | Nivel de redundancia (Tier I-IV) | 🟡 | `CPDParams.tier` (solo informativo) | | Usar el tier en un cálculo o en un filtro |
| D9 | Consumo anual previsto (MWh) | ✅ | `simulator.consumo_anual_mwh` | | — |
| D10 | Potencia máxima demandada | ✅ | `simulator.potencia_total_mw` | | — |
| D11 | PUE | ✅ | `CPDParams.pue`, `simulator.pue_estimado` | | — |
| D12 | Porcentaje de energía renovable requerida | ✅ | `CPDParams.pct_renovable` | | — |
| D13 | Producción fotovoltaica propia | 🟡 | `CPDParams.autoproduccion_mwh` (una sola cifra) | | Separar FV y eólica o documentar que es agregada |
| D14 | Producción eólica propia | 🟡 | `CPDParams.autoproduccion_mwh` (una sola cifra) | | Igual que D13 |
| D15 | Litros/día para refrigeración | ✅ | `simulator.agua_l_dia` | | — |
| D16 | Tipo de refrigeración (aire, evaporativa, adiabática, inmersión líquida) | ✅ | `CPDParams.tipo_refrigeracion` | | Convertir en `enum` (I9) |
| D17 | WUE | ✅ | `CPDParams.wue_l_kwh` | | — |
| D18 | Tráfico medio esperado (Gbps) | ❌ | — | | Añadir a `CPDParams` |
| D19 | Tráfico pico esperado | ❌ | — | | Añadir a `CPDParams` |
| D20 | Número de operadores requeridos | ❌ | — | | Añadir a `CPDParams` |
| D21 | Latencia máxima admisible | ✅ | `CPDParams.latencia_max_ms`, `simulator.latencia_rtt_ms`, filtro | | — |
| D22 | Inversión inicial | ✅ | `CPDParams.inversion_eur` | | — |
| D23 | Costes operativos esperados | ✅ | `simulator.opex_eur` | | — |
| D24 | Vida útil prevista | ✅ | `CPDParams.vida_util_anos` | | — |
| D25 | Personal necesario | ✅ | `CPDParams.personal` | | — |


## E. Variables del entorno territorial (enunciado, p. 4-6)

### E.1 Demografía (fuentes: INE, datos abiertos de CCAA)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E1 | Población | ✅ | `panel`: `poblacion` | | — |
| E2 | Densidad de población | 🟡 | Municipal en `data/raw/municipios/` (GISCO); no en el panel | | Añadir densidad provincial |
| E3 | Evolución demográfica | 🟡 | Serie de `poblacion` en el panel | | Calcular tasa de variación anual |
| E4 | Tasa de envejecimiento | 🟡 | `data/raw/demografia/ine_adrh_demograficos_30832.csv` (sin integrar) | | Integrar en el panel |
| E5 | Tasa de desempleo | 🟡 | `paro_registrado`, `paro_por_1000_hab` (no es tasa de paro sobre activos) | | Documentar la diferencia o calcular la tasa |
| E6 | Nivel educativo | 🟡 | `data/raw/demografia/ine_censo2021_estudios_*.csv` (municipal, sin integrar) | | Integrar a nivel provincial |

### E.2 Energía (fuentes: Red Eléctrica, MITECO)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E7 | Producción eléctrica disponible | 🟡 | `generacion_total_ccaa_mwh` (CCAA, no provincia); generación de España por tecnología (`generacion_nacional_detalle`, eólica, solar, hidráulica, nuclear, ciclo combinado, carbón) y su previsión a 1 año (`gas_tiempo.py`, inestable); generación renovable prevista a 1 año por comunidad (mes a mes 86,2 % y total de 12 meses 92,3-93,5 %, con la suma de tecnologías y la hidráulica desde los embalses) | | Documentar nivel CCAA |
| E8 | Consumo eléctrico municipal | 🟡 | `demanda_ccaa_mwh` (CCAA); sin dato municipal abierto (ver `docs/datos/README.md`) | | Documentar la limitación |
| E9 | Capacidad de la red | 🟡 | `nudos_acceso_ccaa`, `capacidad_demanda_rdt_disponible_mw` | | Revisar cobertura territorial |
| E10 | Subestaciones cercanas | 🟡 | `subestaciones_220_400kv`, `subestaciones_400kv` (OSM) | | Distancia a la subestación más cercana, no solo conteo |
| E11 | Capacidad de transporte | 🟡 | `capacidad_demanda_rdt_disponible_mw` | | Aclarar si es transporte o acceso |
| E12 | Porcentaje de renovables | ✅ | `pct_renovable_ccaa`; previsión a 1 año por comunidad en `docs/analisis/previsiones_1_anio.md` (% medio de 12 meses: acierto 89,4-92,2 %; mes a mes 84,8 %, orientativo) | | Mejorar el mes a mes (viento, lluvia y sol del mes no se pueden prever a 1 año) |

### E.3 Agua (fuentes: Confederaciones Hidrográficas, MITECO, AEMET)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E13 | Disponibilidad hídrica | 🟡 | `reserva_hidrica_pct`, `reserva_hidrica_hm3` (por ámbito) | | Explicar relación con disponibilidad real |
| E14 | Consumo hídrico municipal | 🟡 | Por comunidad: INE «Estadística sobre el suministro y saneamiento del agua» (tabla 53447, bienal 2014-2024: suministrada, registrada y distribuida, pérdidas), `ine.agua_ccaa`, `agua_ccaa.csv` | | No hay dato municipal abierto: documentado |
| E15 | Embalses cercanos | 🟡 | Reserva por ámbito hidrográfico (MITECO) | | Asociar embalse al municipio o provincia |
| E16 | Estrés hídrico | ✅ | `estres_hidrico_wri_0_1` (WRI Aqueduct) | | — |
| E17 | Sequías históricas | 🟡 | `indice_sequia_12m` (suma de 12 meses, no índice oficial) | | Documentar que no es SPI oficial |
| E18 | Calidad del agua | ❌ | — | | Buscar fuente (CCHH, MITECO) |

### E.4 Climatología (fuentes: AEMET en el enunciado; NASA POWER y Open-Meteo en el repo)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E19 | Temperatura media anual | 🟡 | `tmedia_mes_c` (mensual); media de los últimos 12 meses y de los 12 previstos por provincia en `data/curated/modelos/previsiones_1_anio.json` (`temperatura`) | | Añadir la media anual al panel provincial |
| E20 | Temperatura máxima histórica | 🟡 | `tmax_media_c` (media de máximas, no máximo histórico) | | Añadir máximo histórico |
| E21 | Humedad relativa | ✅ | `humedad_relativa_media_pct` | | — |
| E22 | Número de días de calor extremo | ✅ | `dias_mas_35c` (umbral 35 °C) | | Justificar el umbral de "extremo" |
| E23 | Velocidad media del viento | ✅ | `viento_medio_kmh` | | — |
| E24 | Horas de free cooling (justificación del brief: un clima frío reduce costes de refrigeración) | ✅ | `horas_free_cooling`, `pct_horas_free_cooling` | | — |

### E.5 Infraestructuras de telecomunicaciones (fuentes: CNMC, Secretaría de Estado de Telecomunicaciones)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E25 | Cobertura de fibra óptica | ❌ | — | | Buscar fuente CNMC |
| E26 | Troncales de comunicaciones | ❌ | — | | Buscar fuente (OSM, Secretaría de Estado) |
| E27 | Puntos neutros de Internet | 🟡 | `n_ixp`, `distancia_ixp_km` (PeeringDB) | | Documentar fuente alternativa |
| E28 | Distancia a nodos principales | 🟡 | `distancia_ixp_km` (IXP más cercano) y `distancia_hubs_ixp_km` (al más lejano de los dos grandes nodos: las provincias con más IXP en PeeringDB, hoy Madrid y Barcelona), en el bloque de conectividad del score | | Rutas reales de fibra (hoy, línea recta × 1,5) |
| E29 | Cobertura 5G | ❌ | — | | Buscar fuente CNMC |

### E.6 Transporte y logística (fuentes: OSM u otras)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E30 | Distancia a autopistas | ❌ | — (en la lista de pendientes de `docs/datos/README.md`) | | Descargar OSM y calcular distancia |
| E31 | Distancia a puertos | ❌ | — | | Igual |
| E32 | Distancia a aeropuertos | ❌ | — | | Igual |
| E33 | Accesibilidad logística | ❌ | — | | Definir índice (recomendación) |

### E.7 Suelo disponible (enunciado, p. 6-7)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E34 | Precio del suelo industrial | 🟡 | `precio_suelo_urbano_eur_m2` (Ministerio de Transportes, «Precios de suelo», tabla 4; mediana de 4 trimestres; `src/cpd/fuentes/suelo.py`), en el bloque de suelo del score | | Es suelo urbano, no industrial: por eso no entra en el CAPEX. Buscar precio industrial abierto |
| E35 | Disponibilidad de parcelas | ❌ | — | | Buscar fuente |
| E36 | Calificación urbanística | ❌ | — | | Buscar fuente (planeamiento municipal) |
| E37 | Riesgos de inundación | 🟡 | Filtro "zona inundable" en `README.md` (fuente por verificar) | | Confirmar fuente y añadir a panel |
| E38 | Riesgo sísmico | ✅ | `aceleracion_sismica_capital_g`, `aceleracion_sismica_max_g`, `municipios_ab_008_o_mas` (norma NCSE-02, BOE, anejo 1; `src/cpd/fuentes/norma_sismica.py`) en el filtro de 0,16 g y el bloque de riesgos; `n_terremotos`, `magnitud_max`, `n_terremotos_m3_plus` (EMSC) | | Mapa del IGN 2015 si se publica por municipio |

### E.8 Impacto socioeconómico (enunciado, p. 7)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E39 | Empleo generado | ✅ | `src/cpd/modelos/socioeconomico.py`: modelo input-output de Leontief (tipo I) con las Tablas Input-Output 2022 del INE (`src/cpd/fuentes/ine_tio.py`, inversa interior y empleo ETC por rama): obra 3.402 empleos-año; operación 60 directos + 217 indirectos al año (×4,6); figura 18, ficha del mapa; tests con una economía sintética | | Calibrar el reparto del CAPEX (`config/settings.yaml`, supuesto) |
| E40 | Inversión inducida | ✅ | Mismo modelo: de 400 M€ de CAPEX se quedan en España 295 M€ (cuota de importación real por producto) y generan 562 M€ de producción y 217 M€ de VAB; operación 78 M€ de VAB al año | | Tipo II (gasto de los salarios), si se pide |
| E41 | PIB municipal | 🟡 | No hay PIB municipal abierto; PIB por provincia del INE (Contabilidad Regional, tabla 82284, `ine.pib_provincias`, `pib_provincia.csv`): VAB directo del CPD sobre el PIB provincial (de 0,01 % en Madrid a 2,5 % en Melilla) | | Documentado: el dato municipal no existe en abierto |
| E42 | Atracción empresarial | ✅ | Sociedades mercantiles constituidas por provincia y mes (INE, tabla 6295, 2008-2025; `ine.sociedades_provincias`) y su previsión a 1 año (`src/cpd/modelos/empresas.py`, combinación con candidatos por día hábil, `src/cpd/features/calendario.py`): mes a mes 88,3 % / 85,4 % y total de 12 meses 93,0 % / 92,1 %; indicador por 10.000 habitantes, figura 20 y ficha del mapa | | Indicador de dinamismo (recomendación, no viene de clase), fuera del score |

### E.9 Impacto ambiental (enunciado, p. 7)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E43 | Incremento del consumo energético local | ✅ | % del consumo previsto del CPD sobre la demanda prevista de su comunidad y habitantes equivalentes (`src/cpd/modelos/impacto_local.py`, 96,1 % en validación); `simulator.impacto_local_pct` queda para el dato municipal | | Municipal sin fuente abierta (E8) |
| E44 | Incremento del consumo hídrico | ✅ | % del agua anual del CPD sobre el agua registrada y distribuida de su comunidad (INE, tabla 53447) y habitantes equivalentes (`src/cpd/modelos/impacto_local.py`) | | — |
| E45 | Huella de carbono | ✅ | `simulator.co2_t` | | Documentar factor de emisión y alcance |
| E46 | Emisiones indirectas | 🟡 | `co2_t` (solo energía comprada) | | Aclarar alcance 2 y 3 |
| E47 | Ocupación del suelo | ❌ | — | | Calcular a partir de superficie (D1) |

## F. Entregables y evidencias (enunciado, p. 8)

| ID | Entregable / evidencia | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| F1 | Informe de origen de datos (M4RA1) | 🟡 | `docs/datos/README.md` (borrador) | | Completar con todas las fuentes y licencias |
| F2 | Informe de cuadro de mandos (M4RA2) | 🟡 | `docs/entrega/cuadro-de-mandos.md` | | Revisar con el equipo y adjuntar capturas. |
| F3 | Informe de análisis de los datos (M4RA2) | 🟡 | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py`, `docs/analisis/metricas.md` (generados) | | Redactar el informe final integrado (fases 4 y 8) |
| F4 | Informe de visualización de datos (M4RA4) | 🟡 | `docs/entrega/cuadro-de-mandos.md` | | Revisar en móvil y adjuntar capturas. |
| F5 | Documentación descriptiva del sistema de gestión y almacenamiento de datos (M4RA3) | ✅ | `src/cpd/almacen.py`, `docs/datos/tablas_api.md`, diccionarios en `data/curated/` | | Documento y esquema en `docs/datos/almacenamiento.md` |
| F6 | Código fuente con comentarios en las funciones principales, en control de versiones (M4RA1-M4RA4) | 🟡 | Git (`main`, commits); comentarios por función sin verificar | | Auditar docstrings de funciones principales |
| F7 | Vídeo del sistema funcional con diversos casos de prueba (M4RA1-M4RA4) | 🟡 | `docs/entrega/cuadro-de-mandos.md` | | Guion listo. Queda grabar el vídeo. |
| F8 | Manual de instalación y despliegue (M4RA1, M4RA3) | 🟡 | `docs/entrega/manual.md` | | Falta restaurar en un equipo limpio. |
| F9 | Manual de usuario final (M4RA2, M4RA4) | 🟡 | `docs/entrega/manual.md` | | Manual operativo. Queda revisar con un usuario. |

## G. Rúbrica (enunciado, p. 9-10; nivel 6 = excelente)

| ID | Criterio de nivel 6 | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| G1 | Documentación: descripción exhaustiva, detallada y profesional de todos los requisitos funcionales y no funcionales y del prototipo | 🟡 | Esta carpeta `docs/metodologia/`, `docs/datos/` | | Lista de requisitos no funcionales (rendimiento, seguridad, usabilidad) |
| G2 | Código fuente: repositorio completo, mantenible y perfectamente organizado, con buenas prácticas | 🟡 | `src/`, `tests/`, `config/`; 105 tests pytest y 7 vitest (según el encargo) | | Lint, tipos, `enum`, docstrings, eliminar `app/` antiguo si no se usa |
| G3 | Vídeo: variedad de casos de uso que demuestren funcionalidad y eficacia | ❌ | — | | Definir 3 o más casos (fase 11) |

## H. Resultados de aprendizaje (RA) citados en el enunciado

Las descripciones de los RA **no aparecen en el enunciado**; solo sus códigos. Antes de cerrar estas filas, pedir la
descripción oficial al profesor o a la guía de la asignatura.

| ID | RA | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| H1 | M4RA1 | 🟡 | Ingesta y origen de datos (F1, F6) | | Confirmar descripción del RA |
| H2 | M4RA2 | ❌ | Análisis y cuadro de mandos sin informe (F2, F3) | | Entregar informes |
| H3 | M4RA3 | 🟡 | Almacenamiento (F5) | | Documento de almacenamiento |
| H4 | M4RA4 | ❌ | Visualización sin informe (F4, F9) | | Informe de visualización y manual |
| H5 | M1RA5 | ❌ | Sin evidencia identificada en el repo | | Confirmar qué exige el RA |
| H6 | M1RA6 | ❌ | Sin evidencia identificada en el repo | | Confirmar qué exige el RA |
| H7 | M2RA3 | ❌ | Sin evidencia identificada en el repo | | Confirmar qué exige el RA |
| H8 | M2RA4 | ❌ | Sin evidencia identificada en el repo | | Confirmar qué exige el RA |
| H9 | M2RA5 | ❌ | Sin evidencia identificada en el repo | | Confirmar qué exige el RA |

## I. Técnicas de las clases y de la calidad de datos

Cada fila cita la clase y la página de la diapositiva (`C1 p.x`…`C4 p.x`). Las técnicas que el equipo considera
necesarias y que no vienen de clase aparecen marcadas como **(recomendación)**.

### I.1 Clase 02/10 · Data Modelling

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I1 | Tipos de datos: relacional, no relacional, tabular, no tabular (C1 p.3) | 🟡 | Tipos por fuente en `docs/datos/README.md` | | Añadir tabla de tipos en el informe de origen |
| I2 | Datos cualitativos y cuantitativos (C1 p.4) | ❌ | — | | Marcar cada variable del diccionario |
| I3 | Adquisición de datos desde open data (C1 p.5) | ✅ | INE, REE, MITECO, WRI, NASA POWER, Open-Meteo (`docs/datos/`) | | — |
| I4 | Adquisición de datos propios: foto, encuesta, registro (C1 p.5) | ❌ | — | | Decidir si se usa (no lo exige el enunciado) |
| I5 | Convertir todos los datos a un formato común (C1 p.5) | ✅ | `data/curated/panel_provincia_mes.csv` (51 columnas), `provincias_actual.csv` (66) | | — |
| I6 | Git: `fetch`, ramas `feature/…`, `pull --rebase`, `checkout -b` (C1 p.10-11) | 🟡 | Commits en `main`; sin PR ni ramas documentadas | | Aplicar [[05_Reglas_de_codigo_y_git]] desde ya |
| I7 | Equipo con roles: Dirección, Data Cleaners, Data Visualization, Data Filters, R&D (C1 p.9-10) | ❌ | — | | Asignar roles en fase 0 |
| I8 | Estructura: `data/`, `utils/`, `config/` (C1 p.12-13) | 🟡 | `data/`, `config/` existen; no hay `utils/` (las utilidades están en `src/`) | | Decidir y documentar (ver [[05_Reglas_de_codigo_y_git]]) |
| I9 | Enumeraciones (enums) (C1 p.13) | ❌ | Ninguna en `src/`, `app/`, `tests/` | | Crear enums para refrigeración, tier, estado de viabilidad |
| I10 | Justificar modelo relacional frente a no relacional (C1 p.3; examen C2 p.4) | ❌ | — | | Párrafo en la fase 5 |
| I11 | Grafos: nodos, aristas, influencers (examen C2 p.4) | ❌ | — (no es requisito) | | Decidir si se incluye (recomendación: no) |

### I.2 Clase 09/10 · Visualización y correlación

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I12 | Gráfico de líneas: evolución temporal (C2 p.6) | ✅ | `docs/figuras/eda/03_serie_demanda.png`, `04_series_precio_agua.png` | | — |
| I13 | Gráfico de barras: comparar categorías (C2 p.7) | ✅ | `docs/figuras/eda/05_barras_cpd.png` | | — |
| I14 | Histograma de variables numéricas (C2 p.8) | ✅ | `docs/figuras/eda/01_histogramas.png` | | — |
| I15 | Diagrama de dispersión (C2 p.9) | ✅ | `docs/figuras/eda/06_dispersion.png` | | — |
| I16 | Box plot: outliers, mediana y cuartiles (C2 p.10) | 🟡 | `docs/figuras/eda/02_boxplots.png` (temperatura y precio) | | Box plot del resto de variables en el informe de calidad (fase 2) |
| I17 | Mapa de calor de correlación (C2 p.11) | ✅ | `docs/figuras/eda/07_correlacion_pearson.png`, `08_correlacion_spearman.png` | | — |
| I18 | Gráfico de sectores (C2 p.12) | ❌ | — (no hay uso; recomendación: evitar) | | No aplica salvo caso puntual |
| I19 | Pair plot (C2 p.13) | ✅ | `docs/figuras/eda/09_pair_plot.png` | | — |
| I20 | Correlación de −1 a 1 y su interpretación (C2 p.15) | ✅ | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py` §5 | | — |
| I21 | Pearson: lineal, sensible a outliers (C2 p.23) | ✅ | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py` §5 | | — |
| I22 | Spearman: monótona, robusta (C2 p.23) | ✅ | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py` §5 (con comparación Pearson − Spearman) | | — |
| I23 | Kendall: muestras pequeñas (C2 p.23-24) | 🟡 | `cpd.modelos.eda.correlaciones` (calcula Kendall) | | Mostrar la tabla de Kendall en el informe |
| I24 | Correlación no implica causalidad (C2 p.18-21) | ✅ | `docs/analisis/eda_panel.md`, `src/cpd/modelos/eda.py` §5 y §8 | | — |
| I25 | Ejercicio de examen (Q1 a Q4) (C2 p.4) | ❌ | Ejercicio de clase, no entregable de P3 (sin hacer) | | Repasar preguntas 3 y 4 para el informe de modelado |
| I26 | Practicar con datasets de ejemplo (penguins, tips, breast cancer, student dropout) (C2 p.25) | ❌ | — | | Practicar EDA con uno antes de usar datos propios (recomendación) |

### I.3 Clase 23/10 · Forecasting y métricas

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I27 | Causas de fallo de previsión: checklist (C3 p.4) | 🟡 | `docs/modelos/demanda_ccaa.md`, `src/cpd/modelos/demanda.py` (fuga, estacionalidad, atípicos, horizonte) | | Lista explícita de las causas de C3 p.4 en el informe |
| I28 | Evitar fuga de información (C3 p.4) | ✅ | `src/cpd/features/demanda.py`, `tests/test_modelos.py` (`test_features_no_usan_datos_posteriores_a_t_menos_h`); `n_ixp` excluida en `src/cpd/features/provincia.py` | | — |
| I29 | Horizonte de previsión justificado (C3 p.4) | ✅ | `docs/analisis/previsiones_1_anio.md` (1 año para el simulador; 10 años para P5, con el intervalo que crece con el plazo) | | — |
| I30 | Ventana temporal de entrenamiento y validación (C3 p.4) | ✅ | `docs/modelos/demanda_ccaa.md`, `src/cpd/modelos/demanda.py`; `tests/test_modelos.py` (`test_particiones_son_temporales_y_no_se_solapan`) | | — |
| I31 | Estacionalidad (C3 p.4) | ✅ | Baseline estacional y features de mes en `docs/modelos/demanda_ccaa.md`, `src/cpd/modelos/demanda.py`; `docs/figuras/eda/02_boxplots.png` | | — |
| I32 | Calidad de la previsión frente a baseline (C3 p.5-6) | ✅ | `docs/analisis/metricas.md`, `docs/analisis/previsiones_1_anio.md` (figuras 4 y 5) | | — |
| I33 | Métricas de regresión: distancia al valor real (C3 p.9-11) | ✅ | `docs/analisis/metricas.md` (MAE, RMSE, MAPE); `src/cpd/modelos/metricas.py` | | — |
| I34 | Métricas de clasificación (C3 p.13) | ✅ | `docs/modelos/prob_cpd.md`, `src/cpd/modelos/prob_cpd.py` | | — |
| I35 | Accuracy (C3 p.14) | ✅ | `docs/analisis/metricas.md` (con clase mayoritaria) | | — |
| I36 | Precision (C3 p.14, 23) | ✅ | `docs/analisis/metricas.md` | | — |
| I37 | Recall (C3 p.14, 19) | ✅ | `docs/analisis/metricas.md` | | — |
| I38 | F-Score (C3 p.14) | ✅ | `docs/analisis/metricas.md` | | — |
| I39 | ROC-AUC: la métrica que siempre hay que mirar (C3 p.14, 19) | ✅ | `docs/analisis/metricas.md`; `docs/figuras/modelos/roc_prob_cpd.png` | | — |
| I40 | Log-Loss (C3 p.14) | ✅ | `docs/analisis/metricas.md` | | — |
| I41 | Matriz de confusión: TP, TN, FP, FN (C3 p.15-17) | ✅ | `docs/modelos/prob_cpd.md` (matriz con el umbral elegido) | | — |
| I42 | Errores de tipo I y tipo II (C3 p.16) | 🟡 | `docs/modelos/prob_cpd.md` (coste de falsos positivos y negativos) | | Nombrar tipo I y tipo II en el informe |
| I43 | TPR y FPR (C3 p.19) | ✅ | `docs/modelos/prob_cpd.md` | | — |
| I44 | Umbral de decisión (C3 p.19) | ✅ | `docs/modelos/prob_cpd.md` (Youden sobre la curva ROC) | | — |
| I45 | Paradoja de la exactitud (C3 p.23) | ✅ | `docs/analisis/metricas.md`; `tests/test_modelos.py` | | — |
| I46 | Coste de un error no es igual para todos (C3 p.8) | ✅ | `docs/modelos/demanda_ccaa.md`, `docs/modelos/prob_cpd.md` (regla de coste) | | — |
| I47 | Sesgos de los datos y cómo comprobarlos (C3 p.22-24) | ✅ | `docs/modelos/prob_cpd.md` (territorio y tamaño), `docs/modelos/demanda_ccaa.md` (por comunidad) | | — |
| I48 | Ejercicio AutoPredict (hoja de cálculo con precision y accuracy) (C3 p.18) | ❌ | Hoja de Google Sheets "PREDICTION" (lectura parcial; ver [[Clase_2026-10-23_Forecasting_Metricas]]) | | Ejercicio de clase, no entregable |

### I.4 Clase 13/11 · Advanced Feature Engineering

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I49 | Lags (retardos) (C4 p.7, 12-14) | ✅ | `src/cpd/features/demanda.py`, `tests/test_modelos.py` | | — |
| I50 | Ventanas móviles: media, máximo, mínimo, desviación (C4 p.7, 15) | ✅ | `src/cpd/features/demanda.py`, `tests/test_modelos.py` (medias de 3, 6 y 12 meses y desviación de 12) | | — |
| I51 | Estacionariedad y estacionalidad (C4 p.16) | ✅ | `src/cpd/modelos/estacionariedad.py`: media y desviación por año y test ADF de la demanda de las 19 comunidades (2015-2025) en nivel, log, diferencia estacional y doble diferencia: 0/19, 0/19, 3/19 y 19/19 estacionarias; figura 21 y sección del informe; `tests/test_modelos.py` | | — |
| I52 | Diferencias (C4 p.7, 17) | ✅ | `f_desv_12m` (Ridge) y `estacional_tendencia` sobre la diferencia estacional; modelo sobre diferencias `anual._ar_diferencias` (AR(1) sobre Δ₁₂ log): 96,1 % / 95,0 %, como el estacional, pero no mejora la combinación de la demanda y no se usa (documentado) | | — |
| I53 | Transformación logarítmica (log, log1p) (C4 p.8, 25-26) | ✅ | `src/cpd/features/demanda.py`, `tests/test_modelos.py`; `src/cpd/features/provincia.py` (`log_poblacion`) | | — |
| I54 | Eventos puntuales (DANA, Black Friday) (C4 p.18) | ✅ | `src/cpd/features/demanda.py`, `tests/test_modelos.py` (`f_confinamiento`) | | Añadir más eventos si se conocen |
| I55 | Escalado (scaling) (C4 p.8, 23) | ✅ | `StandardScaler` dentro del pipeline en `src/cpd/modelos/demanda.py` y `prob_cpd.py` (solo con entrenamiento) | | — |
| I56 | Normalización min-max (MAX-MIN) (C4 p.23) | ✅ | `src/cpd/scoring.py` (`normalizar_min_max`) | | Verificar que no altera la columna original (R-7) |
| I57 | Estandarización z-score (C4 p.23) | ✅ | `StandardScaler` (z-score) en los pipelines de `src/cpd/modelos/` | | — |
| I58 | Winsorizing (C4 p.8) | ✅ | `prob_cpd.Winsorizador` (percentiles 1 y 99 calculados solo con el entrenamiento de cada pliegue) y candidato `logistica_winsor`: log-loss 0,394 → 0,393, sin cambio de elegido; `tests/test_modelos.py` | | — |
| I59 | Transformaciones polinómicas (C4 p.8) | ✅ | `prob_cpd`, candidato `poblacion_polinomica` (población y población², `PolynomialFeatures`): log-loss 0,371 frente a 0,377, sin ganar al elegido; `docs/modelos/prob_cpd.md` | | — |
| I60 | One-hot encoding (C4 p.9, 20) | ✅ | `src/cpd/features/demanda.py`, `tests/test_modelos.py` (mes del año `f_mes_02`…`f_mes_12`) | | — |
| I61 | Frequency encoding (C4 p.9, 21) | ✅ | `prob_cpd.anadir_codificaciones` (`ccaa_frecuencia`: fracción de provincias de la comunidad) y candidato `poblacion_frecuencia_ccaa`: log-loss 0,387, sin ganar; `tests/test_modelos.py` | | — |
| I62 | Target encoding (C4 p.9) | ✅ | `prob_cpd`, candidato `poblacion_target_ccaa` (`TargetEncoder` de la comunidad dentro de cada pliegue, con validación cruzada interna): **elegido** por log-loss (0,377 → 0,316); ROC-AUC 0,882 → 0,925; acierto con umbral 90,4 % → 92,3 %; `tests/test_modelos.py` (se ajusta solo con el entrenamiento) | | — |
| I63 | Embeddings (C4 p.9) | ❌ | — (opcional, "super-ultra-advanced") | | No prioritario |
| I64 | Variables semánticas: zona climática, región, ranking, extracciones (C4 p.10, 27-28) | 🟡 | `ccaa`, `ambito_hidrografico`, `extrapeninsular` (`src/cpd/features/provincia.py`), ranking en `scoring.evaluar` | | Añadir zona climática y extracciones |
| I65 | Rankings como variable (C4 p.10) | ✅ | `src/cpd/scoring.py` (ranking) | | — |
| I66 | Presentar ideas, debilidades y oportunidades (IDEA, WEAKNESS, OPORTUNITY) (C4 p.30) | ❌ | — | | Registrar un DAFO por equipo (recomendación) |

### I.5 Calidad de datos y tratamiento (énfasis del encargo)

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I67 | Limpieza: tipos, duplicados, codificación (recomendación) | 🟡 | `src/cpd/fuentes/curado.py`, `src/ingesta/utils.py`, tests de datos | | Informe de calidad (fase 2) |
| I68 | Valores ausentes: política explícita (recomendación) | 🟡 | `curado.py` (NaN); demanda imposible → NaN con registro en `data/curated/calidad_demanda_ccaa.csv`; imputación solo como entrada de modelos en `src/cpd/features/demanda.py` | | Tabla de nulos y decisiones por variable |
| I69 | Atípicos (outliers): detección y decisión (recomendación; box plot C2 p.10) | 🟡 | Demanda por CCAA: `src/cpd/fuentes/calidad.py` (regla y causa comprobada en REData), `data/curated/calidad_demanda_ccaa.csv`, `docs/datos/tablas_api.md` §9, `docs/analisis/eda_panel.md` §7 | | Detección y registro en el resto de variables |
| I70 | Escalar y normalizar sin perder datos (recomendación; C4 p.23 y R-7) | ✅ | R-7 en los modelos: columnas originales intactas y escalador ajustado solo con entrenamiento | | — |

### I.6 Clase 27/11 · Data Mining & Data Engineering

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I71 | Ingesta batch frente a continua; polling frente a streaming (C5 p.4-6) | ✅ | `src/cpd/fuentes/actualizar.py` (batch completo e incremental; `--rapido` para tiempo real); polling en `frontend/src/live/usePolling.ts`. Streaming no hace falta (ninguna variable cambia en segundos) | | — |
| I72 | ETL frente a ELT (C5 p.4) | ✅ | ETL en `src/cpd/fuentes/` (raw → `data/curated/tablas`); ELT con SQL dentro de DuckDB en `src/cpd/almacen.py` (`dw`, `gold`) | | — |
| I73 | Filtrar en la API antes de descargar (C5 p.13) | ✅ | `country=ES` (PeeringDB), cajas geográficas (EMSC, Overpass, Natura 2000), solo las variables necesarias (NASA POWER, Open-Meteo) | | — |
| I74 | Paginación: offset, página, cursor (C5 p.12) | 🟡 | Ninguna API usada pagina; las series largas se piden por bloques de años (`ree.py`, `sismicidad.py`, `nasa_power.py`) | | Aplicarla si se añade una API paginada |
| I75 | Batching: varios elementos por petición (C5 p.14) | ✅ | `src/cpd/fuentes/meteo.py` (`TAMANO_LOTE = 52`: las 52 provincias en una petición) | | — |
| I76 | Paralelización con límite de simultaneidad (C5 p.15-16) | ✅ | `http.en_paralelo` (hilos, orden conservado); NASA POWER con 4 hilos (`nasa_power.HILOS`); `tests/test_fuentes.py` | | Medir el tiempo de una actualización completa |
| I77 | Rate limiting y HTTP 429 (C5 p.17) | ✅ | `http._esperar_turno` (pausa mínima con cerrojo, también entre hilos); 429 → `Retry-After` o 65 s; `tests/test_fuentes.py` | | — |
| I78 | Reintentos con backoff exponencial y jitter (C5 p.18-19) | ✅ | `http.espera_backoff` (2, 4, 8… s, tope 60 s, +25 % de jitter) en `http.pedir`; `tests/test_fuentes.py` | | — |
| I79 | Caché: estático frente a dinámico, TTL (C5 p.20) | ✅ | `http.leer_cache_json(ruta, ttl_horas)`; PeeringDB con TTL de 7 días; años cerrados siempre de caché; `tests/test_fuentes.py` | | — |
| I80 | Parquet: formato columnar, binario y con tipos (C5 p.23-25) | ✅ | `capas.tablas_a_parquet` (Silver en Parquet zstd si el CSV cambió); `panel_provincia_mes.parquet`; `tests/test_capas.py` | | — |
| I81 | DuckDB frente a pandas (C5 p.27-28) | ✅ | Almacén `data/almacen/p3_cpd.duckdb`; comparación medida en `gold.formatos` (Parquet 3,9× más pequeño; DuckDB sobre Parquet ~57× más rápido que sobre CSV) | | — |
| I82 | OLTP frente a OLAP (C5 p.29-31) | ✅ | Decisión en [[Clase_2026-11-27_Data_Engineering]] y R-21: P3 es OLAP (DuckDB) | | — |
| I83 | ORM / SQLAlchemy (C5 p.32) | ❌ | — (no aplica: no hay datos transaccionales; ver R-21) | | No prioritario |
| I84 | Data lake por capas Bronze / Silver / Gold (C5 p.34) | ✅ | `src/cpd/capas.py` (`CAPAS`), esquema `gold` del almacén, R-20; `tests/test_capas.py` | | — |
| I85 | Calidad de datos en el paso de Bronze a Silver (C5 p.35) | 🟡 | `src/cpd/fuentes/calidad.py`, `curado.py`; ver I67-I69 | | Informe de calidad (I67-I69) |
| I86 | Trazabilidad y no descargar dos veces (C5 p.36) | ✅ | `data/raw/_registro_descargas.csv`, `meta.carga`, caché de `data/raw/api/`; R-17 y R-18 | | — |
| I87 | Watermarks y carga incremental (C5 p.36) | ✅ | `capas.watermarks` y `guardar_historial` (`data/almacen/historial_watermarks.csv`), `gold.watermark`; `tests/test_capas.py` | | Usar el watermark para decidir qué pedir en `actualizar` |
| I88 | At least once frente a exactly once (C5 p.36) | ✅ | Escrituras atómicas e idempotentes: `.part` en `http.descargar_archivo` y `capas.tablas_a_parquet`, `.tmp.duckdb` en `almacen.construir`; repetir no duplica | | — |
| I89 | Dashboard DuckDB + Streamlit que solo lee (C5 p.36) | ✅ | `app/pages/1_Datos_y_APIs.py` (6 pestañas: resumen, APIs, datasets, frescura, Bronze y formatos, explorador; `read_only=True`); `tests/test_dashboard_datos.py` | | Informe de cuadro de mandos (F) |

---

## Cómo mantener esta checklist

1. Cada tarea cierra al menos una fila: cambiar estado, poner evidencia (ruta o commit corto) y dejar la siguiente acción.
2. Una fila solo pasa a ✅ si la evidencia **se puede verificar** por un tercero.
3. Revisar esta tabla en la reunión semanal ([[07_Estado_actual]], plan).
4. Las filas nuevas se añaden al final de su sección, con el siguiente ID libre.
