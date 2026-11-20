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
- **Mapa:** muestra `prob_cpd`, la demanda de la comunidad y el VAN con distintos precios de la luz; la clase roja se llama «No viable»; aviso de que el VAN de las viables solo varía entre 20,3 y 25,7 M€; recuadro de Canarias sin tapar Huelva ni Cádiz en pantallas estrechas.
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
| Previsión | Validada a 1 y 12 meses con backtesting (17/11/2026); falta la previsión a 10 años validada (P5) |
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
