---
tags: [metodologia, flujo, metodo, p3]
estado: borrador
actualizado: 2026-11-14
---

# 03 · Flujo de trabajo (el método)

Volver a [[00_Indice]]. Relacionadas: [[04_Reglas_de_datos]], [[05_Reglas_de_codigo_y_git]], [[06_Checklist_entrega]], [[07_Estado_actual]].

Este es el **orden de trabajo** del proyecto. Cada fase tiene objetivo, entradas, pasos, técnicas de clase con
referencia a la página del PDF, salidas (con su ubicación en el repositorio), una **definición de "hecho"** y los
**errores frecuentes**. Las referencias tienen la forma `[C2 p.13]`, donde `C1`…`C4` son las cuatro clases
(ver [[00_Indice]]) y `E` es el enunciado.

Regla general: **no se pasa a la fase siguiente sin cumplir la definición de "hecho"** de la anterior.
Las fases se solapan en la práctica (por ejemplo, el EDA destapa errores de limpieza), pero cada cambio vuelve a
dejar la fase anterior en orden.

```
0 Organización ─► 1 Ingesta ─► 2 Calidad y limpieza ─► 3 Transformación y escalado
                                                              │
   11 Documentación, vídeo y entrega ◄─ 10 Dashboards ◄─ 9 Simulador ◄─ 8 Métricas ◄─ 7 Modelos ◄─ 6 Features ◄─ 5 Modelado de datos ◄─ 4 EDA
```

Leyenda de técnicas: **[recomendación (no viene de clase)]** = buena práctica propuesta por el equipo que no aparece
en los PDF.

---

## Fase 0 · Organización

**Objetivo.** Dejar claro quién hace qué, cómo se trabaja y dónde se guarda cada cosa, antes de programar.

**Entradas.** Enunciado ([[Enunciado]]), esta metodología, decisiones pendientes de [[01_Objetivo_y_alcance]] (D1 a D6).

**Pasos.**
1. Reunir al equipo y asignar roles. La clase propone cinco grupos: Dirección, Data Cleaners, Data Visualization,
   Data Filters y R&D, más un flujo principal ("main script flux master") [C1 p.9-10]. Un equipo puede juntar roles
   pero cada tarea debe tener **un responsable**.
2. Decidir la granularidad territorial (D1), las fuentes que se usan y las que se sustituyen (D2) y si el
   entrenamiento de modelos entra en la entrega (D3). Anotarlo en un acta corta en `docs/` (recomendación, no viene de clase).
3. Crear las carpetas del proyecto con la regla de la clase: `data/` solo con datos usados, funciones directas en
   una carpeta de utilidades y configuración global en `config/` [C1 p.12-13]. En el repo ya existe `src/cpd/`
   en lugar de `utils/`: la decisión se documenta en [[05_Reglas_de_codigo_y_git]].
4. Crear las ramas de trabajo según [[05_Reglas_de_codigo_y_git]] (`feature/...`) [C1 p.10-11].
5. Preparar el tablero de tareas (recomendación, no viene de clase): una tarjeta por tarea, con la plantilla de
   [[08_Plantillas]] y un enlace al requisito de [[06_Checklist_entrega]].
6. Fijar la reunión semanal y la revisión de la checklist.

**Técnicas de clase.** Trabajo en equipo con Git y ramas [C1 p.6-11]; reparto de roles [C1 p.9-10]; brainstorming
inicial y "un proyecto de equipo como empresa" [C1 p.7-8]; enums como buena práctica (puntos extra) [C1 p.13].

**Salidas y dónde viven.**
- Acta de decisiones D1 a D6 → `docs/metodologia/01_Objetivo_y_alcance.md` (sección de decisiones) y, si se amplía, `docs/decisiones/` (recomendación).
- Roles y responsables → [[06_Checklist_entrega]] (columna "owner").
- Tablero de tareas → herramienta del equipo (fuera del repo).

**Hecho cuando.** Cada rol tiene nombre; las decisiones D1 a D6 están escritas y aceptadas; las ramas y carpetas existen y están documentadas.

**Errores frecuentes.** Empezar a programar sin decidir la granularidad; dos personas editando el mismo fichero a la vez; no nombrar responsable de la checklist.

**Estado actual.** Parcial: carpetas y ramas funcionan (ver [[07_Estado_actual]]); faltan decisiones D1 a D6 aceptadas y roles asignados.

---

## Fase 1 · Ingesta (APIs, capa raw y registro)

**Objetivo.** Obtener las fuentes de datos abiertos de forma **reproducible**, guardarlas tal cual en la capa raw y dejar registro de cada descarga. Es la "E" del ETL.

**Entradas.** Lista de fuentes del enunciado (INE, datos abiertos de CCAA, REE, MITECO, AEMET, Confederaciones Hidrográficas, CNMC, Secretaría de Estado de Telecomunicaciones) [E p.2-5]. Enlaces de la clase: portal de datos abiertos de Barcelona [C1 p.5].

