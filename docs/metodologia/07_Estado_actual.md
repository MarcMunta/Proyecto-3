---
tags: [metodologia, estado, auditoria, plan, p3]
estado: borrador
actualizado: 2026-11-17
---

# 07 · Estado actual (auditoría y plan)

Volver a [[00_Indice]]. Filas detalladas en [[06_Checklist_entrega]]. Fecha de auditoría: **14/11/2026**, commit `90b91e4` de `main` (árbol de trabajo limpio).

## Novedades del 17/11/2026 (rama `fix/mapa-revision`, sin commit)

- **EDA** con figuras e informe (`docs/analisis/eda_panel.md`), correlaciones de Pearson y Spearman con el score y el VAN (B5 🟡, B6 ✅).
- **Modelos entrenados y evaluados** (B7 ✅, B10 ✅): demanda eléctrica por comunidad a 1 mes (Ridge, MAPE de test 4,40 % frente a 4,88 % del mejor baseline) y a 12 meses (gana el baseline "mismo mes del año anterior"); `prob_cpd` por provincia (gana la logística con la población, ROC-AUC 0,88). Fichas en `docs/modelos/`, métricas en `docs/analisis/metricas.md`. Todo se regenera con `python -m cpd.modelos`.
- **Precio de la luz** (`docs/modelos/precio_luz.md`): ningún modelo de ML supera en validación a la media de los últimos 12 meses (MAE 23,5 €/MWh), que es lo que ya usaba el simulador; sin el precio del gas no se anticipan los cambios de régimen. Previsión para los 12 meses siguientes a octubre de 2026: 80 €/MWh (rango 45-282). **Hallazgo:** si la luz se queda como en octubre de 2026 (167 €/MWh), el VAN es negativo en las 52 provincias: el precio pesa más que la ubicación. Siguiente mejora: añadir el precio del gas (MIBGAS) o los futuros de OMIP (recomendación, no viene de clase).
- **Previsión a 1 año** (`docs/analisis/previsiones_1_anio.md`, `src/cpd/modelos/anual.py`): backtesting con 24 orígenes, ETS, ML, **precio del gas de MIBGAS** (fuente nueva) y combinación de los 3 mejores modelos. Precio: error a 1 año de 29 €/MWh en validación frente a 42 de la media de 12 meses; previsión media de 153 €/MWh para nov-2026 a oct-2027. Demanda: 3,9 % de error en validación. Con el precio previsto, el VAN es negativo en todas las provincias. **Decisión D7 (17/11/2026):** el simulador mantiene como precio base la media de los últimos 12 meses; la previsión a 1 año se enseña como escenario (ver [[01_Objetivo_y_alcance]]).
- **Requisito de acierto (D8):** 85 % ≤ acierto < 99,9 %. Cumplen la demanda a 1 año (95,6-96,7 %), la demanda nacional a 10 años (97,3 %, P5 ✅), las reservas de agua a 1 año (85,3-86,7 %, P4 ✅) y `prob_cpd` (90,4 %). **No cumple el precio de la luz a 1 año (59-62 %)**. **Decidido (17/11/2026):** se queda como escenario orientativo, con aviso y fuera del VAN. Motivo, con cifras de la validación: ni a 1 mes vista ningún modelo pasa del 77 % (ETS), porque el precio real de esos meses va de 14 €/MWh (abril de 2024) a 133 €/MWh (febrero de 2023) (`docs/analisis/previsiones_1_anio.md`); forzar el 85 % exigiría elegir el periodo de evaluación o usar datos del futuro. Los futuros de OMIP no se usan (18/11/2026): no están en abierto y extraerlos de su web choca con sus condiciones de uso.
- **Temperatura media por provincia a 1 año** (nuevo, `anual.candidatos_temperatura`, NASA POWER desde 2015): es la variable del PUE estimado. Combinación de ETS y anomalía persistente; acierto 93,8 % en validación y 92,8 % en test (cumple D8), error de 1 °C al mes y de 0,5 °C en la media anual, que mueve el PUE unas milésimas. Intervalo en °C (aditivo). Figuras 09-10 y gráfico en la ficha del mapa. Las figuras 03-04 (error por horizonte y comparación) incluyen ahora las reservas y la temperatura, y `prob_cpd` tiene una figura nueva (matriz de confusión y probabilidad por provincia).
- **% de generación renovable por comunidad a 1 año** (nuevo, `anual.candidatos_renovables`, REData desde 2015; Ceuta fuera porque siempre es 0 %): combinación de tres ETS (dos con solo los últimos 5 años, por el auge solar). Mes a mes: 84,8 % en validación y 88,6 % en test (con el Ridge sobre anomalías y la reserva de los embalses, añadido el 18/11/2026), **no cumple D8 por 0,2 puntos** (el viento, la lluvia y el sol del mes no se pueden prever a 1 año; Cantabria, Navarra y Madrid concentran el error) y se enseña como orientativo. El % medio de 12 meses, la cifra útil para un CPD, sí cumple: 89,4 % y 92,2 %. Figuras 11-12, gráfico en la ficha (bloque Luz) y dos filas en el control de acierto.
- **Cobertura renovable y red otorgada (17/11/2026):** modelo de generación renovable por comunidad a 1 año (con la suma de tecnologías (solar, eólica, hidráulica y resto previstas por separado, 18/11/2026) el mes a mes cumple, y más con la hidráulica prevista desde los embalses: 86,2 % en validación y 88,2 % en test; total de 12 meses: 92,3 % y 93,5 %. Para el precio de la luz, el % renovable mes a mes y el riesgo sísmico se probaron mejoras con datos reales (embalses, tecnologías, horizonte de 3 años en el sísmico) sin llegar al 85 %: no se fuerzan; mes a mes orientativo) → cobertura renovable prevista = generación renovable / demanda (Extremadura 315 %, Castilla y León 241 %, Castilla-La Mancha 199 %, Aragón 170 %). Dato nuevo de REE en la ingesta: capacidad de red **otorgada** a nueva demanda y **pendiente** (Aragón es la primera de España: 3.938 MW otorgados y 3.244 MW en trámite; el nudo de Calatorao tiene 650 MW otorgados, los mismos que el campus anunciado por Blackstone). Regla fijada antes de ver el ranking: la cobertura entra en el bloque de energía y los CPD existentes y la red otorgada en el de mercado (sin cambiar pesos).
- **Suelo y conectividad (17/11/2026):** fuente nueva del Ministerio de Transportes (precio medio del suelo urbano por provincia, mediana de 4 trimestres; solo en el score, no en el CAPEX porque no es suelo industrial) y latencia al más lejano de los dos grandes nodos de internet (provincias con más IXP en PeeringDB: hoy Madrid y Barcelona). Reglas fijadas antes de ver el ranking.
- **Operación del CPD a 1 año (A3)** (`src/cpd/modelos/operacion.py`): encadena la temperatura prevista (→ PUE → consumo) y el % renovable previsto de la comunidad (→ emisiones con el mix de su comunidad), más el agua y la reserva mínima prevista del ámbito. Validación de punta a punta en 22 orígenes comunes: consumo 99,7 % (el PUE apenas cambia con la temperatura en la fórmula del simulador) y emisiones 90,6 %. Figura 14 y línea en la ficha.
- **Riesgo sísmico (P8)** (`src/cpd/modelos/sismico.py`): probabilidad de algún terremoto M ≥ 3 el año siguiente (EMSC 2015-2025, backtesting año a año). La logística mejora a los baselines (ROC-AUC 0,82); con la peligrosidad oficial de la NCSE-02 como variable acierta 74,2 % en validación y 73,1 % en test: **no cumple D8**, no se usa en el score (el año a año es aleatorio). Para P8 manda la aceleración oficial de la norma.
- **Peligrosidad sísmica oficial (17/11/2026):** norma sismorresistente NCSE-02 (BOE, anejo 1: aceleración sísmica básica de 2.615 municipios, del mapa del IGN), leída con `pypdf` (`src/cpd/fuentes/norma_sismica.py`). Por provincia, la de la capital (0,04 g si no aparece: máximo posible). Rellena el filtro sísmico (0,16 g o más → con condiciones: Granada, 0,23 g) y el bloque de riesgos del score. El modelo anual de terremotos la usa como variable, pero sigue sin llegar al 85 %.
- **Gas y tiempo para el precio de la luz (18/11/2026)** (`src/cpd/modelos/gas_tiempo.py`): el precio era el modelo más difícil (59-62 %). Se añadieron el **modelo del gas** (MIBGAS: último valor, ETS y futuros; 70,4 % / 52,3 %) y el **modelo del tiempo** a través de la generación de España por tecnología (eólica 86,6 % / 83,7 %, solar 90,9 % / 90,9 %, hidráulica 72,9 % / 85,5 %), marcados como **inestables** y solo como entradas del precio. Con ellos, un **precio estructural** (gas + cuotas de eólica, solar, hidráulica, nuclear, ciclo combinado y carbón) entra en la combinación: el precio pasa de 59,0 % a 59,7 % en validación (test 62,4 % → 61,4 %). Diagnóstico: ni con el gas y la generación reales de cada mes se pasa del 78,9 %; falta el precio del CO2 (EEX, de pago), la demanda horaria y las interconexiones. Tabla nueva `generacion_nacional_detalle` (REData) y figura 15.
- **Medio plazo: clima y agua a 10 años (A3, 18/11/2026)** (`src/cpd/modelos/medio_plazo.py`): temperatura media anual por provincia con NASA POWER mensual desde 1981 (dato nuevo: la tabla diaria empezaba en 2015), validación con orígenes 1995-2005 y test desde 2015 (2016-2025). Acierto 97,7 % / 94,8 % (error 0,34 / 0,79 °C); consumo del CPD de punta a punta 99,8 % / 99,5 %. Reserva de agua por ámbito: la **media de la década** cumple (91,1 % / 86,6 %); año a año 83,3 % / 81,9 %, orientativo. El test muestra que el modelo elegido se queda corto con el calentamiento de 2016-2025; se da un escenario de sensibilidad con la tendencia de 30 años (+0,48 °C por década → PUE 1,455 → 1,461, consumo +0,5 %). Emisiones a 10 años: no se prevén (mix desde 2015). Figura 16 y línea «A 10 años» en la ficha del mapa.
- **Impacto local (P2, 18/11/2026)** (`src/cpd/modelos/impacto_local.py`): peso previsto del CPD de referencia sobre los recursos de su comunidad (no hay consumo abierto por municipio): electricidad (consumo previsto / demanda prevista de la comunidad; validación de punta a punta 96,1 %, 20 orígenes), red (potencia máxima / capacidad de acceso libre de REE) y agua (agua del CPD / agua registrada y distribuida, INE tabla 53447, dato nuevo). Provincia mediana: 3,7 % de la electricidad (como 90.000 habitantes) y 0,10 % del agua (como 2.600): pesa la electricidad, no el agua. Ceuta y Melilla: más del 200 % (sistemas aislados). Red: Aragón usaría el 82 % de la capacidad libre (89 MW); Madrid, Navarra y Ceuta tienen 0 MW libres. Figura 17 y línea en la ficha del mapa. Cierra P2, E43 y E44.
- **Impacto socioeconómico (E39-E41, 18/11/2026)** (`src/cpd/modelos/socioeconomico.py`, `src/cpd/fuentes/ine_tio.py`): modelo input-output de Leontief tipo I con las Tablas Input-Output 2022 del INE (dato nuevo: inversa interior, producción, VAB, importaciones y empleo ETC de 65 productos) y el PIB provincial (INE, tabla 82284). Construcción: de 400 M€ de CAPEX quedan en España 295 M€ → 3.402 empleos-año, 562 M€ de producción y 217 M€ de VAB (reparto del CAPEX por productos = supuesto a calibrar en `settings.yaml`). Operación: 60 empleos directos + 217 en proveedores (×4,6) y 78 M€ de VAB al año. VAB directo / PIB provincial: de 0,01 % (Madrid) a 2,5 % (Melilla); Soria 1,5 %. Es un cálculo, no una previsión: no tiene backtesting. Figura 18 y línea en la ficha. E42 (atracción empresarial) sigue sin indicador.
- **Escenarios de demanda (P5, 18/11/2026)** (`src/cpd/modelos/escenarios.py`): la previsión a 10 años es tendencial (244 TWh en 2035) y no sabe que llegan grandes consumos. Red Eléctrica ya ha otorgado 18.535 MW de acceso a nuevos consumos y tiene 23.500 MW en trámite; usada al 80 %, la otorgada serían 130 TWh/año (la mitad de la demanda actual). Escenarios (supuestos a calibrar, sin dato abierto de realización): 25 % → 276 TWh, 50 % → 309 TWh, 100 % → 374 TWh, techo con lo pedido → 539 TWh. Aragón tiene otorgado el 243 % de su demanda. No es una previsión con acierto. Figura 19 y dato en la ficha.
- **Atracción empresarial (E42, 18/11/2026)** (`src/cpd/modelos/empresas.py`): sociedades mercantiles constituidas por provincia y mes (INE, tabla 6295, 2008-2025; dato nuevo) y su previsión a 1 año con el protocolo común (24 orígenes, test de un año). Elegido ETS (mejora a la combinación > 5 %). Total de 12 meses 93,4 % / 92,6 % (cumple); mes a mes 87,9 % / 84,6 % (orientativo, como las renovables). Indicador por 10.000 habitantes, figura 20 y línea en la ficha. Con esto, todas las variables del enunciado que piden un modelo lo tienen; lo pendiente de E es de datos (fibra, 5G, logística, parcelas, calidad del agua).
- **Afinado del 18/11/2026:** `prob_cpd` con datos nuevos (PIB provincial del INE; población + renta): mejora el log-loss (0,377 → 0,342) y el ROC (0,882 → 0,897) pero baja el acierto con umbral de 90,4 % a 84,6 %; con 52 provincias son 2-3 provincias de diferencia: no es mejora clara, se mantiene «solo población». Informe socioeconómico con los nombres de los productos en el reparto del CAPEX.
- **Comprobación externa: Aragón.** Aragón acumula unos 70.000 M€ de inversión anunciada en centros de datos (noticias, no es un dato del modelo). Con cada dato real nuevo Aragón sube en el score: Teruel 14.º → 13.º → 11.º, Huesca 39.º → 30.º → 22.º, Zaragoza 46.º → 35.º → 32.º. No llega arriba: Castilla y León le gana en clima (PUE), suelo (León 52 €/m², Zaragoza 140), cobertura renovable (241 % frente a 170 %) y red libre (10.299 MW frente a 89). No se fuerza. Datos reales que aún faltan: agua concedida, tramitación autonómica, suelo industrial y rutas reales de fibra.
- **Mapa:** muestra `prob_cpd`, la demanda de la comunidad y la nacional a 10 años, las reservas del ámbito, el VAN con distintos precios de la luz y gráficos de las previsiones con su acierto (interactivos: línea vertical y recuadro con el valor del mes al pasar el ratón, tocar o usar las flechas; tabla «Ver los datos»; real en azul y previsión en magenta, colores comprobados para daltonismo); las figuras del informe de previsiones usan el mismo estilo y ya no tienen doble eje (precio de la luz y gas en dos paneles); la clase roja se llama «No viable» y su icono es «sin cobertura» (barras vacías y un distintivo rojo con ×, se distingue sin color); la ficha tiene el gráfico de la temperatura prevista de la provincia; aviso de que el VAN de las viables solo varía entre 20,3 y 25,7 M€; recuadro de Canarias sin tapar Huelva ni Cádiz en pantallas estrechas.
- **Hallazgos:** (1) REData publica la demanda de jul-ago de 2026 sin el saldo de intercambios (su "demanda" es solo la generación: Madrid 123 GWh, Cantabria negativa). **Corregido en el curado:** `cpd.fuentes.calidad` la deja en NaN con registro en `data/curated/calidad_demanda_ccaa.csv`, y la demanda de un año se vuelve a pedir durante 12 meses, así que las correcciones de REData entrarán solas; (2) el VAN simulado depende casi solo de la temperatura (Spearman −0,99) y va en sentido contrario al número real de CPD: revisar el simulador.

