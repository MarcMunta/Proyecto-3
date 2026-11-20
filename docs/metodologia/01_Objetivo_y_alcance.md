---
tags: [metodologia, objetivo, alcance, p3]
estado: borrador
actualizado: 2026-11-14
---

# 01 · Objetivo y alcance

Fuente principal: [[Enunciado]]. Volver a [[00_Indice]].

## Objetivo real en un párrafo

Construir una plataforma Big Data que, a partir de los **parámetros de un CPD** (superficie, potencia, PUE,
refrigeración, conectividad, inversión…) y de **datos territoriales abiertos** (energía, agua, clima, demografía,
telecomunicaciones, suelo, riesgos, impacto), **diga qué zonas de España son viables** para instalarlo, con una
**puntuación global de viabilidad** y sus motivos, **simule** energía, agua, costes, impacto y retorno en distintos
escenarios, y **prevea** la evolución a corto y medio plazo (sobre todo la demanda eléctrica a 10 años) con modelos
**evaluados con honestidad** (validación temporal y métricas adecuadas), todo ello **reproducible desde los datos
crudos** y presentado en **dashboards** para la toma de decisiones.

## Preguntas que el sistema debe responder

Del enunciado (sección "Análisis requerimientos funcionales"):

| # | Pregunta | Dato o módulo que la responde (previsto) | Estado en el repo |
|---|---|---|---|
| P1 | ¿Qué municipios son los más adecuados? | Filtros + score global + ranking (`scoring.py`) | 🟡 Ranking por provincia real; municipal solo con datos demo sintéticos |
| P2 | ¿Qué impacto tendrá el CPD sobre los recursos locales? | Impacto local en % del consumo municipal (`simulator.impacto_local_pct`) | 🟡 Fórmula sí; faltan datos municipales reales de consumo |
| P3 | ¿Existe suficiente disponibilidad energética? | Capacidad de acceso de la red (REE), subestaciones, producción | 🟡 Capacidad por nudo/CCAA; sin modelo de disponibilidad municipal |
| P4 | ¿Existe riesgo hídrico? | Estrés hídrico (WRI), embalses (MITECO), sequía (SPI-12 de `agua.py`) | 🟡 Datos sí; falta el análisis y la validación |
| P5 | ¿Cómo evolucionará la demanda eléctrica en 10 años? | Previsión mensual baseline (`forecast.py`, 120 meses) | 🟡 Baseline de tendencia + estacionalidad; sin evaluación de error |
| P6 | ¿Cuál será el coste operativo esperado? | OPEX (`simulator.opex_eur`, `desglose_opex`) | ✅ Fórmulas y tests; parámetros a calibrar |
| P7 | ¿Cuál será el retorno de inversión estimado? | VAN, ROI, payback (`simulator.py`) | ✅ Fórmulas y tests; parámetros a calibrar |
| P8 | ¿Qué zonas presentan menor riesgo regulatorio o ambiental? | Filtros (inundación, Natura 2000, sísmico) + sub-score | 🟡 Filtros sí; falta fuente y umbrales validados |

## Alcance: qué entra y qué no

### Dentro del alcance

- Los 10 objetivos específicos del enunciado (ver [[06_Checklist_entrega]], sección B).
- Las variables del CPD y del entorno territorial del enunciado, en la medida en que haya **fuente abierta**
  disponible y documentada.
- Simulador de escenarios, dashboards y previsiones (baseline + al menos un modelo ML evaluado).
- Documentación, código con comentarios en funciones principales, manual de instalación, manual de usuario
  y vídeo con varios casos de prueba.

### Fuera del alcance (salvo que el profesor lo pida)

- Datos privados de empresas o de clientes. No se piden ni se inventan.
- Compra de datos de pago o licencias. Solo fuentes abiertas o de acceso gratuito.
- Despliegue en la nube en producción. El entregable es un prototipo funcional y su documentación de despliegue local.
- Un modelo de negocio o un estudio de mercado completo (el enunciado pide el cálculo, no el plan de empresa).

### Decisiones de alcance que hay que tomar y documentar