**Pasos.**
1. Hacer un **catálogo de fuentes**: nombre, organismo, URL, formato, cobertura temporal y geográfica, licencia, frecuencia de actualización, clave de unión. Ya existe en `docs/datos/README.md` y `docs/datos/tablas_api.md`; completarlo con las fuentes que faltan (D2).
2. Descargar con script (nunca a mano): un script por fuente en `src/ingesta/` o `src/cpd/fuentes/`.
3. Guardar en `data/raw/<fuente>/<fecha>/` **sin modificar** el contenido.
4. Registrar cada descarga en `data/raw/_registro_descargas.csv` (fuente, URL, fecha, tamaño) y calcular el hash SHA-256 en el manifiesto (`docs/datos/manifiesto_raw_<fecha>.csv`).
5. Ser tolerante a fallos: si una fuente falla, el resto sigue y el resumen lo muestra (ya ocurre en `cpd.fuentes.actualizar`).
6. Tipos de datos: anotar si cada fuente es relacional/tabular, JSON, XLSX o Access [C1 p.3]. Distinguir cualitativo y cuantitativo [C1 p.4].
7. Si se usan datos propios (encuesta, fotos, registros) [C1 p.5], documentar cómo se obtienen y su sesgo. El enunciado no los pide.

**Técnicas de clase.** Adquisición desde datos abiertos y desde fuentes propias; convertir todo a un formato común ("common ground") [C1 p.5]; tipos de datos relacionales, no relacionales, tabulares y no tabulares [C1 p.3]; datos cualitativos y cuantitativos [C1 p.4].

**Salidas y dónde viven.**
- Código de ingesta → `src/ingesta/`, `src/cpd/fuentes/`.
- Capa raw → `data/raw/` (fuera de git, salvo el registro; ver [[04_Reglas_de_datos]]).
- Registro y manifiesto → `data/raw/_registro_descargas.csv`, `docs/datos/manifiesto_*.csv`.
- **Informe de origen de datos** (entregable M4RA1) → `docs/datos/README.md` (hoy borrador).

**Hecho cuando.** Cada fuente del catálogo tiene un script que la descarga, una fila en el registro, un hash en el manifiesto, y aparece en el informe de origen con cobertura y limitaciones. Un tercero puede repetir la descarga con un comando.

**Errores frecuentes.** Descargar a mano y no poder repetir; modificar el fichero raw "para arreglarlo"; no guardar la URL y la fecha; mezclar la fecha de descarga con la fecha de los datos; confiar en un enlace que cambia.

**Estado actual.** Mayoritariamente hecho para 12 fuentes; faltan AEMET, Confederaciones Hidrográficas y CNMC (ver [[06_Checklist_entrega]]).

---

## Fase 2 · Calidad y limpieza

**Objetivo.** Dejar cada fuente con tipos correctos, sin duplicados sin explicar, con los valores ausentes tratados
de forma explícita, con las unidades claras y con los atípicos identificados y decididos.

**Entradas.** Capa raw (fase 1) y diccionario de origen.

**Pasos.**
1. **Tipos.** Leer cada fuente con su codificación, separador y decimal reales (CSV del INE con `;`, miles con punto,
   decimales con coma; SEPE en latin-1 con una línea de título). Los códigos INE son **texto con ceros a la izquierda**
   (ver [[04_Reglas_de_datos]]).
2. **Claves.** Normalizar el código de provincia (2 dígitos) y de municipio (5 dígitos). Filtrar los códigos que no
   están en el diccionario INE 2026 (8.132 municipios; el padrón trae unos 8.138).
3. **Duplicados.** Comprobar que la clave (p. ej., provincia + mes) es única. Si hay duplicados, explicar la causa y la regla.
4. **Valores ausentes (missing values).** Para cada columna, contar nulos y decidir:
   - no imputar, dejar NaN y documentarlo (preferido cuando la fuente no tiene dato);
   - imputar con regla explícita (p. ej., media del año, o interpolación) solo si está justificada y marcada en una columna aparte;
   - eliminar la fila solo si el hueco hace inútil la observación.
   El SEPE usa `<5` por secreto estadístico: tratarlo como ausente o como rango 0-4, y decirlo.
5. **Atípicos (outliers).** Mirarlos con un **box plot** y un histograma [C2 p.8, p.10]. Un criterio habitual es el rango
   intercuartílico (IQR), [recomendación (no viene de clase)]. Decidir por variable si el valor es error (corregir o
   anular), caso real (conservar) o caso extremo que se recorta (winsorizing, fase 3). Nunca borrar en silencio.
6. **Unidades.** Poner la unidad en el nombre de cada columna (`demanda_mwh`, `precipitacion_mes_mm`, `renta_neta_media_hogar_eur`).
7. **Textos.** Corregir codificación (mojibake, por ejemplo "AndalucÃ­a") leyendo con la codificación correcta.
8. **Validación.** Escribir comprobaciones automáticas: rangos plausibles, totales que cuadran, número de filas
   esperado (p. ej., 52 provincias × meses). Son tests de datos (`tests/test_datos_nuevos.py`).

**Técnicas de clase.** Box plot para outliers y cuartiles [C2 p.10]; histograma para distribuciones [C2 p.8]; las
transformaciones de escala y de tratamiento de valores extremos se detallan en la fase 3 [C4 p.8].