## Resumen en una frase (auditoría del 14/11/2026)

El equipo tiene una **ingesta amplia y bien documentada, un almacén DuckDB, un simulador con tests y dos interfaces**,
pero **no tiene análisis exploratorio, ni correlaciones, ni modelos de Machine Learning evaluados, ni informes, ni vídeo ni manuales**,
y los pocos datos demo que siguen en la aplicación pueden confundirse con datos reales.

## Qué está hecho (✅)

| Área | Evidencia | Comentario |
|---|---|---|
| Ingesta de 12+ fuentes oficiales y abiertas | `src/ingesta/01…04`, `src/cpd/fuentes/*.py` (52 provincias por API) | Fallos de una fuente no paran el resto |
| Registro y hash de descargas | `data/raw/_registro_descargas.csv`, `docs/datos/manifiesto_raw_2026-11-09.csv` (472 ficheros) | Trazabilidad real |
| Tabla maestra provincia × mes | `data/curated/panel_provincia_mes.csv` (51 columnas), `.parquet` | Con diccionario `diccionario_panel_provincia_mes.csv` |
| Tabla de provincias actuales | `data/curated/provincias_actual.csv` (66 columnas) | Con tiempo real |
| Almacén DuckDB | `src/cpd/almacen.py`, `data/almacen/p3_cpd.duckdb` | Esquemas `fuentes`, `dw`, `meta` |
| Simulador de viabilidad | `src/cpd/simulator.py` (energía, agua, OPEX, CO2, latencia, VAN, ROI, payback) | Con tests |
| Filtros, sub-scores, score global y escenarios | `src/cpd/scoring.py` | Con tests |
| Tests automáticos | `tests/` (≈100 funciones `test_`; 105 casos según el encargo), frontend `vitest` (7) | Hay que volver a ejecutarlos antes de la entrega |
| Mapa web por provincias | `frontend/` (Vite + React + MapLibre) | Colores por rentabilidad |
| Aplicación Streamlit | `app/streamlit_app.py` (6 pestañas) | Usa datos demo |
| Configuración central | `config/settings.yaml` | Umbrales "a calibrar" |

