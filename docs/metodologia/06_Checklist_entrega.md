---
tags: [metodologia, checklist, entrega, p3]
estado: borrador
actualizado: 2026-11-14
---

# 06 · Checklist de entrega

Volver a [[00_Indice]]. Ver también [[07_Estado_actual]] (resumen y plan) y [[03_Flujo_de_trabajo]] (cómo cerrar cada fila).

**Leyenda:** ✅ hecho (hay evidencia verificable) · 🟡 parcial (existe algo incompleto o sin validar) · ❌ pendiente (no encontrado en el repositorio).
**Evidencia:** ruta de archivo en el repo, o "—" si no hay.
**Responsable:** vacío hasta asignar en la fase 0.
**Estado verificado:** 14/11/2026, comparando con el commit `90b91e4` de `main`.

Las filas marcadas con `C1`…`C4` son técnicas de las clases (ver [[Clase_2026-10-02_Data_Relation_Modelling]], [[Clase_2026-10-09_Data_Visualization_Correlation]], [[Clase_2026-10-23_Forecasting_Metricas]], [[Clase_2026-11-13_Advanced_Feature_Engineering]]).

> Cómo se actualiza: al cerrar una tarea, cambiar el estado, poner la evidencia (ruta o commit) y escribir la siguiente acción.
> La columna "Siguiente acción" dice qué hace falta para pasar a ✅.

## Resumen de conteos

| Sección | ✅ | 🟡 | ❌ | Total |
|---|---|---|---|---|
| A. Objetivo general | 0 | 3 | 0 | 3 |
| B. Objetivos específicos (1-10) | 0 | 7 | 3 | 10 |
| C. Preguntas funcionales (P1-P8) | 2 | 6 | 0 | 8 |
| D. Variables del CPD (enunciado) | 13 | 3 | 9 | 25 |
| E. Variables del entorno territorial (enunciado) | 8 | 22 | 17 | 47 |
| F. Entregables y evidencias | 0 | 4 | 5 | 9 |
| G. Rúbrica (nivel 6) | 0 | 2 | 1 | 3 |
| H. Resultados de aprendizaje (RA) | 0 | 2 | 7 | 9 |
| I. Técnicas de clase y de calidad de datos | 4 | 15 | 51 | 70 |
| **Total** | **27** | **64** | **93** | **184** |

Conteos verificados el 14/11/2026 contando las celdas de estado de cada fila. Si se añaden filas, recalcular.

---

## A. Objetivo general (enunciado, p. 2)

| ID | Requisito | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| A1 | Plataforma Big Data para analizar y predecir la viabilidad de instalar un CPD en cualquier municipio español | 🟡 | `src/cpd/`, `app/streamlit_app.py`, `frontend/` | | Decidir granularidad (D1) y documentarla |
| A2 | Proporcionar una puntuación global de viabilidad | 🟡 | `src/cpd/scoring.py` (`calcular_score_global`) | | Calibrar pesos y umbrales (`config/settings.yaml`) |
| A3 | Generar previsiones a corto y medio plazo sobre la sostenibilidad operativa del CPD | 🟡 | `src/cpd/forecast.py` | | Añadir validación y métricas (fase 7-8) |

## B. Objetivos específicos (enunciado, p. 2-3)

| ID | Requisito | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| B1 | Identificar y recopilar fuentes de datos relevantes | 🟡 | `docs/datos/README.md`, `docs/datos/tablas_api.md`, `src/cpd/fuentes/` | | Integrar AEMET, Confederaciones Hidrográficas y CNMC o justificar sustitución (D2) |
| B2 | Diseñar procesos ETL para integrar datos heterogéneos | 🟡 | `src/ingesta/01_…04_*.py`, `src/cpd/fuentes/actualizar.py`, `src/cpd/etl/ree.py` | | Documentar el ETL como diagrama y tabla (fases 1-3) |
| B3 | Limpiar, transformar y validar los datos obtenidos | 🟡 | `src/cpd/fuentes/curado.py` (criterio NaN), `tests/test_datos_nuevos.py` | | Informe de calidad: nulos, duplicados, atípicos por variable (fase 2) |
| B4 | Diseñar un Data Lake y un Data Warehouse | 🟡 | `data/raw/`, `data/almacen/p3_cpd.duckdb`, `src/cpd/almacen.py` | | Completar estrella y escribir documento de almacenamiento (fase 5) |
| B5 | Realizar análisis exploratorio de datos | ❌ | — | | Crear `notebooks/01_eda_panel.ipynb` (fase 4) |
| B6 | Detectar correlaciones entre variables territoriales y la viabilidad | ❌ | — | | Matriz de correlación Pearson y Spearman vs score (fase 4) |
| B7 | Construir modelos predictivos mediante Machine Learning | ❌ | — (aplazado por decisión del equipo; ver D3) | | Entrenar al menos un modelo frente a baseline (fase 7) |
| B8 | Diseñar un simulador capaz de evaluar distintos escenarios | 🟡 | `src/cpd/simulator.py`, `scoring.preparar_escenario`, `app/streamlit_app.py` | | Añadir parámetros del CPD que faltan (ver D) |
| B9 | Crear dashboards interactivos para la toma de decisiones | 🟡 | `app/streamlit_app.py` (6 pestañas), `frontend/` (mapa) | | Informe de cuadro de mandos (fase 10) |
| B10 | Elaborar predicciones de evolución futura mediante series temporales | 🟡 | `src/cpd/forecast.py` (tendencia + estacionalidad, 120 meses) | | Backtesting y métricas de error (fase 7-8) |