**Salidas y dónde viven.**
- Limpieza reproducible → `src/cpd/fuentes/curado.py` y scripts de `src/ingesta/`; salidas intermedias en `data/clean/`.
- **Informe de calidad** (recomendación, no viene de clase): tabla con % de nulos, duplicados, outliers y decisión por variable. Va a `docs/datos/` y es insumo del informe de análisis.
- Tests de validación → `tests/`.

**Hecho cuando.** Cada columna de la tabla limpia tiene tipo, unidad, nº de nulos y decisión de tratamiento documentada; los tests de validación pasan; no hay código de provincia o municipio sin tratar.

**Errores frecuentes.** Leer el código INE como número y perder el cero inicial; imputar con la media sin mirar el hueco; borrar outliers sin registrar cuántos; mezclar meses de distinto año; no tratar los `<5` del SEPE.

**Estado actual.** Parcial: `curado.py` documenta el criterio NaN; no hay informe de calidad ni análisis de atípicos (ver [[07_Estado_actual]]).

---

## Fase 3 · Transformación, normalización y escalado (sin perder datos)

**Objetivo.** Unir todas las fuentes en **tablas maestras** comparables (un "common ground") y transformar las
variables para que sean comparables, **sin perder información**.

**Entradas.** Datos limpios (fase 2) y el diccionario de datos.

**Pasos.**
1. **Tabla maestra.** Unir por claves (código de provincia, mes) con una granularidad declarada (p. ej., provincia × mes). Una fila por clave; las variables anuales se repiten en los meses de su año (como hace `curado.py`) y se dice en el diccionario.
2. **Conservar las columnas originales.** Escalar o transformar **creando columnas nuevas** (`_norm`, `_log`, `_z`), nunca sobrescribiendo la original. Así no se pierde información y se puede volver atrás.
3. **Escalado.** Elegir el método según el caso:
   - **Min-max** `(x − min)/(max − min)` → rango 0 a 1. Útil para scores y comparaciones directas [C4 p.23]. Sensible a outliers.
   - **Z-score** `(x − media)/σ` → media 0 y desviación 1. Útil para modelos que asumen escalas parecidas [C4 p.23]. Más robusto que min-max con datos sin outliers extremos.
   - **Log** `log1p(x)` para variables muy asimétricas (consumos, población, precios muy dispersos) [C4 p.25-26].
   - **Winsorizing** (recortar a percentiles 1 % y 99 %) para atípicos que no son error y no se quieren eliminar [C4 p.8].
   Regla: **ajustar el escalador (media, min, max) solo con los datos de entrenamiento** y aplicarlo después a validación y test (ver [[04_Reglas_de_datos]], regla de fugas).
4. **Transformaciones polinómicas** (x², x³) solo si la relación no lineal lo justifica y se mide [C4 p.8].
5. **Codificación de categóricas** [C4 p.9, p.20-21]:
   - one-hot para pocas categorías (tipo de refrigeración, CCAA si no son demasiadas);
   - frequency encoding para muchas categorías (municipios);
   - target encoding solo si se calcula dentro de cada partición de entrenamiento (riesgo de fuga).
6. **Enumeraciones.** Los valores válidos de cada categoría (p. ej., `aire | evaporativa | adiabatica | inmersion`) se definen como `enum` en el código, no como cadenas sueltas [C1 p.13].
7. **Codificación de fuentes.** Los textos se pasan a UTF-8 y los números a formato punto decimal en la salida.

**Técnicas de clase.** Normalización y estandarización (MAX-MIN, Z-SCORE) [C4 p.23-24]; transformación logarítmica [C4 p.25-26]; winsorizing y polinómicas [C4 p.8]; one-hot, frequency y target encoding [C4 p.9, 20-21]; enums [C1 p.13].

**Salidas y dónde viven.**
- Tabla maestra → `data/curated/panel_provincia_mes.parquet` (y `.csv`), `provincias_actual`.
- Diccionario → `data/curated/diccionario_*.csv` (debe incluir columna de transformación aplicada).
- Código → `src/cpd/fuentes/curado.py`.

**Hecho cuando.** Cada columna derivada tiene su original conservada, su transformación documentada en el diccionario, y el escalador solo se ajusta con datos de entrenamiento. Un test comprueba que la suma de filas y las claves no cambian.

**Errores frecuentes.** Sobrescribir la columna original; escalar antes de dividir en train y test (fuga); usar la media de todo el periodo para escalar; aplicar log a columnas con ceros sin `log1p`; crear one-hot de cientos de municipios; ocultar un cambio de granularidad.

**Estado actual.** Parcial: la tabla maestra provincial existe (51 columnas); faltan escalado documentado para modelos, transformaciones logarítmicas y codificaciones de categóricas (ver [[07_Estado_actual]]).

---

## Fase 4 · EDA, visualización y correlación

**Objetivo.** Entender los datos antes de modelarlos: distribuciones, relaciones, atípicos, faltas y relaciones
con la viabilidad. Produce el **informe de análisis de los datos** (M4RA2) y el **informe de visualización** (M4RA4).

**Entradas.** Tabla maestra y diccionario (fase 3).