## Qué está parcial (🟡)

| Área | Qué falta exactamente |
|---|---|
| Informe de origen de datos | `docs/datos/README.md` es borrador; falta la lista de todas las fuentes del enunciado y sus licencias |
| Limpieza y validación | Criterio de NaN en `curado.py`; falta informe de calidad, atípicos y política de imputación |
| Modelado de datos | Dimensiones y vista de hechos en DuckDB; falta documento, diagrama y granularidad declarada |
| Previsión | Validada a 1 año (24 orígenes) y a 10 años (demanda nacional, temperatura, consumo del CPD y agua; 18/11/2026); emisiones a 10 años no validables (mix por comunidad solo desde 2015) |
| Simulador | Faltan parámetros del CPD: superficie, salas, racks, servidores, almacenamiento PB, TFLOPS, tráfico Gbps, operadores; tier solo informativo |
| Escenarios y dashboards | Datos demo sintéticos en la app; sin manual de usuario |
| Variables territoriales | Muchas variables del brief no están en el panel (densidad, envejecimiento, nivel educativo, distancia a autopistas/puertos/aeropuertos, fibra, 5G…) |
| Escalado | Normalización min-max solo para sub-scores; falta escalado para modelos sin fuga |
| Código comentado | Hay docstrings; falta auditar que todas las funciones principales estén documentadas |
| Enumeraciones | Sin `enum` (ni en `src/`, `app/` ni `tests/`) |

