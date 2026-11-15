---
tags: [fuente, enunciado, p3]
estado: revisada
actualizado: 2026-11-14
---

# Fuente · Enunciado "Proyecto 3 – Sistema de Predicción de Viabilidad para la Instalación de un CPD"

Archivo: `C:\Users\marcm\Downloads\P3 Enunciado.pdf` (12 páginas, leídas completas). Volver a [[00_Indice]].

## Resumen

El proyecto pide una plataforma Big Data que analice y prediga la viabilidad de instalar un Centro de Procesamiento de Datos (CPD o data center) en cualquier municipio español. La plataforma debe dar una puntuación global de viabilidad y previsiones a corto y medio plazo. Incluye 10 objetivos específicos, 8 preguntas que el simulador debe responder, decenas de variables del CPD y de su entorno territorial, cuatro entregables con sus evidencias y una rúbrica de niveles 1 a 6.

## Términos clave

Plataforma Big Data · puntuación global de viabilidad · previsiones a corto y medio plazo · ETL · Data Lake · Data Warehouse · análisis exploratorio · correlaciones · Machine Learning · simulador de escenarios · dashboards interactivos · series temporales · PUE · WUE · Tier I-IV · TFLOPS · PB · Gbps · latencia · estrés hídrico · embalses · free cooling · Red Natura · riesgo sísmico · inundación · huella de carbono · RA (M4RA1-M4RA4, M1RA5, M1RA6, M2RA3-M2RA5) · rúbrica · escala 1 a 6.

## Acciones obligatorias (lo que pide el texto)

1. Identificar y recopilar fuentes relevantes (p. 2, objetivo 1).
2. Diseñar procesos ETL para integrar datos heterogéneos (objetivo 2).
3. Limpiar, transformar y validar los datos (objetivo 3).
4. Diseñar un Data Lake y un Data Warehouse (objetivo 4).
5. Realizar análisis exploratorio de datos (objetivo 5).
6. Detectar correlaciones entre variables territoriales y la viabilidad de un CPD (objetivo 6).
7. Construir modelos predictivos mediante Machine Learning (objetivo 7).
8. Diseñar un simulador capaz de evaluar distintos escenarios (objetivo 8).
9. Crear dashboards interactivos para la toma de decisiones (objetivo 9).
10. Elaborar predicciones de evolución futura mediante series temporales (objetivo 10).
11. Responder las 8 preguntas del simulador (p. 3): municipios más adecuados, impacto local, disponibilidad energética, riesgo hídrico, demanda eléctrica a 10 años, coste operativo, retorno de inversión, zonas de menor riesgo regulatorio o ambiental.
12. Entregar: Documento de Especificación (5 informes), prototipo funcional con código comentado en control de versiones, vídeo de funcionamiento con diversos casos de prueba, manual de instalación y despliegue, y manual de usuario final (p. 8).
13. Cumplir la rúbrica en tres evidencias: documentación, código fuente y vídeo (p. 9-10).

## Variables que pide el enunciado (p. 2-7)

- **CPD (entrada del simulador):** infraestructura (superficie, salas técnicas, racks, servidores, potencia TI, almacenamiento, TFLOPS, tier); energía (consumo anual, potencia máxima, PUE, % renovable, producción fotovoltaica y eólica propia); agua (litros/día, tipo de refrigeración, WUE); conectividad (tráfico medio y pico, operadores, latencia); económico (inversión, OPEX, vida útil, personal).
- **Entorno territorial:** demografía (INE, datos de CCAA); energía (REE, MITECO); agua (Confederaciones Hidrográficas, MITECO, AEMET); climatología (temperatura, humedad, días de calor extremo, viento; justificación: un clima frío reduce la refrigeración); telecomunicaciones (CNMC, Secretaría de Estado de Telecomunicaciones); transporte y logística; suelo disponible (precio, parcelas, calificación, inundación, sísmico); impacto socioeconómico; impacto ambiental.

## Dónde aparece cada cosa en el repo (estado 14/11/2026)

Detalle en [[06_Checklist_entrega]], secciones A a H. Resumen: la mayoría de variables del CPD que son cálculo están; faltan parámetros de hardware (superficie, racks, servidores, PB, TFLOPS, Gbps). Del entorno, muchas variables están en fuentes descargadas pero no integradas en el panel; varias no tienen fuente.

## Enlaces encontrados en el PDF

Ninguno (se revisó el texto y las anotaciones del PDF).

## Cómo se aplica a P3

- Es el documento de referencia: toda tarea debe cerrar una fila de la checklist, que a su vez cita un requisito de este documento.
- Los **resultados de aprendizaje** (M4RA1…M2RA5) aparecen solo por código; su descripción no está en el PDF. Pedir la descripción oficial (ver [[06_Checklist_entrega]], sección H).
- El texto dice "cualquier municipio" pero el repo trabaja a nivel provincial: **decisión D1** en [[01_Objetivo_y_alcance]].
- El texto cita AEMET, CCHH y CNMC; no están integradas: decisión D2.

## Advertencias

- La escala de evaluación es 1 (no alcanzado) a 6 (excelente); el nivel 6 exige exhaustividad en documentación, un repositorio "perfectamente organizado" y un vídeo con variedad de casos de uso.
- Las fechas de entrega del enunciado no aparecen en el PDF; la fecha 15/12/2026 viene del encargo.