**Pasos.**
1. **Resumen general.** Dimensiones, tipos, nulos, rangos y cardinalidad por variable (tabla de una página).
2. **Univariante.** Un histograma por variable numérica [C2 p.8] y un gráfico de barras por categoría [C2 p.7]. Un box plot por variable para atípicos y cuartiles [C2 p.10]. Una **serie temporal** por variable relevante con gráfico de líneas [C2 p.6].
3. **Bivariante.** Diagramas de dispersión entre variables candidatas y la variable objetivo (p. ej., demanda o score) [C2 p.9]. Mirar patrones, no solo el número.
4. **Matriz de correlación.** Heatmap de la matriz de correlación [C2 p.11]. Calcular **Pearson** (lineal, sensible a outliers), **Spearman** (monótona, basada en rangos, robusta) y **Kendall** (muestras pequeñas) [C2 p.23-24]. Si Pearson y Spearman difieren mucho, hay outliers o relaciones no lineales: decirlo.
5. **Pair plot.** Un pair plot de las variables seleccionadas para explorar relaciones en conjunto [C2 p.13].
6. **Multicolinealidad.** Detectar pares de variables con correlación muy alta (recomendación, no viene de clase) y decidir cuál conservar.
7. **Correlación no es causalidad.** En cada conclusión, escribir qué se ha observado y qué **no** se puede afirmar. La clase lo marca como falacia central [C2 p.18-21].
8. **Pie charts.** Uso limitado: solo para repartos de un total con pocas partes [C2 p.12]. Preferir barras.
9. **Informe.** Un apartado por pregunta P1 a P8 y un apartado de limitaciones.

**Técnicas de clase.** Gráficos de línea, barra, histograma, dispersión, box plot, heatmap, pie y pair plot [C2 p.6-13]; correlación de −1 a 1 [C2 p.15]; Pearson, Spearman y Kendall [C2 p.23-24]; falacias y causalidad [C2 p.18-21]; examen de clase con scatter plot de dos variables [C2 p.4] (ejercicio, no entregable).

**Salidas y dónde viven.**
- Notebook(s) de EDA → `notebooks/` (carpeta a crear; ver [[05_Reglas_de_codigo_y_git]] y [[08_Plantillas]]).
- Informe de análisis → `docs/analisis/` (a crear) y apartado en el documento de especificación.
- Informe de visualización → `docs/visualizacion/` (a crear).

**Hecho cuando.** Hay un notebook que se ejecuta de principio a fin sin errores; cada gráfico tiene título, ejes con unidades y una frase de interpretación; hay una matriz de correlación con Pearson y Spearman; cada conclusión incluye su limitación.

**Errores frecuentes.** Interpretar correlación como causa; usar Pearson con outliers sin mirar Spearman; gráficos sin unidades; escalas que exageran diferencias; pie charts con muchas categorías; no guardar el notebook con su salida.

**Estado actual.** Pendiente: no hay notebook de EDA, ni pair plot, ni matriz de correlación, ni informe (ver [[07_Estado_actual]]).

---

## Fase 5 · Modelado de datos y relaciones

**Objetivo.** Diseñar el almacén (Data Warehouse) y las relaciones entre tablas: claves, granularidad, dimensiones y hechos. Es el **documento descriptivo del sistema de almacenamiento** (M4RA3).

**Entradas.** Tablas limpias y maestras (fases 2-3); requisitos de consulta de los dashboards y del simulador.

**Pasos.**
1. Declarar, para cada tabla, **granularidad** (una fila = ...), **clave primaria** y **claves foráneas** [C1 p.3; recomendación para la granularidad].
2. Separar **dimensiones** (provincia, CCAA, tiempo, fuente, tipo de refrigeración) y **hechos** (demanda, reserva, precio, población por provincia y mes).
3. Dibujar el **esquema en estrella** (star schema): una tabla de hechos en el centro y las dimensiones alrededor.
4. Justificar la elección de **modelo relacional** frente a no relacional: el dato es tabular, con claves claras y consultas por cruce; los no relacionales (documentos, grafos) convienen cuando el esquema cambia mucho o la relación entre entidades es el centro del problema [C1 p.3; C2 examen preguntas 3 y 4].
5. Definir **tipos** de cada columna y los **enum** de categorías [C1 p.13].
6. Registrar la carga: fuente, fecha, número de filas en `meta.carga` (ya existe en DuckDB).
7. Documentar el **diagrama** y las reglas de actualización (qué se recarga y cuándo).

**Técnicas de clase.** Datos relacionales y no relacionales [C1 p.3]; grafos, nodos e influencers como concepto de estructuras de datos [C2 examen p.4] (no es requisito de P3, pero sirve para justificar la elección); enums [C1 p.13].

**Salidas y dónde viven.**
- Almacén → `data/almacen/p3_cpd.duckdb` con esquemas `fuentes`, `modelo`, `dw` y `meta`; código en `src/cpd/almacen.py`.
- **Documento descriptivo** → `docs/datos/` (apartado de almacenamiento) o `docs/almacen.md` (recomendación).
- Diagrama → `docs/` como imagen o texto (Mermaid es válido, recomendación).