## C. Preguntas funcionales (enunciado, p. 3; ver [[01_Objetivo_y_alcance]])

| ID | Pregunta | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| P1 | ¿Qué municipios son los más adecuados? | 🟡 | `src/cpd/scoring.py` (`evaluar`, ranking) | | Ranking real a nivel de provincia; municipal con datos reales |
| P2 | ¿Qué impacto tendrá el CPD sobre los recursos locales? | 🟡 | `simulator.impacto_local_pct` | | Datos de consumo municipal reales o explicación de límite |
| P3 | ¿Existe suficiente disponibilidad energética? | 🟡 | `panel`: `nudos_acceso_ccaa`, `capacidad_demanda_rdt_disponible_mw` | | Análisis por nudo o CCAA; decisión de nivel |
| P4 | ¿Existe riesgo hídrico? | 🟡 | `panel`: `estres_hidrico_wri_0_1`, `reserva_hidrica_pct`, `indice_sequia_12m` | | Informe con interpretación y limitación |
| P5 | ¿Cómo evolucionará la demanda eléctrica en los próximos 10 años? | 🟡 | `src/cpd/forecast.py`, `data/clean/ree_demanda_mensual.csv` | | Modelo con validación temporal y banda de incertidumbre |
| P6 | ¿Cuál será el coste operativo esperado? | ✅ | `simulator.opex_eur`, `desglose_opex`; `tests/test_simulator.py` | | Calibrar precios en `config/settings.yaml` y documentar |
| P7 | ¿Cuál será el retorno de inversión estimado? | ✅ | `simulator.van`, `roi`, `payback_anos`; tests | | Documentar tasa de descuento y supuestos |
| P8 | ¿Qué zonas presentan menor riesgo regulatorio o ambiental? | 🟡 | `scoring.aplicar_filtros` (Natura 2000, inundación, sísmico) | | Verificar fuentes de inundación y sísmico y sus unidades |

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
| E7 | Producción eléctrica disponible | 🟡 | `generacion_total_ccaa_mwh` (CCAA, no provincia) | | Documentar nivel CCAA |
| E8 | Consumo eléctrico municipal | 🟡 | `demanda_ccaa_mwh` (CCAA); sin dato municipal abierto (ver `docs/datos/README.md`) | | Documentar la limitación |
| E9 | Capacidad de la red | 🟡 | `nudos_acceso_ccaa`, `capacidad_demanda_rdt_disponible_mw` | | Revisar cobertura territorial |
| E10 | Subestaciones cercanas | 🟡 | `subestaciones_220_400kv`, `subestaciones_400kv` (OSM) | | Distancia a la subestación más cercana, no solo conteo |
| E11 | Capacidad de transporte | 🟡 | `capacidad_demanda_rdt_disponible_mw` | | Aclarar si es transporte o acceso |
| E12 | Porcentaje de renovables | ✅ | `pct_renovable_ccaa` | | — |

### E.3 Agua (fuentes: Confederaciones Hidrográficas, MITECO, AEMET)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E13 | Disponibilidad hídrica | 🟡 | `reserva_hidrica_pct`, `reserva_hidrica_hm3` (por ámbito) | | Explicar relación con disponibilidad real |
| E14 | Consumo hídrico municipal | ❌ | — | | Buscar fuente abierta o documentar que no existe |
| E15 | Embalses cercanos | 🟡 | Reserva por ámbito hidrográfico (MITECO) | | Asociar embalse al municipio o provincia |
| E16 | Estrés hídrico | ✅ | `estres_hidrico_wri_0_1` (WRI Aqueduct) | | — |
| E17 | Sequías históricas | 🟡 | `indice_sequia_12m` (suma de 12 meses, no índice oficial) | | Documentar que no es SPI oficial |
| E18 | Calidad del agua | ❌ | — | | Buscar fuente (CCHH, MITECO) |