## Qué falta (❌)

- ~~Análisis exploratorio, correlaciones, modelos ML, métricas y features~~: hechos el 17/11/2026 (ver novedades). Falta el notebook de EDA.
- **Informes:** análisis de datos, cuadro de mandos, visualización.
- **Manual de usuario**, **vídeo** con casos de uso.
- **Fuentes del enunciado no integradas:** AEMET (solo como variable de entorno), Confederaciones Hidrográficas, CNMC, Secretaría de Estado de Telecomunicaciones.
- **Roles y ramas** del equipo documentados; ninguna asignación de responsables.
- **`CLAUDE.md`, `AGENTS.md`, plantillas de PR e issue**: se crean con esta metodología (pendiente de revisión).

## Riesgos principales (ordenados por gravedad)

| # | Riesgo | Impacto | Mitigación propuesta |
|---|---|---|---|
| R1 | ~~No hay modelos ML evaluados~~ **Cerrado el 17/11/2026** | — | Mantener `python -m cpd.modelos` en verde y repetir tras cada actualización de datos |
| R2 | **Datos demo sintéticos** pueden confundirse con datos reales en la app o en el vídeo | Credibilidad y ética; R-1 | Etiqueta visible "DEMO sintético" en toda vista con datos demo; retirar demo de la entrega o usarlo solo como ejemplo |
| R3 | **Granularidad distinta a la del enunciado** (provincia frente a municipio) | Discrepancia con "cualquier municipio" | Decidir D1 en la semana 1 y redactar la justificación |
| R4 | **Fuentes sin integrar** (AEMET, CCHH, CNMC) | Pérdida de puntos en B1 y en variables | Integrar al menos una fuente de cada bloque o justificar la sustitución |
| R5 | **Sin informes escritos** (análisis, visualización, cuadro de mandos) | Tres entregables incompletos | Plantillas de [[08_Plantillas]] y calendario de escritura |
| R6 | **Vídeo y manuales al final** | Riesgo de falta de tiempo | Guion y grabación de prueba en la semana 3 |
| R7 | **Fuga de información** en previsión o en features | Resultados falsos, nota baja | Regla R-8 y auditoría de features |
| R8 | **Carga de trabajo concentrada** en una persona | Bloqueos | Reparto por roles en la semana 1 |
| R9 | **Repositorio público** con `.venv`, claves o datos grandes | Filtración o repo pesado | Revisar `.gitignore` y buscar claves antes de cada push |
| R10 | **Entorno de Windows** (rutas, PowerShell, encoding) | Scripts que fallan en otros equipos | Probar el manual de instalación en un equipo limpio |