**Hecho cuando.** Cada tabla tiene granularidad y clave escritas; el diagrama coincide con el código; una consulta de ejemplo (p. ej., "ranking de provincias por demanda en 2025") se resuelve con joins de la estrella.

**Errores frecuentes.** Tablas sin clave; granularidad mezclada (anual y mensual en la misma tabla sin decirlo); dimensiones con valores duplicados; no versionar el esquema; guardar la BD dentro del repo (está en `.gitignore`).

**Estado actual.** Parcial: existen `dw.dim_provincia`, `dw.dim_tiempo`, `dw.dim_fuente` y la vista `dw.fact_provincia_mes`; falta la documentación del esquema y el diagrama (ver [[07_Estado_actual]]).

---

## Fase 6 · Feature engineering (ingeniería de variables)

**Objetivo.** Crear variables nuevas que ayuden al modelo a aprender, a partir del conocimiento del dominio y del tiempo. Los modelos no encuentran tendencias ni relaciones por sí solos [C4 p.5].

**Entradas.** Tabla maestra (fase 3), EDA (fase 4), esquema (fase 5).

**Pasos.**
1. **Lags (retardos).** Para cada variable temporal relevante, crear `valor(t−1)`, `valor(t−3)`, `valor(t−12)`. Son la feature más importante en previsión: "sin ellos no podemos asegurar que nada funciona" [C4 p.12]. Se pueden usar también valores futuros solo como objetivo, nunca como entrada.
2. **Ventanas móviles (rolling).** Media, máximo, mínimo y desviación típica en ventanas de 3, 6 y 12 meses. Suavizan ruido y capturan la tendencia [C4 p.15]. El repo ya tiene una suma móvil de 12 meses (sequía) en `agua.py`.
3. **Estacionalidad.** Variables de mes, trimestre y "factor estacional" calculado con datos de entrenamiento [C4 p.16]. El baseline de `forecast.py` ya usa un factor por mes.
4. **Estacionariedad.** Si la serie tiene tendencia, usar **diferencias** `y_t − y_{t−1}` [C4 p.17] o restar la tendencia. Comprobarlo con el gráfico y con la media y la varianza por año.
5. **Transformaciones.** Logaritmo `log1p` en variables muy asimétricas [C4 p.25-26].
6. **Eventos.** Marcar, como variable binaria, los hechos conocidos que alteran la serie (DANA, cortes, crisis de precios, cambios de regulación). La clase pone de ejemplo la DANA y el Black Friday [C4 p.18].
7. **Variables categóricas.** Codificar como en la fase 3 [C4 p.9, p.20-21].
8. **Variables semánticas.** Crear variables con el conocimiento del dominio: zona climática, ámbito hidrográfico, distancia a un nodo de red, rankings, extracciones de texto [C4 p.10, p.27-28]. Ejemplo de clase con Pokémon: "completar la tabla con lo que sabemos" [C4 p.28].
9. **Polinómicas** solo si se justifica [C4 p.8].
10. **Control de fuga.** Cada feature se calcula **solo con datos anteriores al momento que predice**. Revisar cada una con la pregunta: "¿esto lo sabría en la fecha de la predicción?" (regla de [[04_Reglas_de_datos]]).

**Técnicas de clase.** Lags, ventanas móviles, estacionariedad, diferencias, eventos [C4 p.12-18]; escalado y normalización [C4 p.23-24]; log [C4 p.25-26]; semánticas [C4 p.27-28]; categóricas [C4 p.19-21].

**Salidas y dónde viven.**
- Código de features → `src/cpd/features/` (a crear; recomendación) con una función por familia.
- Tabla de features → `data/curated/` con sufijo `_features` o en la base DuckDB, esquema `modelo`.
- Diccionario de features (nombre, fórmula, ventana, fuente, riesgo de fuga) → `data/curated/diccionario_features.csv` (recomendación).

**Hecho cuando.** Cada feature tiene fórmula y ventana escritas; un test comprueba que ninguna feature usa datos posteriores a la fecha que predice; la tabla de features se regenera con un comando.

**Errores frecuentes.** Lags que miran al futuro; rolling calculado con la fila actual incluida cuando el objetivo es esa fila; one-hot con miles de columnas; target encoding sin partición; features duplicadas (correlación 1).

**Estado actual.** Pendiente: no hay lags ni features para ML; solo hay una suma móvil y el factor estacional del baseline (ver [[07_Estado_actual]]).

---

## Fase 7 · Modelado y previsión

**Objetivo.** Construir **primero un baseline** y después modelos de Machine Learning que lo superen, con una división
temporal honesta. Responde a los objetivos 7 y 10 y a las preguntas P5.

**Entradas.** Tabla de features (fase 6), periodo de entrenamiento y validación definido.