### E.4 Climatología (fuentes: AEMET en el enunciado; NASA POWER y Open-Meteo en el repo)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E19 | Temperatura media anual | 🟡 | `tmedia_mes_c` (mensual; la anual no está calculada) | | Calcular media anual |
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
| E28 | Distancia a nodos principales | 🟡 | `distancia_ixp_km` (solo IXP, no nodos) | | Definir "nodo principal" |
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
| E34 | Precio del suelo industrial | ❌ | — | | Buscar fuente abierta |
| E35 | Disponibilidad de parcelas | ❌ | — | | Buscar fuente |
| E36 | Calificación urbanística | ❌ | — | | Buscar fuente (planeamiento municipal) |
| E37 | Riesgos de inundación | 🟡 | Filtro "zona inundable" en `README.md` (fuente por verificar) | | Confirmar fuente y añadir a panel |
| E38 | Riesgo sísmico | 🟡 | `n_terremotos`, `magnitud_max`, `n_terremotos_m3_plus` (EMSC); filtro de 0,16 g en README | | Verificar que la unidad (g) y la magnitud son coherentes |

### E.8 Impacto socioeconómico (enunciado, p. 7)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E39 | Empleo generado | ❌ | — | | Definir modelo de cálculo (hipótesis documentada) |
| E40 | Inversión inducida | ❌ | — | | Igual |
| E41 | PIB municipal | ❌ | — | | Buscar fuente (INE, Eurostat) |
| E42 | Atracción empresarial | ❌ | — | | Definir indicador (recomendación) |

### E.9 Impacto ambiental (enunciado, p. 7)

| ID | Variable | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| E43 | Incremento del consumo energético local | 🟡 | `simulator.impacto_local_pct` | | Necesita consumo municipal (E8) |
| E44 | Incremento del consumo hídrico | 🟡 | `simulator.agua_m3_anual` (sin % sobre consumo local) | | Calcular % sobre consumo local |
| E45 | Huella de carbono | ✅ | `simulator.co2_t` | | Documentar factor de emisión y alcance |
| E46 | Emisiones indirectas | 🟡 | `co2_t` (solo energía comprada) | | Aclarar alcance 2 y 3 |
| E47 | Ocupación del suelo | ❌ | — | | Calcular a partir de superficie (D1) |

## F. Entregables y evidencias (enunciado, p. 8)

| ID | Entregable / evidencia | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| F1 | Informe de origen de datos (M4RA1) | 🟡 | `docs/datos/README.md` (borrador) | | Completar con todas las fuentes y licencias |
| F2 | Informe de cuadro de mandos (M4RA2) | ❌ | — | | Redactar tras fase 10 |
| F3 | Informe de análisis de los datos (M4RA2) | ❌ | — | | Redactar tras fase 4 y 8 |
| F4 | Informe de visualización de datos (M4RA4) | ❌ | — | | Redactar en fase 10 |
| F5 | Documentación descriptiva del sistema de gestión y almacenamiento de datos (M4RA3) | 🟡 | `src/cpd/almacen.py`, `docs/datos/tablas_api.md`, diccionarios en `data/curated/` | | Documento con diagrama y granularidad (fase 5) |
| F6 | Código fuente con comentarios en las funciones principales, en control de versiones (M4RA1-M4RA4) | 🟡 | Git (`main`, commits); comentarios por función sin verificar | | Auditar docstrings de funciones principales |
| F7 | Vídeo del sistema funcional con diversos casos de prueba (M4RA1-M4RA4) | ❌ | — | | Guion y grabación (fase 11) |
| F8 | Manual de instalación y despliegue (M4RA1, M4RA3) | 🟡 | `README.md` (sección Instalación) | | Manual aparte con prueba de humo |
| F9 | Manual de usuario final (M4RA2, M4RA4) | ❌ | — | | Redactar con capturas |

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
| I12 | Gráfico de líneas: evolución temporal (C2 p.6) | 🟡 | Gráficos en `app/streamlit_app.py` (previsión) | | Verificar ejes con unidades |
| I13 | Gráfico de barras: comparar categorías (C2 p.7) | 🟡 | Ranking en `app/streamlit_app.py` | | Verificar ejes y orden |
| I14 | Histograma de variables numéricas (C2 p.8) | ❌ | — | | Histograma por variable (fase 4) |
| I15 | Diagrama de dispersión (C2 p.9) | ❌ | — | | Dispersión variable vs score (fase 4) |
| I16 | Box plot: outliers, mediana y cuartiles (C2 p.10) | ❌ | — | | Box plot por variable (fase 2 y 4) |
| I17 | Mapa de calor de correlación (C2 p.11) | ❌ | — | | Heatmap de matriz de correlación (fase 4) |
| I18 | Gráfico de sectores (C2 p.12) | ❌ | — (no hay uso; recomendación: evitar) | | No aplica salvo caso puntual |
| I19 | Pair plot (C2 p.13) | ❌ | — | | Pair plot de variables seleccionadas (fase 4) |
| I20 | Correlación de −1 a 1 y su interpretación (C2 p.15) | ❌ | — | | Calcular y explicar (fase 4) |
| I21 | Pearson: lineal, sensible a outliers (C2 p.23) | ❌ | — | | Calcular (fase 4) |
| I22 | Spearman: monótona, robusta (C2 p.23) | ❌ | — | | Calcular y comparar con Pearson (fase 4) |
| I23 | Kendall: muestras pequeñas (C2 p.23-24) | ❌ | — | | Calcular si hay pocas filas (fase 4) |
| I24 | Correlación no implica causalidad (C2 p.18-21) | ❌ | — | | Frase obligatoria en cada conclusión (fase 4) |
| I25 | Ejercicio de examen (Q1 a Q4) (C2 p.4) | ❌ | Ejercicio de clase, no entregable de P3 (sin hacer) | | Repasar preguntas 3 y 4 para el informe de modelado |
| I26 | Practicar con datasets de ejemplo (penguins, tips, breast cancer, student dropout) (C2 p.25) | ❌ | — | | Practicar EDA con uno antes de usar datos propios (recomendación) |

