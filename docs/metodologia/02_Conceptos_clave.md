---
tags: [metodologia, glosario, p3]
estado: borrador
actualizado: 2026-11-14
---

# 02 · Conceptos clave (glosario)

Volver a [[00_Indice]]. Cada término indica **dónde aparece** (enunciado = `E`, clase 02/10 = `C1`, clase 09/10 = `C2`,
clase 23/10 = `C3`, clase 13/11 = `C4`) y **por qué importa para P3**. Las páginas se refieren al PDF de cada clase.
Las definiciones están en lenguaje sencillo; cuando se dan por supuestas, es "definición general de la disciplina"
(recomendación, no viene de clase).

Índice por temas: [[#1. Proyecto y dominio CPD]] · [[#2. Datos y bases de datos]] · [[#3. ETL, calidad y limpieza]] ·
[[#4. Transformación y escalado]] · [[#5. Visualización y análisis exploratorio]] · [[#6. Correlación]] ·
[[#7. Series temporales y previsión]] · [[#8. Métricas]] · [[#9. Sesgos y errores de diseño]] ·
[[#10. Feature engineering]] · [[#11. Git y trabajo en equipo]] · [[#12. Términos de evaluación]] · [[#13. Términos propios del repositorio]]

---

## 1. Proyecto y dominio CPD

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **CPD / Data center** | Edificio con equipos informáticos (servidores, almacenamiento, redes) y las instalaciones que los mantienen en marcha (electricidad, refrigeración, seguridad). | E, portada | Es el objeto del análisis. |
| **Viabilidad** | Grado en que un municipio o zona reúne las condiciones para instalar y operar el CPD de forma económica, energética, ambiental y social. | E, contexto | Es el resultado que puntúa el sistema. |
| **Puntuación global de viabilidad** | Número único (en el repo, 0 a 100) que resume todos los bloques. | E, objetivo general | Entregable central del objetivo general. |
| **Previsiones a corto y medio plazo** | Estimaciones de valores futuros de una serie (demanda, precio, consumo…). | E, objetivo general | Va ligado a los objetivos 10 y a las preguntas P5. |
| **Potencia TI instalada (MW)** | Potencia de los equipos de TI (servidores, almacenamiento, red). Es la base de casi todos los cálculos. | E, infraestructura | Parámetro de entrada del simulador (`potencia_ti_mw`). |
| **Potencia máxima demandada** | Pico de potencia que pide el CPD de la red, teniendo en cuenta el PUE. | E, energía | Se usa para la conexión a red (filtro de distancia a subestación). |
| **Consumo anual previsto (MWh)** | Energía que consumirá el CPD en un año. | E, energía | Base del coste energético y del CO2. |
| **PUE (Power Usage Effectiveness)** | Energía total del CPD dividida entre la energía de los equipos TI. Cuanto más cerca de 1, más eficiente. | E, energía | Multiplica el consumo; en el repo se puede estimar por municipio (`pue_estimado`). |
| **WUE (Water Usage Effectiveness)** | Litros de agua por kWh de energía de TI. | E, agua | Parámetro `wue_l_kwh` del simulador. |
| **Tier I-IV (Uptime Institute)** | Nivel de redundancia y disponibilidad de un CPD (de I, sin redundancia, a IV, máxima). | E, infraestructura | Parámetro `tier` (en el repo solo informativo). |
| **Refrigeración: aire, evaporativa, adiabática, inmersión líquida** | Cuatro sistemas para evacuar el calor. Cada uno gasta distinta cantidad de agua y energía. | E, agua | Parámetro `tipo_refrigeracion`; también es filtro (estrés hídrico). |
| **Free cooling** | Refrigeración con aire exterior cuando la temperatura lo permite. Depende del clima. | E, climatología (un clima frío reduce costes de refrigeración) | Horas de free cooling por provincia (`horas_free_cooling`). |
| **TFLOPS** | Medida de capacidad de cálculo (billones de operaciones de coma flotante por segundo). | E, infraestructura | Variable del CPD sin parámetro en el repo. |
| **PB (petabyte)** | Medida de capacidad de almacenamiento (1 PB = 1 000 TB). | E, infraestructura | Variable del CPD sin parámetro en el repo. |
| **Gbps / tráfico medio y pico** | Velocidad de transmisión de datos (gigabits por segundo). | E, conectividad | Variable de conectividad sin parámetro en el repo. |
| **Latencia máxima admisible (RTT)** | Tiempo de ida y vuelta de un paquete de datos. Limita la distancia al cliente. | E, conectividad; repo `latencia_rtt_ms` | Filtro de latencia del repo. |
| **Operadores requeridos** | Número de operadores de telecomunicaciones necesarios para la conectividad. | E, conectividad | Variable sin parámetro en el repo. |
| **Inversión inicial (CAPEX)** | Coste de construir y equipar el CPD (en el repo, `inversion_eur`). | E, económico | Entrada del VAN, ROI y payback. |
| **Costes operativos (OPEX)** | Gasto recurrente de explotación (energía, agua, personal, mantenimiento). | E, económico | `opex_eur` y `desglose_opex`. |
| **Vida útil prevista** | Años de análisis financiero (en el repo, `vida_util_anos`). | E, económico | Horizonte del VAN. |
| **VAN (Valor Actual Neto)** | Suma de los flujos de caja futuros descontados, menos la inversión. Positivo = rentable a la tasa usada. | E (retorno de inversión), repo | Responde P7. |
| **ROI (retorno sobre la inversión)** | Beneficio dividido entre la inversión. | E (retorno de inversión), repo | Responde P7. |
| **Payback (periodo de recuperación)** | Años que tarda en recuperarse la inversión. | Repo (`payback_anos`) | Complemento de P7. |
| **Estrés hídrico** | Relación entre demanda y disponibilidad de agua. Alto = riesgo. | E, agua; WRI | Riesgo hídrico (P4) y filtro. |
| **Sequías históricas** | Periodos de déficit de lluvia pasados. | E, agua | Se mide con índices. En el repo, suma móvil de 12 meses de precipitación y balance (`indice_sequia_12m` en `agua.py`); no es un SPI oficial. |
| **Embalse** | Depósito de agua superficial. Su reserva es un indicador de disponibilidad. | E, agua; MITECO | Variable "embalses cercanos". |
| **Calidad del agua** | Parámetros físico-químicos del agua de consumo o de cuerpos de agua. | E, agua | Variable del brief; sin fuente integrada en el repo. |
| **Red Natura 2000** | Red europea de espacios naturales protegidos. | E, suelo/ambiente; repo | Filtro eliminatorio del repo. |
| **Riesgo sísmico / riesgo de inundación** | Probabilidad de daño por terremoto o por inundación en una zona. | E, suelo disponible | Filtros del repo: zona inundable y sismicidad ≥ 0,16 g (según el README del proyecto; fuente de la sismicidad a verificar). |
| **Calificación urbanística** | Uso del suelo permitido por el planeamiento municipal (industrial, residencial…). | E, suelo | Requisito para poder construir. |
| **Suelo industrial: precio y disponibilidad de parcelas** | Coste y oferta de suelo para uso industrial. | E, suelo | Variables de coste y de viabilidad. |
| **Puntos neutros de Internet (IXP)** | Puntos donde operadores y proveedores intercambian tráfico de Internet. | E, telecomunicaciones; PeeringDB | Cercanía a un IXP mejora la latencia. |
| **Troncales de comunicaciones / nodos principales** | Grandes enlaces de fibra y los nodos que los concentran. | E, telecomunicaciones | Distancia a nodos principales como variable. |
| **Cobertura de fibra óptica / 5G** | Porcentaje de población o territorio con esa conectividad. | E, telecomunicaciones | Variables del entorno territorial. |
| **Huella de carbono / emisiones indirectas** | CO2 emitido por la energía que compra el CPD (alcance 2) y por otras fuentes (alcance 3). | E, impacto ambiental | En el repo: `co2_t` con % renovable. |
| **Ocupación del suelo** | Superficie de terreno que ocupa el CPD. | E, impacto ambiental | Relación con superficie construida. |
| **Impacto socioeconómico (empleo, PIB, inversión inducida, atracción empresarial)** | Efectos del CPD sobre la economía local. | E, impacto socioeconómico | Variables del brief; sin modelo en el repo. |

## 2. Datos y bases de datos

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Datos relacionales** | Tablas con filas y columnas relacionadas por claves. Se consultan con SQL. | C1, p. 3 | Base del almacén DuckDB y del esquema en estrella. |
| **Datos no relacionales (NoSQL)** | Almacenes sin tablas fijas (documentos, clave-valor, grafos…). | C1, p. 3; C2 examen pregunta 3 | Hay que saber justificar por qué P3 usa un modelo relacional. |
| **Datos tabulares / no tabulares** | Tabulares = filas y columnas. No tabulares = imágenes, audio, vídeo, proteínas… | C1, p. 3 | Las fuentes de P3 son casi todas tabulares (CSV, XLSX), con JSON y ficheros Access. |
| **Datos cualitativos / cuantitativos** | Cualitativos = categorías (sexo, provincia). Cuantitativos = números medibles (MWh, €). | C1, p. 4 | Determina qué gráfico y qué codificación usar. |
| **Adquisición de datos (open data)** | Obtener datos de portales públicos o de APIs. | C1, p. 5 ("Barcelona Open data") | Es la base de la ingesta de P3. |
| **Datos propios (encuesta, fotos, registros)** | Datos que genera el equipo. | C1, p. 5 | El enunciado no los pide; si se usan, documentar cómo se obtuvieron. |
| **Formato común ("common ground")** | Llevar todas las fuentes a la misma forma (mismas claves, mismas unidades, mismo tipo). | C1, p. 5 | Es el paso de ETL "T" y la tabla maestra. |
| **Data Lake (capa raw)** | Almacén de datos en su forma original, sin transformar. | E (objetivo 4); repo `data/raw/` | Regla: la capa raw no se modifica nunca ([[04_Reglas_de_datos]]). |
| **Data Warehouse (almacén de datos)** | Base de datos organizada para analizar y consultar (histórico, con dimensiones y hechos). | E (objetivo 4); repo `data/almacen/p3_cpd.duckdb` | Lo que alimenta dashboards y modelos. |
| **Esquema en estrella (star schema)** | Una tabla de hechos (medidas) rodeada de tablas de dimensiones (quién, dónde, cuándo). | Repo: `dw.dim_provincia`, `dw.dim_tiempo`, `dw.dim_fuente`, `dw.fact_provincia_mes` | Lo pide la fase 5 de [[03_Flujo_de_trabajo]]. |
| **Tabla de hechos / tabla de dimensiones** | Hechos = medidas numéricas por evento o periodo. Dimensiones = descripción (provincia, mes, fuente). | Repo | Ver arriba. |
| **Clave primaria / clave foránea** | Identificador único de una fila / columna que apunta a otra tabla. | C1 (modelización de datos) | Código INE de provincia/municipio como clave de unión. |
| **Granularidad** | Nivel de detalle de una tabla (una fila por provincia y mes, por municipio, por día…). | C1; recomendación (no viene de clase) | Hay que escribirla en cada tabla. P3: panel provincia × mes. |
| **Diccionario de datos** | Descripción de cada columna: nombre, significado, unidad, fuente, frecuencia. | Repo `data/curated/diccionario_*.csv`; recomendación | Obligatorio para el informe de origen de datos. |
| **Metadatos / registro de cargas** | Información sobre cada carga: fuente, URL, fecha, tamaño, hash. | Repo `data/raw/_registro_descargas.csv`, `meta.carga` | Trazabilidad (regla de datos). |
| **Hash SHA-256** | Huella digital de un fichero. Sirve para comprobar que no ha cambiado. | Repo `docs/datos/manifiesto_raw_*.csv` | Verificación de la Release de datos. |
| **Enumeración (enum)** | Lista cerrada de valores válidos (p. ej., tipos de refrigeración). | C1, p. 13 ("remember the enums and you will get extra points") | No hay `enum` en `src/`, `app/` ni `tests/`: pendiente. |
| **Grafo, nodo, arista, influencer** | Un grafo conecta nodos (entidades) con aristas (relaciones). Un influencer es un nodo muy conectado o central. | C1, examen pregunta 4 | Concepto de teoría de grafos; no es requisito de P3. |
| **API** | Interfaz para pedir datos a un servicio por código (HTTP). | Repo (`src/cpd/fuentes`) | Forma de ingesta programática. |

## 3. ETL, calidad y limpieza

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **ETL (Extraer, Transformar, Cargar)** | Proceso de sacar datos de las fuentes, transformarlos y guardarlos en el destino. | E, objetivo 2 | Fases 1 a 3 de [[03_Flujo_de_trabajo]]. |
| **Ingesta** | Descarga de los datos de la fuente a la capa raw. | Repo `src/ingesta/`, `src/cpd/fuentes/` | Fase 1. |
| **Tipos de datos** | Qué es cada columna (texto, entero, decimal, fecha). | Recomendación (no viene de clase) | Errores típicos: códigos INE leídos como número (pierden ceros). |
| **Duplicados** | Filas repetidas o claves repetidas. | Recomendación | Comprobar clave única por provincia y mes. |
| **Valores ausentes (missing values, NaN)** | Celdas sin dato. Hay que decidir si se rellenan, se marcan o se eliminan. | Repo `curado.py` (NaN donde la fuente no tiene dato); recomendación | Regla: no inventar valores ([[04_Reglas_de_datos]]). |
| **Valores atípicos (outliers)** | Valores muy alejados del resto. Pueden ser error o un caso real. | C2, p. 10 (box plot); C4, p. 8 (winsorizing) | Hay que detectarlos, decidir y documentar. |
| **Secreto estadístico (`<5`)** | El INE/SEPE oculta cifras pequeñas. Hay que tratarlas como dato ausente o como rango. | Repo `docs/datos/README.md` | Aviso de transformación SEPE. |
| **Unidades** | Medida de cada valor (MWh, mm, €/MWh). Va en el nombre de la columna. | Regla de datos | Evita errores de escala. |
| **Validación de datos** | Comprobar que los datos cumplen reglas (rangos, claves, totales). | E, objetivo 3 | Tests de datos (`tests/test_datos_nuevos.py`). |
| **Mojibake** | Texto con caracteres rotos (p. ej. "AndalucÃ­a") por leer con una codificación equivocada. | Repo `agua.py` | Leer siempre con la codificación de la fuente. |

## 4. Transformación y escalado

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Escalado (scaling)** | Cambiar la escala de una variable para que sea comparable con otras. | C4, p. 8 y 23 | Necesario cuando las variables tienen unidades distintas (€, %, MWh). |
| **Normalización (min-max)** | Llevar los valores a un rango, normalmente 0 a 1: `(x − min) / (max − min)`. | C4, p. 23 ("MAX-MIN") | El repo la usa para los sub-scores (`normalizar_min_max`). |
| **Estandarización (z-score)** | Restar la media y dividir por la desviación típica: `(x − media) / σ`. | C4, p. 23 ("Z-SCORE") | Útil para modelos sensibles a la escala. |
| **"Sin perder datos" en el escalado** | Escalar sin borrar ni sobrescribir la columna original, y ajustar el escalador solo con datos de entrenamiento. | Enunciado del encargo; recomendación (no viene de clase) | Ver [[04_Reglas_de_datos]], regla R-7. |
| **Transformación logarítmica** | Aplicar un logaritmo para comprimir valores muy grandes y acercar una distribución sesgada a una forma más simétrica. `log1p(x) = log(1 + x)` evita el log de 0. | C4, p. 25-26 (ejemplo `np.log1p`) | Para variables de consumo o de población muy asimétricas. |
| **Winsorizing (winsorización)** | Recortar los valores extremos a un percentil (p. ej. 1 % y 99 %) en lugar de quitarlos. | C4, p. 8 | Alternativa a eliminar outliers que conserva las filas. |
| **Transformaciones polinómicas** | Añadir potencias de una variable (x², x³) para capturar relaciones no lineales. | C4, p. 8 | Opción para modelos lineales. |
| **Codificación one-hot** | Convertir una categoría en columnas binarias (0/1), una por valor. Ej.: `["barcelona","sabadell","terrassa"]` → `[[1,0,0],[0,1,0],[0,0,1]]`. | C4, p. 9 y 20 | Para categorías pocas (CCAA, tipo de refrigeración). |
| **Codificación por frecuencia (frequency encoding)** | Sustituir cada categoría por la proporción de filas que la tiene. Ej.: `[0.5, 0.25, 0.25]`. | C4, p. 21 | Para muchas categorías (municipios). |
| **Codificación por objetivo (target encoding)** | Sustituir cada categoría por la media de la variable objetivo en esa categoría. Riesgo de fuga si no se calcula bien. | C4, p. 9 | Requiere cuidado: solo con datos de entrenamiento. |
| **Embeddings** | Vectores densos aprendidos para representar categorías. El propio material lo llama "super-ultra-advanced". | C4, p. 9 | Opcional; no prioritario para P3. |
| **Variables derivadas o semánticas** | Variables creadas con conocimiento del dominio (zona climática, región, ranking, extracciones de texto). | C4, p. 10 y 27-28 | Ejemplo de clase: Pokémon. Para P3: zona climática, ámbito hidrográfico, ranking. |

## 5. Visualización y análisis exploratorio

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **EDA (análisis exploratorio de datos)** | Mirar los datos con gráficos y estadísticas antes de modelar. | E, objetivo 5; C2 | Fase 4 de [[03_Flujo_de_trabajo]]. |
| **Gráfico de líneas (line plot)** | Para evolución temporal y tendencias. | C2, p. 6 | Series de demanda, precio, reservas. |
| **Gráfico de barras (bar plot)** | Para comparar categorías. | C2, p. 7 | Ranking de provincias. |
| **Histograma** | Distribución de una variable numérica en intervalos (bins). | C2, p. 8 | Primer vistazo a cada variable (detectar asimetría). |
| **Diagrama de dispersión (scatter plot)** | Un punto por observación, con dos variables en los ejes. | C2, p. 9 y examen | Ver correlación entre dos variables. |
| **Box plot (diagrama de caja)** | Muestra mediana, cuartiles y outliers. | C2, p. 10 | Detección de outliers. |
| **Mediana y cuartiles** | Mediana = valor central. Cuartiles = valores que dejan el 25 % y el 75 % por debajo. | C2, p. 10 | Resúmenes robustos frente a outliers. |
| **Mapa de calor (heatmap)** | Matriz de colores. Se usa para matrices de correlación. | C2, p. 11 | Matriz de correlación del EDA. |
| **Gráfico de sectores (pie chart)** | Reparto de un total entre partes. | C2, p. 12 | Uso limitado; preferir barras. |
| **Pair plot** | Matriz de gráficos de dispersión entre todas las variables numéricas (con histogramas en la diagonal). | C2, p. 13 | Exploración rápida de relaciones. |
| **Cuadro de mandos (dashboard)** | Panel con indicadores clave, filtros y gráficos para decidir. | E, objetivo 9 y entregable | Entregable de M4RA2. |
| **Visualización honesta** | Ejes que no engañan, escalas explicadas, sin efectos que exageren. | Recomendación (no viene de clase) | Parte de la rúbrica (informe de visualización). |

## 6. Correlación

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Correlación** | Medida de cuánto cambian juntas dos variables. Va de −1 a 1. | C2, p. 15 | Relacionar variables territoriales con la viabilidad. |
| **Correlación +1 / −1** | +1 = relación directa perfecta. −1 = relación inversa perfecta. | C2, p. 15 | Interpretación del coeficiente. |
| **Correlación 0** | Sin relación lineal. Ojo: puede existir una relación no lineal. | C2, p. 15 ("0 non linear relationship") | No concluir "no hay relación" con un 0. |
| **Pearson** | Mide relación **lineal**. Sensible a outliers. Para variables numéricas continuas. | C2, p. 23 | Correlación por defecto, pero frágil con outliers. |
| **Spearman** | Mide relación **monótona** (siempre sube o siempre baja, no necesariamente en línea recta). Se basa en rangos. Robusto a outliers. | C2, p. 23 | Opción robusta. |
| **Kendall** | Basado en pares concordantes y discordantes. Útil en datasets pequeños. | C2, p. 23-24 | Opción para muestras pequeñas. |
| **Correlación no implica causalidad** | Que dos variables se muevan juntas no significa que una cause la otra. | C2, p. 18-21 ("BE CAREFUL WITH FALACIES") | Muy importante en la redacción de conclusiones del informe. |
| **Falacia** | Razonamiento que parece válido pero no lo es. Aquí: confundir correlación con causa. | C2, p. 18-21 | Ver [[#9. Sesgos y errores de diseño]]. |
| **Multicolinealidad** | Dos o más variables explicativas muy correlacionadas entre sí. Confunde a algunos modelos. | Recomendación (no viene de clase); la matriz de correlación de C2 la hace visible | Revisar antes de modelar. |

## 7. Series temporales y previsión

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Serie temporal** | Valores de una variable ordenados en el tiempo. | E, objetivo 10; C3 | Demanda eléctrica mensual, reservas, precio. |
| **Previsión (forecasting)** | Estimar valores futuros de una serie a partir de su historia y de otras variables. | E; C3 p. 1-4 | Objetivo 10 y preguntas P5. |
| **Horizonte de previsión** | Hasta qué momento futuro se predice (en P3: hasta 120 meses). | C3, p. 4 ("mala elección de horizonte") | Un horizonte mal elegido hace fracasar la previsión. |
| **Ventana temporal** | Cuántos datos pasados se usan para entrenar y para evaluar. | C3, p. 4 ("ventana temporal incorrecta") | Ver validación temporal. |
| **Estacionalidad** | Patrón que se repite con un periodo fijo (mes, semana, año). | C3, p. 4 ("mala estacionalidad"); C4, p. 16 | La demanda eléctrica tiene estacionalidad anual clara. |
| **Tendencia** | Dirección de largo plazo de la serie (subida, bajada). | C4, p. 16 ("las tendencias no se construyen") | El baseline del repo es tendencia lineal + estacionalidad. |
| **Estacionariedad (stationarity)** | Serie cuya media y varianza no cambian con el tiempo. | C4, p. 16 ("la estacionariedad no se encuentra en la naturaleza") | Muchas series reales no lo son; hay que transformarlas. |
| **Lag (retardo)** | Valor de la misma variable en un periodo anterior (t−1, t−12). Es la feature más importante en previsión. | C4, p. 12-14 | Feature de lags para modelos ML (pendiente en el repo). |
| **Ventana móvil (rolling window)** | Estadístico (media, máximo, mínimo, desviación) calculado sobre los últimos k periodos. Suaviza ruido. | C4, p. 15 | Ya existe una suma móvil de 12 meses en `agua.py` (sequía). |
| **Diferencias (differencing)** | Restar el valor anterior al actual: `y_t − y_{t−1}`. Ayuda a quitar tendencia. | C4, p. 17 | Transformación para estacionariedad. |
| **Fuga de información (data leakage)** | Que el modelo vea, al entrenar, información que no tendría en el momento de predecir (p. ej., el futuro o el propio objetivo). | C3, p. 4 ("fuga de información") | Error grave. Ver [[04_Reglas_de_datos]]. |
| **Validación temporal (time-aware split)** | Entrenar con el pasado y validar con el futuro, nunca al revés ni aleatoriamente. | C3, p. 4; recomendación (no viene de clase) para la técnica concreta | Regla de datos R-6. |
| **Backtesting** | Simular cómo habría funcionado el modelo en fechas pasadas, avanzando la ventana. | Recomendación (no viene de clase) | Forma recomendada de evaluar la previsión. |
| **Variables externas** | Variables que no son la serie pero ayudan a predecirla (clima, precio, población). | C3, p. 4 ("variables externas mal integradas") | Integrarlas sin fuga. |
| **Eventos o efectos puntuales** | Hechos que alteran la serie una vez (DANA, Black Friday). | C4, p. 18 | Marcar eventos como variable binaria, si se conocen. |

## 8. Métricas

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Métricas de regresión** | Miden la distancia entre el valor predicho y el real (número real). | C3, p. 9-11 ("we measure the distance") | Para previsión numérica (demanda, precio). |
| **Métricas de clasificación** | Miden si la clase predicha es la correcta. | C3, p. 13 | Para clasificar zonas en "Viable / Con condiciones / No viable" si se modela. |
| **Accuracy (exactitud)** | Porcentaje de aciertos sobre el total. | C3, p. 14 | Engaña con clases desbalanceadas (ver paradoja). |
| **Precision (precisión)** | De lo que predigo positivo, qué porcentaje lo es. `TP / (TP + FP)`. | C3, p. 14 y 23 | Importa cuando un falso positivo es caro. |
| **Recall (sensibilidad, TPR)** | De los positivos reales, cuántos encuentro. `TP / (TP + FN)`. | C3, p. 14, 19 | Importa cuando un falso negativo es caro. |
| **F-Score (F1)** | Media armónica de precision y recall. | C3, p. 14 | Equilibrio entre ambas. |
| **ROC-AUC** | Área bajo la curva ROC (TPR frente a FPR para cada umbral). Mide la capacidad de separar clases. | C3, p. 14 y 19 | "La única que siempre hay que mirar" (según la clase). También sirve para elegir umbral. |
| **Log-Loss (pérdida logarítmica)** | Penaliza las probabilidades mal calibradas. | C3, p. 14 | Si el modelo da probabilidades. |
| **Matriz de confusión** | Tabla que cruza valor real y valor predicho: TP, TN, FP, FN. | C3, p. 15-17 | Base de todas las métricas de clasificación. |
| **TP / TN / FP / FN** | Verdadero positivo, verdadero negativo, falso positivo (error tipo I), falso negativo (error tipo II). | C3, p. 15-17 y 23 | Ver ejemplo del test de embarazo (p. 16). |
| **Error tipo I / tipo II** | Tipo I = falso positivo ("dices que está embarazada y no lo está"). Tipo II = falso negativo. | C3, p. 16 | Decidir cuál es más grave en cada caso. |
| **FPR (tasa de falsos positivos)** | `FP / (FP + TN)`. | C3, p. 19 | Eje X de la curva ROC. |
| **Umbral (threshold)** | Valor de probabilidad a partir del cual se clasifica como positivo. | C3, p. 19 | Cambiarlo cambia precision y recall. |
| **Paradoja de la exactitud (accuracy paradox)** | Un modelo "tonto" que siempre predice la clase mayoritaria puede tener un accuracy muy alto. Ejemplo de clase: detector de spam con 99 % de acierto en 100 correos donde casi todos son legítimos. | C3, p. 23 | No aprobar un modelo solo por accuracy. |
| **Coste de un error** | No todos los errores pesan igual. Un 5-0 contra 3-0 no es un fallo grave; 1-7 sí. | C3, p. 8 | Elegir métrica según el coste de equivocarse. |
| **Calidad de una previsión** | Cómo de bien predice un modelo, comparado con algo simple. | C3, p. 5-6 | Siempre comparar con un baseline. |

## 9. Sesgos y errores de diseño

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Sesgo (bias) de datos** | Los datos no representan bien la realidad que se quiere modelar. | C3, p. 22-24 | Ej.: datos solo de provincias grandes, o solo de fuentes con cobertura desigual. |
| **Tipos de sesgo** | Hay varios tipos (muestreo, selección, histórico…). La clase deja su comprobación para hacer en código. | C3, p. 24 ("Let's try to code") | Hay que comprobarlos con código y documentarlos. |
| **"Mala preparación de datos"** | Causa de fallo de previsión: datos sucios o mal transformados. | C3, p. 4 | Ver fases 2 y 3. |
| **Variables externas mal integradas** | Causa de fallo: se añaden variables sin alinear fechas o claves. | C3, p. 4 | Alinear periodos y claves. |
| **Métricas mal interpretadas** | Causa de fallo: leer una métrica sin mirar su contexto. | C3, p. 4 | Documentar qué mide cada métrica. |
| **Correlación espuria** | Relación aparente sin causa real. | C2, p. 16-21 | Ver correlación no implica causalidad. |

## 10. Feature engineering

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Feature engineering (ingeniería de variables)** | Conjunto de acciones que transforman las variables para que el modelo aprenda mejor. | C4, p. 5 | Fase 6 de [[03_Flujo_de_trabajo]]. |
| **Feature (variable de entrada)** | Columna que el modelo usa para predecir. | C4 | Cada variable del panel es candidata. |
| **Los modelos no piensan** | Un modelo solo encuentra lo que los datos y las features le dejan ver. Las tendencias y relaciones no aparecen solas. | C4, p. 5 | Justifica el esfuerzo de features. |
| **Features semánticas (derivadas del dominio)** | Variables creadas con conocimiento experto. | C4, p. 10, 27-28 | Ver arriba. |

## 11. Git y trabajo en equipo

| Término | Definición sencilla | Dónde aparece | Por qué importa para P3 |
|---|---|---|---|
| **Git** | Sistema de control de versiones: guarda el historial de cambios. | C1, p. 6-11; E ("sistema de control de versiones") | Requisito de la entrega. |
| **Repositorio (repo)** | Carpeta del proyecto con su historial de Git. | C1 | `p3-cpd`. |
| **Rama (branch)** | Línea de trabajo separada para hacer cambios sin tocar la principal. | C1, p. 10-11 | Una rama por tarea. |
| **Rama de funcionalidad (feature/...)** | Convención de nombre para una nueva funcionalidad. | C1, p. 10-11 (`feature/data-cleaners`, `feature/data-visualizers`, `feature/data-filters`, `feature/master-flux`) | Ver [[05_Reglas_de_codigo_y_git]]. |
| **git fetch / pull --rebase / checkout -b** | Traer los cambios remotos, reaplicar tus cambios encima y crear una rama nueva. | C1, p. 11 | Flujo de la clase. |
| **Rama develop** | Rama de integración que usa la clase. | C1, p. 11 ("git checkout develop") | El repo usa `main`. Ver [[05_Reglas_de_codigo_y_git]] (decisión pendiente). |
| **Commit** | Foto del estado de los ficheros con un mensaje. | Recomendación | Mensajes claros, en español, estilo convencional. |
| **Pull request (PR)** | Propuesta para integrar una rama en otra, revisada por un compañero. | Recomendación (no viene de clase) | Revisión por pares antes de integrar. |
| **Carpetas del proyecto: `data/`, `utils/`, `config/`** | Qué va en cada carpeta: `data/` solo datos usados, `utils/` funciones directas, `config/` configuración global. | C1, p. 12-13 | El repo tiene `src/cpd`, `config/`, `data/`; no hay `utils/` (ver [[05_Reglas_de_codigo_y_git]]). |
| **Roles de equipo (Dirección, Data Cleaners, Data Visualization, Data Filters, R&D)** | Grupos de trabajo propuestos en clase. | C1, p. 9-10 | Asignar responsables en la checklist. |
| **Flujo maestro ("main script flux master")** | Script principal que une las partes. | C1, p. 10 (grupo 1) | Es el punto de entrada del sistema (`scripts/run_app.ps1` o similar). |

## 12. Términos de evaluación

| Término | Definición sencilla | Dónde aparece |
|---|---|---|
| **RA (resultado de aprendizaje)** | Competencia que se evalúa. Códigos: M4RA1 a M4RA4, M1RA5, M1RA6, M2RA3, M2RA4, M2RA5. | E, tabla de entregables y rúbrica |
| **Rúbrica** | Tabla con niveles de desempeño para cada evidencia. | E, "Sistema de Evaluación a través de Rúbricas" |
| **Escala 1-6** | 1 No alcanzado, 2 Insuficiente, 3 Suficiente, 4 Bien, 5 Notable, 6 Excelente. | E |
| **Evidencia** | Lo que se entrega para demostrar un RA (documento, código, vídeo, manual). | E |
| **Manual de instalación y despliegue** | Pasos para dejar el sistema funcionando en otro equipo. | E |
| **Manual de usuario final** | Guía para quien usa el sistema, sin conocimientos técnicos. | E |
| **Vídeo de funcionamiento** | Grabación del sistema en uso con varios casos de prueba. | E |
| **AutoPredict** | Ejercicio de clase (23/10): cada alumno elige un Pokémon en secreto, se anota la predicción y se calcula la precisión y la exactitud. No es entregable. | C3, p. 18 |
| **Examen de clase (09/10)** | Cuatro preguntas: código Python con CSV y medias, gráfico de correlación, bases de datos relacionales frente a no relacionales, y grafos. No es entregable de P3. | C2, p. 3-4 |

## 13. Términos propios del repositorio

| Término | Definición sencilla | Dónde está |
|---|---|---|
| **Panel provincia × mes** | Tabla con una fila por provincia y mes (52 × 142 según el encargo) y 51 columnas. | `data/curated/panel_provincia_mes.csv` |
| **provincias_actual** | Tabla con una fila por provincia (52) con el último dato y campos de tiempo real. | `data/curated/provincias_actual.csv` |
| **Filtro eliminatorio** | Condición que, si se cumple, pone la zona en "No viable" sin importar el resto. | `src/cpd/scoring.py` (`aplicar_filtros`) |
| **Sub-score** | Puntuación de un bloque (energía, agua, riesgo…) entre 0 y 100. | `scoring.calcular_sub_scores` |
| **Escenario** | Conjunto de supuestos (precio de la luz, sequía, refrigeración) para comparar resultados. | `scoring.preparar_escenario` |
| **Baseline** | Modelo simple de referencia. Todo modelo más complejo debe superarlo. | `src/cpd/forecast.py` (tendencia + estacionalidad) |
| **Capa raw / curated / clean** | Datos tal cual (raw), datos limpios (clean) y tabla lista para usar (curated). | `data/raw`, `data/clean`, `data/curated` |
| **DuckDB** | Base de datos local tipo archivo, de análisis. | `data/almacen/p3_cpd.duckdb` |
| **CCAA / ámbito hidrográfico** | Comunidad autónoma / cuenca de río, usados como claves territoriales. | Panel (`ccaa`, `ambito_hidrografico`) |
| **Free cooling** | Ver sección 1. | `horas_free_cooling` |

## 14. Ingeniería de datos (clase 27/11/2026)

Fuente: [[Clase_2026-11-27_Data_Engineering]] (C5).

| Término | Definición sencilla | Dónde está |
|---|---|---|
| **Ingesta batch / continua** | Batch: se descarga por bloques cada cierto tiempo (cada noche, cada 6 h). Continua: cada dato se sube nada más llegar. | `python -m cpd.fuentes.actualizar` (batch) |
| **Polling / streaming** | Polling: el sistema pregunta cada X segundos si hay algo nuevo. Streaming: la fuente envía el dato cuando llega (Kafka, WebSockets). | Polling en `frontend/src/live/usePolling.ts` |
| **ETL / ELT** | Extraer, transformar y cargar (ETL) o extraer, cargar y transformar dentro de la base (ELT). | ETL en `cpd.fuentes`; ELT con SQL en `cpd.almacen` |
| **Paginación** | La API devuelve los datos por trozos (offset, página o un cursor que indica dónde sigue). | No la usa ninguna API del proyecto |
| **Batching** | Pedir muchos elementos en una sola petición en vez de una petición por elemento. | Open-Meteo: 52 provincias por petición |
| **I/O-bound / CPU-bound** | I/O-bound: el tiempo se va esperando a la red o al disco (se acelera con hilos). CPU-bound: se va calculando (se acelera con procesos). | `http.en_paralelo` (hilos) |
| **Rate limiting (HTTP 429)** | Límite de peticiones por minuto de una API; si se pasa, responde 429 «Too Many Requests». | `http.PAUSA_MINIMA_SEGUNDOS`, `ESPERA_429_SEGUNDOS` |
| **Backoff exponencial y jitter** | Esperar cada vez el doble antes de reintentar (2, 4, 8 s) más un poco al azar para no reintentar todos a la vez. | `http.espera_backoff` |
| **Caché y TTL** | Guardar respuestas para no repetir peticiones. El TTL (*time to live*) es cuánto tiempo sigue valiendo la copia. | `http.leer_cache_json(ruta, ttl_horas)` |
| **Parquet (formato columnar)** | Fichero binario, comprimido y con tipos que guarda cada columna junta: leer una columna no obliga a leer las demás. | `data/curated/**/*.parquet` |
| **OLTP / OLAP** | OLTP: muchas operaciones pequeñas (altas, pedidos). OLAP: consultas que recorren muchas filas (medias, agrupaciones). P3 es OLAP. | DuckDB (`data/almacen/p3_cpd.duckdb`) |
| **ORM** | Librería (p. ej. SQLAlchemy) que traduce tablas a objetos de Python. Útil con datos transaccionales; P3 no los tiene. | — |
| **Bronze / Silver / Gold** | Capas del lago de datos: Bronze = lo que llegó (raw); Silver = limpio y tipado; Gold = agregado y listo para usar. | `src/cpd/capas.py` (`CAPAS`) |
| **Watermark** | Marca del último periodo cargado de una tabla. Sirve para pedir solo lo nuevo y saber si los datos están al día. | `gold.watermark`, `data/almacen/historial_watermarks.csv` |
| **At least once / exactly once** | Garantía de que cada dato se procesa al menos una vez (puede repetirse) o exactamente una vez (sin duplicados). | Escritura temporal y renombrado (idempotente) |
| **Capa Gold del dashboard** | Tablas ya agregadas que el dashboard solo lee: el producto no hace ingeniería de datos. | Esquema `gold` del almacén; `frontend/src/components/CatalogoDatos.tsx` (panel «Datos» del mapa, `#/datos`) |