**Pasos.**
1. **Definir el problema.** Qué se predice (demanda mensual nacional o por CCAA, precio, reservas, score de viabilidad), con qué horizonte (en el repo, hasta 120 meses) y con qué frecuencia.
2. **Baselines.** Empezar siempre por modelos simples: "el último valor" (naive), "el mismo mes del año anterior" (seasonal naive) y la **tendencia + estacionalidad** que ya existe en `forecast.py`. Todo modelo más complejo debe superarlos en la métrica elegida.
3. **División temporal.** Dividir **por fecha**: entrenamiento (pasado), validación (periodo intermedio, para elegir), test (el más reciente, usado una sola vez). Nunca aleatorio en series temporales [C3 p.4 "ventana temporal"; recomendación para la técnica concreta].
4. **Modelos ML.** Como mínimo, un modelo de regresión lineal o regularizada con las features, y un modelo de árboles (p. ej., gradient boosting) [recomendación, no viene de clase]. Mismo conjunto de features y mismas particiones para comparar.
5. **Backtesting.** Repetir la previsión en varias fechas de corte del pasado y promediar el error [recomendación, no viene de clase].
6. **Intervalos.** Mostrar incertidumbre. El baseline ya calcula un intervalo aproximado ±1,96 σ de los residuos; explicar sus límites.
7. **Ajuste.** Elegir hiperparámetros solo con validación; el test no se toca hasta el final.
8. **Guardar el modelo** con su **model card** (ver [[08_Plantillas]]) y su fecha de entrenamiento.
9. **Previsión a 10 años** con la misma metodología, mostrando que el horizonte largo tiene más incertidumbre.

**Técnicas de clase.** Previsión y causas de su fallo: datos mal preparados, mala estacionalidad, variables externas mal integradas, fuga de información, horizonte o ventana temporal incorrectos, métricas mal interpretadas [C3 p.3-4]. Mirar siempre la calidad de la previsión [C3 p.5-6].

**Salidas y dónde viven.**
- Código → `src/cpd/forecast.py` (baseline) y `src/cpd/modelos/` (a crear; recomendación).
- Modelos guardados → `models/` (fuera de git si son grandes; recomendación) con su model card en `docs/modelos/`.
- Resultados de validación → tabla en `docs/analisis/` (ver fase 8).

**Hecho cuando.** Hay al menos tres baselines y un modelo ML evaluados con la misma división temporal; el test se ha usado una vez; el modelo supera al baseline en la métrica de la fase 8 o se documenta por qué no; la model card está completa.

**Errores frecuentes.** Dividir al azar; escalar o imputar con datos del test; elegir el modelo por el test; no comparar con un baseline; prever a 10 años sin decir que la incertidumbre es enorme; usar una feature que contiene el objetivo.

**Estado actual.** Parcial: solo existe el baseline de tendencia + estacionalidad, sin validación ni backtesting. **No hay modelos ML entrenados** (decisión de aplazar, ver D3 en [[01_Objetivo_y_alcance]]).

---

## Fase 8 · Métricas y evaluación

**Objetivo.** Medir cada modelo con las métricas adecuadas al tipo de problema, interpretarlas con su coste de error y detectar errores de diseño.

**Entradas.** Predicciones de validación y test (fase 7); clase de problema (regresión o clasificación).

**Pasos.**
1. **Elegir la métrica según el problema** [C3 p.7-13]:
   - **Regresión** (valor numérico, p. ej., demanda): medir la **distancia** entre predicción y valor real [C3 p.10-11]. La clase no nombra fórmulas; se propone usar **MAE** (error absoluto medio) y **RMSE** (raíz del error cuadrático medio), y **MAPE** solo si no hay ceros [recomendación, no viene de clase].
   - **Clasificación** (p. ej., viable / no viable): **matriz de confusión** [C3 p.15-17], después **accuracy, precision, recall, F1, ROC-AUC y log-loss** [C3 p.14].
2. **Matriz de confusión** con TP, TN, FP, FN [C3 p.15-17]. Escribir qué significa cada celda en el contexto del CPD.
3. **Precision y recall** según el coste del error [C3 p.14, 23]. Ejemplo para el CPD: un falso "viable" (FP) puede costar una inversión de cientos de millones; un falso "no viable" (FN) cuesta una oportunidad.
4. **ROC-AUC** siempre que haya un modelo de probabilidad: la clase la marca como la que siempre hay que mirar [C3 p.19]. Usar la curva para **elegir umbral** (TPR frente a FPR) [C3 p.19].
5. **Paradoja de la exactitud.** Comprobar si un accuracy alto es solo la clase mayoritaria [C3 p.23]. Comparar siempre con un modelo que predice la clase más frecuente.
6. **Coste de los errores.** No todos pesan igual [C3 p.8]. Escribir la regla de coste en la model card.
7. **Sesgos.** Comprobar sesgos de los datos y de las predicciones por subgrupos (p. ej., por CCAA o tamaño de municipio) [C3 p.22-24]. La clase pide hacerlo con código.
8. **Métricas de la previsión frente al baseline** en la misma tabla.
9. **Interpretar siempre.** Cada métrica con una frase: qué mide, qué valor es aceptable y por qué.

**Técnicas de clase.** Métricas de regresión y de clasificación [C3 p.9-14]; matriz de confusión y tipos de error [C3 p.15-17]; TPR y FPR [C3 p.19]; ROC-AUC y umbral [C3 p.19]; paradoja de la exactitud [C3 p.23]; sesgos [C3 p.22-24]; coste de un error [C3 p.8]; ejemplo de clase AutoPredict (hoja "PREDICTION" con precisión y exactitud) [C3 p.18].