### I.3 Clase 23/10 · Forecasting y métricas

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I27 | Causas de fallo de previsión: checklist (C3 p.4) | ❌ | — | | Revisar cada causa en fase 7 |
| I28 | Evitar fuga de información (C3 p.4) | 🟡 | Baseline sin feature de futuro (revisado a ojo) | | Auditoría formal de features (fase 6) |
| I29 | Horizonte de previsión justificado (C3 p.4) | 🟡 | `forecast.py` (120 meses por defecto) | | Justificar horizonte por pregunta |
| I30 | Ventana temporal de entrenamiento y validación (C3 p.4) | ❌ | — | | División temporal documentada (fase 7) |
| I31 | Estacionalidad (C3 p.4) | 🟡 | `forecast.py` (factor estacional por mes) | | Verificar con gráfico y test |
| I32 | Calidad de la previsión frente a baseline (C3 p.5-6) | ❌ | — | | Tabla de comparación (fase 8) |
| I33 | Métricas de regresión: distancia al valor real (C3 p.9-11) | ❌ | — | | MAE y RMSE (fase 8) |
| I34 | Métricas de clasificación (C3 p.13) | ❌ | — | | Solo si se modela clasificación |
| I35 | Accuracy (C3 p.14) | ❌ | — | | Calcular con baseline de clase mayoritaria |
| I36 | Precision (C3 p.14, 23) | ❌ | — | | Calcular (fase 8) |
| I37 | Recall (C3 p.14, 19) | ❌ | — | | Calcular (fase 8) |
| I38 | F-Score (C3 p.14) | ❌ | — | | Calcular (fase 8) |
| I39 | ROC-AUC: la métrica que siempre hay que mirar (C3 p.14, 19) | ❌ | — | | Calcular y graficar (fase 8) |
| I40 | Log-Loss (C3 p.14) | ❌ | — | | Si el modelo da probabilidades |
| I41 | Matriz de confusión: TP, TN, FP, FN (C3 p.15-17) | ❌ | — | | Matriz en fase 8 |
| I42 | Errores de tipo I y tipo II (C3 p.16) | ❌ | — | | Explicar coste (fase 8) |
| I43 | TPR y FPR (C3 p.19) | ❌ | — | | Calcular para curva ROC |
| I44 | Umbral de decisión (C3 p.19) | ❌ | — | | Elegir y justificar |
| I45 | Paradoja de la exactitud (C3 p.23) | ❌ | — | | Comprobación explícita (fase 8) |
| I46 | Coste de un error no es igual para todos (C3 p.8) | ❌ | — | | Regla de coste en la model card |
| I47 | Sesgos de los datos y cómo comprobarlos (C3 p.22-24) | ❌ | — | | Análisis de sesgo por subgrupo (fase 8) |
| I48 | Ejercicio AutoPredict (hoja de cálculo con precision y accuracy) (C3 p.18) | ❌ | Hoja de Google Sheets "PREDICTION" (lectura parcial; ver [[Clase_2026-10-23_Forecasting_Metricas]]) | | Ejercicio de clase, no entregable |