| # | Tema | Lo que dice el enunciado | Lo que hay en el repo | Propuesta (recomendación, no viene de clase) |
|---|---|---|---|---|
| D1 | **Granularidad territorial** | "cualquier municipio español" | Panel real por **provincia** (52). Municipios: solo demo sintético (`data/demo/municipios_demo.csv`) | Presentar el sistema a nivel **provincia con datos reales** y dejar el nivel municipal como ampliación si hay datos. Decidirlo en equipo y escribirlo en la especificación. |
| D2 | **Fuentes citadas** | INE, datos abiertos CCAA, REE, MITECO, AEMET, Confederaciones Hidrográficas, CNMC, Secretaría de Estado de Telecomunicaciones | Integradas: INE, REE, MITECO, WRI, NASA POWER, Open-Meteo, OMIE, SEPE, OSM, PeeringDB, EMSC, Natura 2000. **No integradas:** AEMET, CCHH, CNMC (AEMET solo como placeholder en `.env.example`) | Documentar cada sustitución (p. ej. Open-Meteo por AEMET) con el motivo. Si no hay tiempo, dejarlo escrito como limitación. |
| D3 | **Modelos ML** | Objetivo 7: "modelos predictivos mediante Machine Learning" | **Resuelta el 17/11/2026:** modelos entrenados y evaluados frente a baselines (`src/cpd/modelos/`, `docs/modelos/`, `docs/analisis/metricas.md`) | Mantener: previsión de demanda por comunidad (1 y 12 meses) y `prob_cpd` por provincia. Pendiente: previsión a 10 años validada (P5). |
| D4 | **Análisis exploratorio** | Objetivo 5 y entregable "Informe de análisis de los datos" | Informe EDA en `docs/analisis/eda_panel.md` (17/11/2026); sin notebook | Añadir el notebook en `notebooks/` que llame a `cpd.modelos.eda`. Ver fase 4. |
| D5 | **Data Lake y Data Warehouse** | Objetivo 4 | Capa raw en `data/raw/` (no versionada salvo registro), DuckDB con esquemas `fuentes`, `dw` (dimensiones y vista de hechos) y `meta` | Completar el esquema en estrella y documentarlo (fase 5). |
| D6 | **Dashboards** | Objetivo 9 e "Informe de cuadro de mandos" | Streamlit (6 pestañas) y mapa web (Vite + React + MapLibre) | Decidir cuál es el cuadro de mandos oficial o justificar los dos. |
| D7 | **Precio de la luz del simulador** | El VAN y el OPEX dependen del precio de la energía | Media spot de los últimos 12 meses (80 €/MWh); la previsión a 1 año (`docs/analisis/previsiones_1_anio.md`) da 153 €/MWh y, con ella, el VAN es negativo en las 52 provincias | **Decidida el 17/11/2026:** se mantiene la media de 12 meses como precio base (supuesto conocido y estable para comparar provincias). La previsión a 1 año y su rango se enseñan en la ficha como escenarios del VAN. Revisar si el precio se mantiene alto. |

## Entregables y fechas

Fuente: tabla "Contenido de la entrega" del enunciado. Los códigos `M4RA1…` son los resultados de aprendizaje
que afecta cada entregable (las descripciones de cada RA no están en el enunciado).

| Entregable | Evidencia | RA afectados |
|---|---|---|
| Documento de Especificación del Proyecto | Informe de origen de datos | M4RA1 |
| | Informe de cuadro de mandos | M4RA2 |
| | Informe de análisis de los datos | M4RA2 |
| | Informe de visualización de datos | M4RA4 |
| | Documentación descriptiva del sistema de gestión y almacenamiento de datos | M4RA3 |
| Prototipo funcional de la plataforma de predicción | Código fuente con comentarios en las funciones principales, en sistema de control de versiones | M4RA1, M4RA2, M4RA3, M4RA4 |
| Vídeos de funcionamiento | Vídeo del sistema funcional con diversos casos de prueba | M4RA1, M4RA2, M4RA3, M4RA4 |
| Documentación detallada para el despliegue y mantenimiento | Manual de instalación y despliegue del sistema | M4RA1, M4RA3 |
| | Manual de usuario final | M4RA2, M4RA4 |

**Fecha de entrega: 15/12/2026 en Moodle.** Desde hoy (14/11/2026) quedan 31 días.
El plan semanal está en [[07_Estado_actual]].

## Evaluación (resumen)

Tres evidencias con rúbrica de niveles 1 a 6 (escala: 1 No alcanzado, 2 Insuficiente, 3 Suficiente, 4 Bien,
5 Notable, 6 Excelente):

- **Documentación:** nivel 6 exige una descripción exhaustiva, detallada y profesional de todos los requisitos
  funcionales y no funcionales, y del prototipo.
- **Código fuente del prototipo:** nivel 6 exige un repositorio completo, mantenible y perfectamente organizado.
- **Vídeo del prototipo:** nivel 6 exige una variedad de casos de uso que demuestren funcionalidad y eficacia.

Detalle y comprobaciones: [[06_Checklist_entrega]], sección F.

## Criterio de "terminado" del proyecto

El proyecto está terminado cuando:

1. Un tercero puede clonar el repositorio, seguir el manual de instalación y ver el sistema funcionar con datos
   reales (o con la copia de la Release, ver [[04_Reglas_de_datos]]).
2. Cada pregunta P1 a P8 tiene una respuesta visible en la aplicación o en el informe, con su limitación escrita.
3. Todos los objetivos 1 a 10 y todos los entregables de la tabla tienen evidencia (fila ✅ en [[06_Checklist_entrega]]).
4. El vídeo muestra al menos tres casos de uso distintos.