## Las 8 faltas más importantes por prioridad

1. ~~Modelos frente al baseline, EDA, métricas y validación temporal~~ (hecho el 17/11/2026). Queda: **previsión a 10 años validada** (P5) y **notebook de EDA** (B5).
2. **Revisar el simulador**, que hoy solo distingue provincias por el clima (la demanda errónea de REData ya se filtra en el curado).
3. **Informe de análisis final** que integre `eda_panel.md` y `metricas.md` (F3).
4. **Informe de origen y calidad** con todas las fuentes, licencias, nulos y atípicos (F1, B3; fases 1-2).
5. **Vídeo con al menos tres casos de uso** y **manual de usuario** (F7, F9, G3).
6. **Documento de almacenamiento y diagrama del esquema en estrella** (F5, B4; fase 5).
7. **Parámetros del CPD que faltan** en el simulador (D1-D4, D6, D7, D18-D20).
8. **Integrar AEMET, Confederaciones Hidrográficas y CNMC, o justificar su sustitución** (B1, E18, E25-E29).

## Plan semanal hasta el 15/12/2026

Recomendación (no viene de clase). Cada semana cierra con revisión de [[06_Checklist_entrega]].

### Semana 1 · 16 al 22 de noviembre · Organización y datos base

- Reunión de equipo: roles, decisiones D1 a D6 aceptadas, base de ramas `main` (decisión sobre `develop`).
- Crear `notebooks/`, plantillas en `.github/` y `docs/` (ya propuestas).
- Informe de origen de datos completo (F1) y diccionario de todas las columnas.
- Auditar la etiqueta de datos demo en la app (R2).
- Primer EDA: histogramas y box plots del panel (B5 inicio).