### I.4 Clase 13/11 · Advanced Feature Engineering

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I49 | Lags (retardos) (C4 p.7, 12-14) | ❌ | — | | Lags 1, 3, 12 en fase 6 |
| I50 | Ventanas móviles: media, máximo, mínimo, desviación (C4 p.7, 15) | 🟡 | `src/cpd/fuentes/agua.py` (suma móvil 12 meses) | | Ampliar a más ventanas y estadísticos |
| I51 | Estacionariedad y estacionalidad (C4 p.16) | 🟡 | `forecast.py` (factor mensual) | | Comprobar estacionariedad y transformar |
| I52 | Diferencias (C4 p.7, 17) | ❌ | — | | Probar en serie de demanda |
| I53 | Transformación logarítmica (log, log1p) (C4 p.8, 25-26) | ❌ | Ninguna en `src/` | | Aplicar a variables asimétricas (fase 3) |
| I54 | Eventos puntuales (DANA, Black Friday) (C4 p.18) | ❌ | — | | Variable binaria con eventos conocidos |
| I55 | Escalado (scaling) (C4 p.8, 23) | 🟡 | `scoring.normalizar_min_max` (solo para sub-scores) | | Escalado documentado para modelos (fase 3) |
| I56 | Normalización min-max (MAX-MIN) (C4 p.23) | ✅ | `src/cpd/scoring.py` (`normalizar_min_max`) | | Verificar que no altera la columna original (R-7) |
| I57 | Estandarización z-score (C4 p.23) | ❌ | — | | Añadir función y test (fase 3) |
| I58 | Winsorizing (C4 p.8) | ❌ | — | | Recorte de percentiles 1 y 99 (fase 2-3) |
| I59 | Transformaciones polinómicas (C4 p.8) | ❌ | — | | Solo si se justifica |
| I60 | One-hot encoding (C4 p.9, 20) | ❌ | — | | Para categorías pocas (fase 3) |
| I61 | Frequency encoding (C4 p.9, 21) | ❌ | — | | Para categorías muchas (fase 3) |
| I62 | Target encoding (C4 p.9) | ❌ | — | | Solo dentro de partición de entrenamiento |
| I63 | Embeddings (C4 p.9) | ❌ | — (opcional, "super-ultra-advanced") | | No prioritario |
| I64 | Variables semánticas: zona climática, región, ranking, extracciones (C4 p.10, 27-28) | 🟡 | `ccaa`, `ambito_hidrografico`, ranking en `scoring.evaluar` | | Añadir zona climática y extracciones |
| I65 | Rankings como variable (C4 p.10) | ✅ | `src/cpd/scoring.py` (ranking) | | — |
| I66 | Presentar ideas, debilidades y oportunidades (IDEA, WEAKNESS, OPORTUNITY) (C4 p.30) | ❌ | — | | Registrar un DAFO por equipo (recomendación) |

### I.5 Calidad de datos y tratamiento (énfasis del encargo)

| ID | Técnica | Estado | Evidencia | Responsable | Siguiente acción |
|---|---|---|---|---|---|
| I67 | Limpieza: tipos, duplicados, codificación (recomendación) | 🟡 | `src/cpd/fuentes/curado.py`, `src/ingesta/utils.py`, tests de datos | | Informe de calidad (fase 2) |
| I68 | Valores ausentes: política explícita (recomendación) | 🟡 | `curado.py`: NaN donde la fuente no tiene dato | | Tabla de nulos y decisiones por variable |
| I69 | Atípicos (outliers): detección y decisión (recomendación; box plot C2 p.10) | ❌ | — | | Detección por variable y registro de decisiones |
| I70 | Escalar y normalizar sin perder datos (recomendación; C4 p.23 y R-7) | 🟡 | Normalización de scores; sin política para modelos | | Política R-7 aplicada en fase 3 |

---

## Cómo mantener esta checklist

1. Cada tarea cierra al menos una fila: cambiar estado, poner evidencia (ruta o commit corto) y dejar la siguiente acción.
2. Una fila solo pasa a ✅ si la evidencia **se puede verificar** por un tercero.
3. Revisar esta tabla en la reunión semanal ([[07_Estado_actual]], plan).
4. Las filas nuevas se añaden al final de su sección, con el siguiente ID libre.