**Salidas y dónde viven.**
- Tabla de métricas por modelo → `docs/analisis/metricas.md` (recomendación).
- Apartado "Evaluación" de la model card → `docs/modelos/`.
- Informe de análisis (M4RA2) → `docs/analisis/`.

**Hecho cuando.** Hay una tabla con las métricas de todos los modelos y baselines en validación y test; cada métrica tiene su interpretación; hay un apartado de sesgos; la paradoja de la exactitud se ha comprobado explícitamente.

**Errores frecuentes.** Dar solo accuracy; comparar métricas calculadas sobre conjuntos distintos; mirar el test varias veces; no decir el umbral; no comparar con baseline; interpretar un RMSE sin unidades.

**Estado actual.** Pendiente: no hay métricas de error de la previsión ni de clasificación. Ver [[07_Estado_actual]].

---

## Fase 9 · Simulador, viabilidad y mapa

**Objetivo.** Convertir los datos y los modelos en **respuestas de viabilidad**: filtros eliminatorios, scores por bloque,
score global 0-100, simulación económica y comparación de escenarios, con un mapa para verlo.

**Entradas.** Tabla maestra y features (fases 3 y 6), modelos (fase 7), parámetros del CPD y pesos.

**Pasos.**
1. **Parámetros del CPD.** Completar los parámetros del enunciado: superficie construida, número de salas técnicas, de racks y de servidores, potencia TI (MW), capacidad de almacenamiento (PB), capacidad de proceso (TFLOPS), tier, PUE, WUE, tipo de refrigeración, % renovable, producción propia (fotovoltaica y eólica), inversión, vida útil, personal, latencia, tráfico medio y pico (Gbps), número de operadores y litros/día para refrigeración. En el repo faltan los que se marcan en [[06_Checklist_entrega]].
2. **Filtros eliminatorios.** Zona inundable, Red Natura 2000, distancia a subestación para CPD > 20 MW, capacidad de acceso, latencia, estrés hídrico con refrigeración evaporativa, sismicidad, temperatura máxima, suelo industrial (según el README). Cada filtro con su umbral y su fuente en `config/settings.yaml`.
3. **Sub-scores** por bloque, normalizados 0 a 100 (min-max, [C4 p.23]) con dirección clara (más alto = mejor o peor).
4. **Pesos** del score global: sumar 1, guardarlos en configuración y documentar por qué.
5. **Simulación económica.** Energía, agua, OPEX, CO2, VAN, ROI y payback. Comprobar cada fórmula con un caso a mano.
6. **Escenarios.** Precio de la luz, sequía, tipo de refrigeración. Presentar la comparación de rankings.
7. **Análisis de sensibilidad.** Cambiar un parámetro cada vez y ver cuánto mueve el ranking (recomendación, no viene de clase).
8. **Mapa.** Provincias coloreadas por viabilidad o rentabilidad (frontend). Los datos sintéticos deben estar etiquetados como tales.

**Técnicas de clase.** Normalización de variables a escalas comparables [C4 p.23-24]; rankings como variable derivada [C4 p.10]; comparar escenarios es el "simulador que evalúa distintos escenarios" del objetivo 8 [E p.2].

**Salidas y dónde viven.**
- Código → `src/cpd/simulator.py`, `src/cpd/scoring.py`, `config/settings.yaml`.
- Mapa → `frontend/`.
- Simulador en la app → `app/streamlit_app.py`.

**Hecho cuando.** Cada filtro y peso tiene fuente y umbral documentados; las fórmulas económicas tienen tests (ya hay 19 tests en `tests/test_simulator.py`); un escenario de ejemplo produce un resultado reproducible; el mapa indica qué datos son sintéticos y cuáles reales.

**Errores frecuentes.** Parámetros inventados sin marcar; pesos que no suman 1; cambiar un umbral sin dejar rastro; comparar escenarios con datos de años distintos; mostrar un VAN sin decir la tasa de descuento.

**Estado actual.** Parcial: simulador, filtros y escenarios existen con tests; faltan varios parámetros del CPD, la app aún usa datos demo sintéticos y los umbrales están "a calibrar" (ver [[07_Estado_actual]]).

---

## Fase 10 · Dashboards y visualización

**Objetivo.** Presentar los resultados para la toma de decisiones: cuadro de mandos interactivo y el **informe de visualización** (M4RA4) y de cuadro de mandos (M4RA2).

**Entradas.** Resultados de las fases 4, 8 y 9.

**Pasos.**
1. Definir **para quién** es cada vista (dirección, técnico de datos, usuario del simulador) y qué decisión ayuda.
2. Elegir el **gráfico adecuado** a cada pregunta: línea para evolución, barra para ranking, dispersión para relación, mapa para territorio, box plot para atípicos [C2 p.6-13].
3. Poner **unidades, fuentes, fecha de datos y una frase de lectura** en cada gráfico.
4. Usar una **paleta** accesible (recomendación, no viene de clase): no depender solo del color.
5. Mostrar **incertidumbre** en las previsiones (intervalos) y **limitaciones** en el propio dashboard.
6. Pruebas en navegador (ver [[05_Reglas_de_codigo_y_git]]) y en el móvil.
7. Escribir el **informe de visualización**: para cada gráfico, qué pregunta responde y qué decisión apoya.