### Semana 2 · 23 al 29 de noviembre · Calidad, correlación y modelado de datos

- Informe de calidad: nulos, duplicados, atípicos y decisiones (B3).
- Matriz de correlación Pearson y Spearman; pair plot; frase de causalidad en cada conclusión (B6, I20-I24).
- Esquema en estrella documentado y diagrama (F5, B4).
- Enums para tipo de refrigeración y tier (I9).
- Integrar AEMET o documentar sustitución (B1, R4).

### Semana 3 · 30 de noviembre al 6 de diciembre · Modelos y métricas

- Features: lags, diferencias, logaritmos y ventanas (I49-I53).
- Validación temporal y tres baselines (I30, I29).
- Al menos un modelo ML frente al baseline; model card (B7, B10).
- Métricas MAE, RMSE y backtesting; tabla de resultados (I33, I32).
- Parámetros del CPD que faltan en el simulador (D1-D4, D6, D7, D18-D20).
- Guion del vídeo y primera grabación de prueba (F7).

### Semana 4 · 7 al 13 de diciembre · Informes, manuales y vídeo

- Informes de análisis, visualización y cuadro de mandos (F2-F4).
- Manual de instalación probado en un equipo limpio (F8).
- Manual de usuario con capturas (F9).
- Auditoría de comentarios en funciones principales (F6) y revisión de código (G2).
- Vídeo final con al menos tres casos de uso (F7, G3).

### Semana final · 14 y 15 de diciembre · Cierre

- Lunes 14: checklist completa, tests en verde, etiqueta de entrega. Sin funcionalidades nuevas.
- Martes 15: subir a Moodle antes de la hora límite (no esperar al último minuto).

## Cómo se actualiza este documento

Cada semana, el responsable de la checklist cambia la fecha de "actualizado", resume en tres líneas lo hecho y lo pendiente, y
marca los riesgos que se han cerrado o han aparecido.