**Técnicas de clase.** Tipos de gráfico y uso recomendado [C2 p.6-13]; evitar falacias de correlación en las etiquetas [C2 p.18-21].

**Salidas y dónde viven.**
- Dashboards → `app/streamlit_app.py` (6 pestañas) y `frontend/` (mapa).
- Informe de visualización → `docs/visualizacion/` (a crear).
- Informe de cuadro de mandos → `docs/cuadro_mandos/` (a crear).

**Hecho cuando.** Cada gráfico del dashboard aparece en el informe con su pregunta; las previsiones muestran intervalo; las unidades están en todos los ejes; la app y el frontend arrancan desde cero siguiendo el manual.

**Errores frecuentes.** Muchos gráficos sin conclusión; ejes sin unidades; colores que no se distinguen; dashboards que dependen de datos no versionados; datos demo presentados como reales.

**Estado actual.** Parcial: existen dos interfaces (Streamlit y mapa web); faltan los informes escritos (ver [[07_Estado_actual]]).

---

## Fase 11 · Documentación, vídeo y entrega

**Objetivo.** Entregar todos los documentos y evidencias del enunciado, con la calidad de la rúbrica de nivel 6.

**Entradas.** Todo lo anterior.

**Pasos.**
1. **Documento de especificación** con: informe de origen de datos (M4RA1), informe de cuadro de mandos (M4RA2), informe de análisis (M4RA2), informe de visualización (M4RA4) y documentación del sistema de almacenamiento (M4RA3). Usar las plantillas de [[08_Plantillas]].
2. **Requisitos funcionales y no funcionales** descritos de forma exhaustiva (nivel 6 de la rúbrica de documentación).
3. **Código** con comentarios en las funciones principales (requisito explícito del enunciado) y en sistema de control de versiones. Ver [[05_Reglas_de_codigo_y_git]].
4. **Manual de instalación y despliegue** (M4RA1 y M4RA3): requisitos, pasos numerados, comandos exactos, prueba de humo y solución de problemas. Partir de la sección de instalación del README.
5. **Manual de usuario final** (M4RA2 y M4RA4): sin jerga, con capturas y un ejemplo completo.
6. **Vídeo** de funcionamiento con **varios casos de uso** (rúbrica de nivel 6): mínimo tres escenarios distintos (p. ej., municipio viable, no viable por agua, escenario de sequía). Guion previo en `docs/video/guion.md` (recomendación).
7. **Revisión final.** Pasar la checklist ([[06_Checklist_entrega]]) completa y dejar cada fila con estado y evidencia.
8. **Paquete de entrega** para Moodle: documentos en PDF, enlace al repositorio con la etiqueta de entrega, vídeo subido.

**Técnicas de clase.** Presentar avances y debatir ideas, debilidades y oportunidades [C4 p.30]; la rúbrica pide evidencias verificables.

**Salidas y dónde viven.**
- Documentos → `docs/` (y su PDF exportado para Moodle).
- Manuales → `docs/manuales/` (a crear).
- Vídeo → enlace en el README y en Moodle.

**Hecho cuando.** Todas las filas de la checklist con evidencia ✅ o con una limitación explicada; un tercero reproduce la instalación y ejecuta un caso de uso con el manual; el vídeo cubre los casos; el repositorio está limpio (sin secretos, sin datos grandes).

**Errores frecuentes.** Entregar el día 15 a las 23:00; el manual que funciona solo en tu equipo; vídeo sin audio ni explicación; documentos que contradicen el código; datos grandes o claves en el repositorio.

**Estado actual.** Pendiente en su mayoría (ver [[07_Estado_actual]] y plan semanal).

---

## Resumen de técnicas de clase por fase

| Fase | Técnicas de clase clave | Referencias |
|---|---|---|
| 0 | Equipo, roles, ramas, carpetas | C1 p.6-13 |
| 1 | Tipos de datos, adquisición, formato común | C1 p.3-5 |
| 2 | Box plot, histograma | C2 p.8, 10 |
| 3 | Min-max, z-score, log, winsorizing, polinómicas, one-hot, frequency, target, enums | C4 p.8-9, 20-26; C1 p.13 |
| 4 | Línea, barra, histograma, dispersión, box, heatmap, pie, pair plot, Pearson, Spearman, Kendall, causalidad | C2 p.6-24 |
| 5 | Relacional vs no relacional, grafos | C1 p.3; C2 examen p.4 |
| 6 | Lags, rolling, estacionariedad, diferencias, eventos, categóricas, semánticas | C4 p.5-28 |
| 7 | Causas de fallo de previsión, calidad de previsión | C3 p.3-6 |
| 8 | Métricas de regresión y clasificación, matriz, ROC-AUC, paradoja, sesgos, coste de error | C3 p.7-24 |
| 9 | Escalado y normalización para scores | C4 p.23-24 |
| 10 | Tipos de gráfico, falacias en la comunicación | C2 p.6-21 |
| 11 | Presentación y debate de ideas | C4 p.29-30 |
