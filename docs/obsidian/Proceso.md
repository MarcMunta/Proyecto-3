---
tags: [clase, proyecto-3, proceso]
actualizado: 2026-11-17
---

# Proceso paso a paso

Volver a [[00 Índice]]. Registro en orden de lo que se ha hecho, por qué y qué ha salido. Es la base del documento de entrega con todos los pasos.

## Hasta el 14/11/2026 · Punto de partida (auditoría)

- Ingesta amplia y documentada, almacén DuckDB, simulador con tests y dos interfaces (Streamlit y mapa web).
- Faltaban: análisis exploratorio, correlaciones, modelos de ML evaluados, informes, vídeo y manuales.

## 17/11/2026 · Revisión del mapa y calidad de datos

1. Revisión del frontend: etiqueta «No viable», aviso del rango de VAN, latencia, recuadro de Canarias (PR #1).
2. **Hallazgo de datos:** REData publicó la demanda de jul-ago 2026 sin el saldo de intercambios (Madrid 123 GWh, Cantabria negativa). Se filtra en el curado con registro en `calidad_demanda_ccaa.csv` (PR #2).

## 17/11/2026 · EDA y primeros modelos (PR #3)

3. EDA con histogramas, box plots, series, dispersión, Pearson, Spearman y pair plot (`docs/analisis/eda_panel.md`).
4. Demanda por comunidad a 1 y 12 meses (baselines, Ridge, gradient boosting, validación temporal) y `prob_cpd` por provincia (la logística con la población gana: ROC-AUC 0,88).

## 17/11/2026 · Precio de la luz y previsión a 1 año (PR #4 y #5)

5. Modelo del precio de la luz y sensibilidad del VAN al precio.
6. Previsión a 1 año con backtesting de 24 orígenes, ETS, ML y combinación; gas de MIBGAS como fuente nueva.
7. **Decisión D7:** el simulador mantiene la media de 12 meses como precio (ver [[Decisiones]]).

## 17/11/2026 · Modelos de largo plazo y requisito de acierto (PR #6)

8. Demanda nacional a 10 años (backtesting plurianual, acierto 97,3 %) y reservas de agua a 1 año (85,3-86,7 %).
9. **Requisito D8:** 85 % ≤ acierto < 99,9 %. Control automático en cada ejecución.
10. El precio de la luz no llega (59-62 %): se deja orientativo, con la explicación con cifras en el informe.
11. Gráficos rehechos: mapa interactivo (línea vertical, recuadro, tabla «Ver los datos», colores comprobados para daltonismo) y figuras del informe sin doble eje.
12. Icono de «No viable» como «sin cobertura» (barras vacías y distintivo rojo con ×).
13. Temperatura por provincia a 1 año (93,8 / 92,8 %): es la variable del PUE.
14. % renovable por comunidad: mes a mes 84,3 % (orientativo), media de 12 meses 88,7 / 93,6 % (cumple).

## 17/11/2026 · Aragón y datos reales nuevos

15. Comprobación externa: Aragón concentra unos 70.000 M€ de inversión anunciada en CPD (noticias). Con los datos de entonces Aragón salía mal (Zaragoza 46.ª en el score) porque el simulador solo distinguía por el clima.
16. Regla del usuario: **no forzar; añadir datos reales** (ver [[Decisiones]]).
17. Generación renovable y **cobertura renovable prevista** (89,1 / 90,8 %) → bloque energía.
18. **Red Eléctrica: capacidad otorgada y pendiente** → bloque mercado. Aragón es la primera de España.
19. **Suelo (Ministerio de Transportes)** y **latencia a Madrid y Barcelona** → bloques suelo y conectividad. El suelo urbano se sacó del CAPEX porque lo inflaba y daba suelo gratis a Ceuta y Melilla (sin dato).
20. Resultado: Aragón sube con cada dato (Teruel 14.º → 11.º, Huesca 39.º → 22.º, Zaragoza 46.º → 32.º); Castilla y León sigue delante por clima, suelo, renovables y red libre. No se fuerza.

## 17/11/2026 · Modelos restantes

21. **Operación del CPD a 1 año (A3):** temperatura → PUE → consumo; % renovable → emisiones; agua y reserva mínima del ámbito. Validación de punta a punta: consumo 99,7 %, emisiones 89,4 %.
22. **Riesgo sísmico anual (P8):** 72,8 / 76,9 %, no cumple; no se usa.
23. Se crea esta carpeta de notas en Obsidian para registrar todo el proceso.

## 17/11/2026 · Peligrosidad sísmica oficial (IGN / NCSE-02)

24. Búsqueda de la fuente: el IGN no publica tabla por municipio ni servicio FDSN abierto; la fuente oficial con valores por municipio es la **norma sismorresistente NCSE-02** (BOE núm. 244, 11/10/2002, anejo 1, hecha con el mapa del IGN).
25. Lectura del PDF del BOE con `pypdf` (`src/cpd/fuentes/norma_sismica.py`): 2.615 municipios con su aceleración sísmica básica (ab) y coeficiente K. Errata del BOE detectada («DONOSITA SAN SEBASTIÁN»).
26. Regla fijada antes de ver resultados: por provincia, la ab de la capital; si no aparece en la norma, 0,04 g (el máximo posible). Entra en el filtro sísmico (≥ 0,16 g → con condiciones) y en el bloque de riesgos del score.
27. Resultado: Granada (0,23 g) recibe el motivo «diseño sísmico reforzado»; Murcia 0,15 g, Alicante y Almería 0,14 g. Aragón sigue subiendo: Huesca 22.º → 19.º, Zaragoza 32.º → 28.º, Teruel 11.º.
28. El modelo anual de terremotos usa ahora la norma como variable: 74,2 % en validación y 73,1 % en test; sigue sin cumplir (el año a año es aleatorio). El dato que manda para P8 es la norma, no el modelo.


## 17/11/2026 · Commits y PR

29. Commits en `feature/modelos-largo-plazo` subidos a la PR #6 (encima de #5), por tema: datos (red otorgada y pendiente, suelo, nodos, norma NCSE-02), modelos (generación renovable, cobertura, operación del CPD, riesgo sísmico), scoring, informe, mapa, datos del mapa y metodología. La descripción de la PR recoge la tabla de acierto y la comprobación de Aragón. 151 tests de Python y 21 del frontend en verde.


## 18/11/2026 · Mejora de la precisión de los modelos

30. Objetivo: subir el acierto de los modelos existentes con datos reales y eligiendo solo con la validación (sin mirar el test para decidir).
31. **Suma de tecnologías** para la generación renovable: tabla nueva `ccaa_generacion_tecnologia` (solar, eólica, hidráulica, otras y no renovable) a partir de la caché de REData que ya existía (cuadra al MWh con la tabla anterior). El mes a mes pasa de 84,9 % a **85,6 %: cumple**. Total de 12 meses 91,5 % / 93,6 %.
32. **Ridge sobre anomalías con la reserva de los embalses** para el % renovable: 84,3 % → 84,8 % mes a mes (a 0,2 del mínimo) y 88,7 % → 89,4 % la media anual. La operación del CPD (emisiones) sube de 89,4 % a 90,6 %.
33. Descartado por no mejorar la validación: el mismo Ridge en las reservas de agua, la interacción embalses × comunidad y juntar los dos candidatos en el %.
34. Corrección: el total anual de la generación renovable del pipeline era 90,9 % / 94,0 %, no 89,1 % / 90,8 % (cifras de un experimento previo que quitaba los meses a cero de Melilla). Corregido en la documentación.
35. Fallo encontrado y arreglado: el candidato nuevo devolvía tablas vacías sin tipo y rompía una figura; ahora las previsiones se fuerzan a número.

36. Commits de la mejora subidos a la PR #6 (generación por tecnología, candidatos nuevos, informe, mapa y metodología) y descripción de la PR corregida con las cifras reales.


## 18/11/2026 · Intento de llevar al 85 % los tres que no llegaban

37. Petición: mejorar precio de la luz, riesgo sísmico y % renovable mes a mes hasta el 85 %, sin forzar.
38. **% renovable mes a mes:** probadas la hidráulica desde los embalses y la suma de tecnologías también para el %; se queda entre 84,2 y 84,8 %. Tras cinco variantes con base física se para, para no ajustar a la validación a fuerza de intentos. Queda en 84,8 % (orientativo).
39. **Generación renovable mes a mes:** la hidráulica desde los embalses sí ayuda: 85,6 → **86,2 %** (test 88,2 %); total de 12 meses 92,3 / 93,5 %. Adoptado (`candidato_tecnologias_hidro_embalses`).
40. **Riesgo sísmico:** probado el horizonte de 3 años («algún M ≥ 3 en los próximos 3 años», más acorde con la vida de un CPD): 74,5 %, tampoco llega. Que haya un terremoto en un periodo concreto es aleatorio; para P8 manda la peligrosidad oficial (NCSE-02).
41. **Precio de la luz:** OMIP no publica en abierto el histórico de futuros (su web carga los precios con JavaScript y sus descargas solo traen la lista de contratos). Conseguirlo exigiría extraer años de datos de su web, lo que choca con sus condiciones de uso: pendiente de decisión del usuario. Aun así, a 12 meses en 2022-2025 el propio mercado de futuros falló mucho.

42. Decisión: no se extraen los futuros de OMIP (condiciones de uso y poca ganancia esperada). El precio de la luz queda definitivamente como orientativo. Anotado en `01_Objetivo_y_alcance.md` (D8) y en [[Decisiones]].

43. Commits subidos a la PR #6 (hidráulica desde los embalses, informe, mapa y metodología con la decisión de OMIP); descripción de la PR actualizada (generación renovable 86,2 % / 88,2 %, 154 tests).

44. Error de presentación corregido en el mapa: el aviso redondeaba el acierto a 0 decimales y el % renovable (84,8 %) salía como «acierta un 85 %, por debajo del 85 %». Ahora muestra un decimal.
45. Precio de la luz, último intento con datos propios: añadir la previsión del % renovable nacional (modelo de tecnologías) como variable junto al gas. Empeora: 29 % en validación (pocos años con datos por tecnología y la crisis de 2022 lo desestabilizan). Descartado. Fuentes de futuros: solo la CNMC los cita en sus informes PDF (contrato del mes siguiente); no hay histórico abierto.


## 18/11/2026 · Modelos del gas y del tiempo para el precio de la luz

46. Petición: hacer los modelos de gas y de tiempo, marcarlos como inestables y añadidos para la luz, conseguir los datos que falten y documentarlo todo (con gráficos) en Obsidian. Historia completa en [[Precio de la luz (historia)]].
47. Datos nuevos: tabla `generacion_nacional_detalle` (REData, a partir de la caché ya descargada): eólica, solar, hidráulica, nuclear, ciclo combinado, carbón y total de España. Función `ree.generacion_nacional_detalle` y paso nuevo en la ingesta.
48. **Modelo del gas** (MIBGAS spot): último valor, ETS sobre el log y futuros del gas (M+1, Q+1, Y+1). Elegido ETS: 70,4 % / 52,3 % → inestable.
49. **Modelo del tiempo** a través de la generación de España: eólica 86,6 % / 83,7 %, solar 90,9 % / 90,9 %, hidráulica 72,9 % / 85,5 % (con el Ridge de los embalses entre los candidatos). Marcados como entradas del precio, inestables.
50. **Diagnóstico:** con el gas y la generación reales de cada mes, el precio solo se explica en un 76,4 % (gas + eólica + solar + hidráulica) y en un **78,9 %** añadiendo nuclear, ciclo combinado y carbón. Falta el precio del CO2 (EEX, de pago; EEA solo publica emisiones), la demanda horaria y las interconexiones.
51. **Precio estructural** (gas y tiempo previstos): mejor candidato individual en validación (60,9 %), entra en la combinación. Precio final: 59,0 % → **59,7 %** en validación (test 62,4 % → 61,4 %). Sigue orientativo.
52. Informe: sección «Gas y tiempo: modelos añadidos para el precio de la luz (inestables)» y figura 15; filas nuevas en el control de acierto. Test nuevo de que gas y precio estructural no usan datos posteriores al origen. 155 tests de Python y 21 del frontend en verde.
53. Obsidian: carpeta `Figuras/` con las 15 figuras del informe, las de modelos y las capturas del mapa; notas nuevas [[Figuras]] (galería con explicación) y [[Precio de la luz (historia)]].


### 54. Subida a la PR #6 (18/11/2026)

- Cinco commits en `feature/modelos-largo-plazo`: modelos del gas y del tiempo (`feat(modelos)`), aviso con un decimal (`fix(mapa)`), informe y figuras (`docs(analisis)`), datos del mapa (`data(mapa)`) y estado/checklist (`docs(metodologia)`).
- Push a GitHub y descripción de la PR #6 actualizada con la tabla nueva (precio 59,7 / 61,4 %, gas y tiempo inestables) y el diagnóstico del 78,9 %.
- `viabilidad.json` se deja fuera (solo cambia la fecha de generación).


### 55. Qué IA y previsiones faltaban (18/11/2026)

- Petición: «Pasemos a el resto de IA's y predicciones que nos faltan».
- Se repasó la checklist (`06_Checklist_entrega.md`). La previsión que faltaba del enunciado era **A3 a medio plazo**: «previsiones a corto y medio plazo sobre la sostenibilidad operativa del CPD». El corto plazo (1 año) ya estaba (`operacion.py`); faltaba el **medio plazo (10 años)**.
- A 10 años, lo que cambia la operación de un CPD es el **clima** (temperatura → PUE → consumo) y el **agua** de los embalses.

### 56. Dato nuevo: temperatura desde 1981 (NASA POWER mensual)

- Problema: la tabla de clima diario empieza en 2015 (11 años): no basta para validar una previsión a 10 años.
- Solución: endpoint **mensual** de NASA POWER (misma fuente y mismo punto que la diaria, sin clave), 1981-2025, 52 provincias. Función `nasa_power.temperatura_mensual_larga()`, tabla `clima_mensual_largo.csv` (28.080 filas), paso nuevo en `actualizar.py`.
- Comprobación: en los 6.864 meses comunes con la tabla diaria, la diferencia media es **0,003 °C** (máx. 0,01): es el mismo dato.
- Las reservas de MITECO ya venían desde 1987 (se usan años completos desde 1988).

### 57. Modelo a medio plazo (`src/cpd/modelos/medio_plazo.py`)

- **Protocolo**: test = lo que se habría previsto desde 2015 para 2016-2025 (ningún modelo lo ve). Validación = orígenes 1995-2005 (temperatura) y 1997-2005 (reservas), cuyos 10 años terminan **antes** del test, para que elegir no mire el test.
- **Candidatos**: sin cambio, media de 10 años, media larga (30 años), tendencia lineal de 30 años, media de 10 años + tendencia, Holt amortiguado y la combinación de los 3 mejores.
- **Temperatura por provincia a 10 años**: combinación (media de 10 años, media larga y Holt). Acierto **97,7 %** validación y **94,8 %** test (error 0,34 y 0,79 °C). **Cumple.**
- **Consumo del CPD a 10 años** (temperatura prevista → PUE → consumo, de punta a punta): **99,8 % / 99,5 %**. Cumple (por debajo del 99,9 % de sospecha).
- **Reservas de agua por ámbito a 10 años**: año a año **83,3 % / 81,9 %** → no llega: el año concreto de una sequía no se puede saber con 10 años de antelación. Para una inversión a 10 años importa el **agua media de la década**: **91,1 % / 86,6 %** → cumple. El año a año se enseña como orientativo (no se esconde).
- **Hallazgo honesto**: el test muestra que el modelo elegido se queda corto con el calentamiento de 2016-2025 (prevía 14,6 °C de media y fue 15-16 °C). Los modelos con tendencia habrían acertado algo más en el test, pero en la validación (1996-2015, años de calentamiento más lento) no ganaban. **No se cambia la elección** (regla: se elige con la validación).
- **Escenario de sensibilidad** (no es la previsión): si sigue la tendencia de 30 años (+0,48 °C por década), España en 2035 estaría a 16,1 °C en lugar de 15,5 °C; PUE medio 1,455 → 1,461; consumo +0,5 %. Conclusión: el calentamiento afecta poco a la operación con la fórmula del simulador.
- **Emisiones a 10 años: no se prevén.** El mix por comunidad solo existe desde 2015: no se puede validar 10 años, y depende de decisiones políticas (PNIEC).

![[16_medio_plazo_10_anios.png]]

*Figura 16.* (a) Temperatura media anual de España (media de las 52 capitales): real, lo que se habría previsto desde 2015 (test, punteado) y previsión a 10 años con su intervalo. (b) Reserva media de los embalses por ámbito: últimos 10 años (azul) y próxima década (naranja).

### 58. Integración

- Control de acierto (figura 08): 4 filas nuevas (temperatura 10 años, consumo 10 años, reservas media de la década, reservas año a año).
- Informe `docs/analisis/previsiones_1_anio.md`: sección «Medio plazo: clima y agua a 10 años», con tablas de candidatos y la sensibilidad.
- Mapa: línea «A 10 años (2035)» en la ficha de cada provincia (temperatura, PUE, reserva media del ámbito y aciertos de test).
- Tests: 4 nuevos en `tests/test_modelos.py` (sin fuga, validación antes del test, intervalo que no se estrecha, acierto de la década) y 1 en `tests/test_fuentes.py` (lector del endpoint mensual); 1 en el frontend.
- Checklist: **A3 pasa a ✅**; P4 añade el agua media de la década.


### 59. Subida del medio plazo a la PR #6 (18/11/2026)

- Seis commits en `feature/modelos-largo-plazo`: temperatura mensual de NASA POWER (`feat(fuentes)`), modelo a 10 años (`feat(modelos)`), línea «A 10 años» en la ficha (`feat(mapa)`), informe y figuras (`docs(analisis)`), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`).
- Push a GitHub y descripción de la PR #6 con las 4 filas nuevas y la sección «Medio plazo a 10 años: A3 completo». Tests: 160 Python y 22 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 60. Qué modelos faltaban (18/11/2026)

- Petición: «Sigue con el resto de modelos que faltan».
- Repaso del enunciado (8 preguntas del simulador) y de la checklist. Pendientes con forma de modelo, por prioridad: **P2 impacto local** (🟡), **impacto socioeconómico** (E39-E41: empleo, inversión inducida, PIB; ❌) y un **escenario de demanda a 10 años con los nuevos CPD** (P5). Se empieza por P2 porque es una de las 8 preguntas que el simulador debe contestar.
- La especificación de Google Docs pedía iniciar sesión: se trabajó con el repo y la checklist.

### 61. Dato nuevo: agua de la red pública por comunidad (INE)

- Problema: no hay consumo de agua ni de electricidad abierto por municipio o provincia (E8, E14).
- Fuente: INE, «Estadística sobre el suministro y saneamiento del agua», **tabla 53447** (API Tempus3, sin clave): agua suministrada, registrada y distribuida y pérdidas por comunidad, bienal 2014-2024, en miles de m³. Función `ine.agua_ccaa()`, tabla `agua_ccaa.csv`, paso nuevo en `actualizar.py`.
- Incidencia: 6 comunidades no salían porque su nombre lleva coma («Asturias, Principado de, …»). Se corrigió buscando el indicador por el final del nombre. Comprobación: la suma de las comunidades da el total de España (3.283.073 frente a 3.283.072 miles de m³; diferencia de redondeo).
- Ceuta y Melilla se publican juntas (código «18-19»).

### 62. Modelo de impacto local (P2) · `src/cpd/modelos/impacto_local.py`

- **Electricidad**: consumo previsto del CPD (temperatura prevista → PUE) / demanda prevista de su comunidad (12 meses). **Validación de punta a punta: 96,1 %** (20 orígenes comunes de los modelos de temperatura y demanda). Sin test común (los dos modelos tienen el test en orígenes distintos), igual que la operación.
- **Red**: potencia máxima del CPD (50 MW de TI × PUE ≈ 73 MW) / capacidad de acceso **libre** de su comunidad (REE).
- **Agua**: agua del CPD (WUE 0,5 L/kWh) / agua registrada y distribuida de su comunidad (INE 2024).
- **Habitantes equivalentes**: consumo del CPD / consumo por habitante de la comunidad (todos los usos). Escala, no hogares.
- **Resultados**: provincia mediana 3,7 % de la electricidad (como ~90.000 habitantes) y 0,10 % del agua (como ~2.600): **pesa la electricidad, no el agua**. Ceuta y Melilla: más del 200 % (sistemas aislados); La Rioja 32 %. **Red**: Aragón usaría el **82 %** de su capacidad libre (solo 89 MW libres, porque ya tiene 3.938 MW otorgados); **Madrid, Navarra y Ceuta tienen 0 MW libres**: el CPD no cabe hoy.
- Cierra **P2, E43 y E44** (✅) y E14 pasa a 🟡 (dato por comunidad; municipal no existe).

![[17_impacto_local.png]]

*Figura 17.* Impacto previsto del CPD por comunidad: (a) % de la demanda eléctrica, (b) % de la capacidad de acceso libre, (c) % del agua distribuida.

![[mapa_impacto_local_zaragoza.png]]

*Ficha de Zaragoza en el mapa:* línea «Impacto en su comunidad (12 meses)».

### 63. Integración del impacto local

- Control de acierto (figura 08): fila «Impacto eléctrico local a 1 año (P2)», 96,1 %.
- Informe: sección «Impacto del CPD sobre los recursos locales (pregunta P2)».
- Mapa: línea en el bloque «Clima y agua» (Madrid: «0 MW libres en la red de acceso: hoy no cabe»).
- Tests: impacto con datos sintéticos (porcentajes, último año del agua, red sin capacidad) y lector del INE con nombres con coma; 1 en el frontend.
- Detalle de calidad: el eje del panel (c) salía con punto decimal; se cambió a coma.


### 64. Subida del impacto local a la PR #6 (18/11/2026)

- Seis commits: agua del INE (`feat(fuentes)`), modelo de impacto local (`feat(modelos)`), línea en la ficha (`feat(mapa)`), informe y figuras (`docs(analisis)`), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`).
- Push y descripción de la PR #6 con la fila «Impacto eléctrico local a 1 año (P2)» y la sección «Impacto local: P2 completo». Tests: 162 Python y 23 frontend.
- Siguientes modelos: impacto socioeconómico (E39-E41) y escenario de demanda a 10 años con los nuevos CPD (P5).


### 65. Impacto socioeconómico (E39-E41): qué se buscaba (18/11/2026)

- Petición: «Sí, sigue» (con el impacto socioeconómico). Variables del enunciado: E39 empleo generado, E40 inversión inducida, E41 PIB municipal, E42 atracción empresarial (todas ❌).
- Decisión de método: **modelo input-output de Leontief tipo I** (recomendación, no viene de clase): es el método estándar de la contabilidad nacional para medir efectos indirectos (un euro gastado en un proveedor hace producir a ese proveedor y a los suyos).

### 66. Datos nuevos del INE

- **Tablas Input-Output 2022** (Revisión Estadística 2024, publicadas el 19/12/2025): `cne_tio_22.xlsx`. Se leen dos hojas: **Tabla 1** (producción, VAB, importaciones, oferta y **empleo equivalente a tiempo completo** de 65 productos) y **Tabla 7** (**matriz inversa interior de Leontief**, ya calculada por el INE). Módulo nuevo `src/cpd/fuentes/ine_tio.py`; tablas `tio_ramas.csv` y `tio_leontief_interior.csv`.
- Comprobación: VAB total 1,25 billones de € y 19,0 millones de empleos ETC (cuadra con la contabilidad nacional). Multiplicador de producción del producto 40 (informática y **proceso de datos/hosting**, CNAE 62-63): 1,69.
- **PIB por provincia** (Contabilidad Regional, tabla 82284, último año con las 52 provincias: 2024): `ine.pib_provincias()`, `pib_provincia.csv`. Incidencia: los nombres de comunidad («Aragón», «Canarias») se colaban como provincias en el emparejamiento; se excluyen explícitamente.
- Búsqueda: la página de INEbase de las TIO lista los xlsx de 2016 a 2022; la tabla se descarga con `descargar_archivo` (queda en el registro de descargas).

### 67. Modelo socioeconómico · `src/cpd/modelos/socioeconomico.py`

- **Construcción (una vez)**: CAPEX de 400 M€ repartido por productos (**supuesto a calibrar** en `settings.yaml`: construcción 35 %, equipo eléctrico 30 %, maquinaria/refrigeración 20 %, ingeniería 8 %, instalación 7 %). A cada producto se le quita su **cuota de importación real**: se quedan en España **295 M€** (la mitad del equipo eléctrico y de la maquinaria se importa). Resultado: **3.402 empleos-año**, 562 M€ de producción (inversión inducida) y 217 M€ de VAB.
- **Operación (cada año)**: **60 empleos directos** (plantilla del simulador) + **217 indirectos** (proveedores de mantenimiento, seguridad, comercio, electricidad…) = **277 (×4,6)**. VAB directo 45,2 M€ (ingresos 91,9 − compras 46,7, con las fórmulas del VAN) + indirecto 33 M€ = **78 M€ al año**.
- **PIB (E41)**: no hay PIB municipal; VAB directo / PIB provincial: Melilla 2,5 %, Ceuta 2,3 %, **Soria 1,5 %**, Ávila 1,2 %, Teruel 1,0 %… Madrid 0,01 %.
- **Corrección durante el trabajo**: al principio se comparó el empleo de la obra con el paro de la provincia (Soria salía al 126 %). Se quitó: ese empleo se reparte por toda España (proveedores) y exageraba el peso local. Solo se compara el empleo directo.
- **No es una previsión**: es un cálculo con coeficientes de 2022, sin backtesting (no entra en el control de acierto).
- Checklist: **E39 y E40 ✅**, E41 🟡 (provincial), E42 sigue ❌.

![[18_impacto_socioeconomico.png]]

*Figura 18.* (a) Empleo de la obra por producto (empleos-año). (b) Empleo de un año de operación: plantilla (azul) y proveedores (naranja). (c) VAB directo / PIB de las 15 provincias donde más pesa.

### 68. Integración

- Informe: sección «Impacto socioeconómico: empleo, inversión inducida y PIB (E39-E41)».
- Mapa: línea «Empleo y economía (INE, tablas input-output)» en el bloque «Inversión, red y mercado».
- Tests: economía sintética de 4 productos (Leontief, cuota interior, reparto que suma 1), lector del PIB (descarta comunidades) y códigos «44 bis»; 1 en el frontend.
- Figura 18: el eje de (c) repetía marcas («0, 0, 1, 1») y la plantilla no se distinguía; se corrigió (decimales y plantilla en azul).


### 69. Escenarios de demanda a 10 años con los nuevos grandes consumos (P5) (18/11/2026)

- Petición: «Sigue con el proximo modelo y afinando los que ya existen».
- Problema: la previsión a 10 años (97,3 %) es **tendencial** (244 TWh en 2035, −4,8 %) y no sabe que llegan centros de datos, hidrógeno o industria electrificada.
- Dato real: Red Eléctrica ya ha **otorgado 18.535 MW** de acceso a nuevos consumos y tiene **23.500 MW en trámite**. Usada al 80 %, la otorgada serían **130 TWh/año**, la mitad de la demanda de España (256 TWh).
- No hay dato abierto de cuánto de lo otorgado llega a consumir (REE solo publica el último mes, sin histórico): se dan **escenarios** con supuestos a la vista (`settings.yaml → escenarios_demanda`), con la capacidad entrando de forma lineal en 10 años. **No es una previsión con acierto**.
- Resultados 2035: tendencial 244 TWh; +25 % de lo otorgado → 276 TWh (+8 %); +50 % → 309 TWh (+21 %); +100 % → 374 TWh (+46 %); techo (otorgada + en trámite) → 539 TWh.
- Por comunidad: **Aragón tiene otorgado el 243 % de su demanda actual** (la huella de los CPD anunciados), Extremadura 131 %, Castilla-La Mancha 127 %. Extremadura tiene en trámite el 668 % de su demanda.
- Código: `src/cpd/modelos/escenarios.py`. Figura 19, sección en el informe y dato en la ficha («≈ X % de su demanda actual si se usara al 80 %»). Tests: rampa lineal y peso por comunidad.
- Incidencia: un `.get(..., valor)` con el valor por defecto calculado siempre rompía la figura; se cambió por una condición.

![[19_escenarios_demanda.png]]

*Figura 19.* (a) Demanda de España: real, tendencial con su intervalo y escenarios con la red otorgada. (b) Energía de la red otorgada (naranja) y en trámite (azul) frente a la demanda de cada comunidad.

### 70. Afinado de los modelos existentes (18/11/2026)

- **prob_cpd** (B7 pedía mejorar con más datos): se probaron, con los mismos pliegues y la misma regla (menor log-loss), el **PIB provincial** (INE, dato nuevo) y **población + renta**.

| Candidato | Log-loss | ROC-AUC | Acierto con umbral de Youden |
|---|---|---|---|
| Solo población (actual) | 0,377 | 0,882 | **90,4 %** |
| Solo PIB | 0,359 | 0,889 | 82,7 % |
| Población + renta | **0,342** | **0,897** | 84,6 % |

- Conclusión: mejoran las probabilidades (log-loss, ROC) pero baja el acierto por debajo del 85 %. Con 52 provincias la diferencia son 2-3 provincias (ruido). **No es una mejora clara: se mantiene «solo población»** y se documenta como probado y descartado. No se fuerza.
- Informe socioeconómico: el reparto del CAPEX salía como «producto 27 35 %»; ahora con nombres («construcciones y trabajos de construcción 35 %…»).


### 71. Comprobación en el mapa (18/11/2026)

- Ficha de Zaragoza, bloque «Inversión, red y mercado»: «3.938 MW ≈ 243 % de su demanda actual si se usara al 80 %» y la línea «Empleo y economía» (VAB del CPD = 0,13 % del PIB de Zaragoza).
- Detalle de diseño: la nota bajo el valor salía en la letra de las cifras (monoespaciada); se cambió a la letra del texto, en su propia línea (`styles.css`).
- Tests: 168 de Python y 25 del frontend; build correcto.

![[mapa_red_otorgada_zaragoza.png]]


### 72. Subida del impacto socioeconómico, los escenarios P5 y el afinado a la PR #6 (18/11/2026)

- Seis commits: fuentes del INE (`feat(fuentes)`: tablas input-output y PIB provincial), modelos (`feat(modelos)`: socioeconómico y escenarios), ficha (`feat(mapa)`), informe y figuras 18-19 (`docs(analisis)`), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`).
- Push y descripción de la PR #6 con la sección «Impacto socioeconómico (E39-E41) y escenarios de demanda (P5)». Tests: 168 Python y 25 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 73. ¿Falta algún modelo? Atracción empresarial (E42) (18/11/2026)

- Petición: «Sigue con el resto de modelos que faltan si falta alguno».
- Repaso: las 8 preguntas del simulador ya tienen modelo (P1-P8). De las variables del enunciado, la única que pedía un **modelo** y seguía en ❌ era **E42 atracción empresarial**. El resto de ❌ son de **datos** (fibra, 5G, autopistas, puertos, aeropuertos, parcelas, calificación urbanística, calidad del agua).
- Dato nuevo: **sociedades mercantiles constituidas** por provincia y mes (INE, Estadística de Sociedades Mercantiles, **tabla 6295**, 2008-2025; último mes publicado: diciembre de 2025). `ine.sociedades_provincias()`, `sociedades_provincia.csv`. Comprobación: la suma de provincias da el total nacional (11.721 en dic-2025).
- Incidencia: la API del INE cortó la conexión por demasiadas consultas seguidas al buscar la tabla; se esperó 2,5 minutos y se reintentó con una sola petición.
- Modelo (`src/cpd/modelos/empresas.py`): mismo protocolo que las previsiones a 1 año (24 orígenes de validación, test de un año, combinación salvo mejora clara) y los mismos candidatos que la generación renovable en MWh. **Elegido: ETS** (mejora a la combinación en más de un 5 %).

| Medida | Validación | Test | Estado |
|---|---|---|---|
| Mes a mes | 87,9 % | 84,6 % | orientativo (el mes suelto es ruidoso) |
| **Total de 12 meses** (el indicador) | **93,4 %** | **92,6 %** | **cumple** |

- Indicador: sociedades creadas al año **por cada 10.000 habitantes** (previstas en 12 meses) y su cambio frente a los 12 anteriores. Es dinamismo empresarial, no mide qué empresas llegan por el CPD. Fuera del score (no se tocan los pesos).
- Integración: control de acierto (2 filas), sección del informe, figura 20, línea en la ficha («Atracción empresarial: X sociedades nuevas al año por cada 10.000 habitantes»). Tests: lector del INE (descarta comunidades) e indicador por 10.000 habitantes; 1 en el frontend.
- Checklist: **E42 ✅**. Sección E: 14 ✅, 22 🟡, 11 ❌.


### 74. Subida de la atracción empresarial a la PR #6 (18/11/2026)

- Seis commits: lector del INE (`feat(fuentes)`), modelo (`feat(modelos)`), línea en la ficha (`feat(mapa)`), informe y figura 20 (`docs(analisis)`), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`: «ya no falta ningún modelo del enunciado»).
- Push y descripción de la PR #6 con la fila E42 y la sección «Atracción empresarial (E42): ya no falta ningún modelo». Tests: 170 Python y 26 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 75. Afinado con los días hábiles (18/11/2026)

- Petición: «Sigue afinando los modelos que ya existen».
- Idea con base real: las sociedades se inscriben (y muchas actividades ocurren) en **días hábiles**; un mes con Semana Santa o más fines de semana tiene menos actividad aunque nada haya cambiado. Se puede prever la actividad **por día hábil** y multiplicar por los días hábiles del mes previsto, que se conocen de antemano (calendario público: no es fuga).
- Calendario nuevo `src/cpd/features/calendario.py`: lunes a viernes menos los festivos **nacionales** (1 y 6 de enero, Viernes Santo con la fecha de Pascua, 1 de mayo, 15 de agosto, 12 de octubre, 1 de noviembre, 6, 8 y 25 de diciembre). Los autonómicos y locales no se incluyen (aproximación). Comprobado: abril de 2025 = 21 días hábiles, agosto de 2025 = 20, diciembre de 2025 = 21.
- Envoltorio genérico en `anual.py` (`candidatos_por_dia_habil`, `escalar_por_dias`): convierte cualquier conjunto de candidatos en su versión por día.

**Atracción empresarial (E42): mejora y se adopta.** Todas las versiones por día hábil bajan el error de validación de su candidato base (ETS 21,1 → 20,0; estacional 25,2 → 22,7; anomalía 25,4 → 23,8…).

| E42 | Validación | Test |
|---|---|---|
| Mes a mes, antes (ETS) | 87,9 % | 84,6 % (no cumplía) |
| **Mes a mes, ahora** (combinación: ETS por día hábil, ETS, ETS 5 años sin tendencia por día hábil) | **88,3 %** | **85,4 % (cumple)** |
| Total de 12 meses, antes | 93,4 % | 92,6 % |
| Total de 12 meses, ahora | 93,0 % | 92,1 % |

- Se dice tal cual: el total anual baja unas décimas; la elección es con la validación.

**Demanda eléctrica: probado y descartado.** Por día hábil **empeora** (ETS 3,76 % → 5,31 % de MAPE en validación): la electricidad se consume todos los días. Por día natural no mejora (3,78 %). La combinación cambiaría solo por ruido (+0,2 validación, −0,1 test): **no se adopta**.

- Tests: días hábiles de meses conocidos y el envoltorio con una serie sintética de 10 sociedades por día hábil.
- Nombres de los modelos en el informe: «ETS (Holt-Winters amortiguado), por día hábil».


### 76. Subida del afinado por días hábiles a la PR #6 (18/11/2026)

- Cuatro commits: calendario y candidatos por día hábil (`feat(modelos)`), informe y figuras (`docs(analisis)`), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`).
- Push y descripción de la PR #6 con la fila E42 actualizada (mes a mes 88,3 % / 85,4 %) y la sección «Afinado por días hábiles». Tests: 172 Python y 26 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 77. «Resto de IA's»: técnicas de clase en los modelos (I51, I52, I58) (18/11/2026)

- Petición: «Sigue con el resto de IA's». Todos los modelos del enunciado ya existen; lo que faltaba eran **técnicas de la clase de Advanced Feature Engineering** sin aplicar a los modelos (checklist I): estacionariedad (I51), diferencias (I52) y winsorizing (I58).

**I51 · Estacionariedad** (`src/cpd/modelos/estacionariedad.py`). Criterio de la clase (media y desviación de cada año) + test **ADF** (Dickey-Fuller aumentado) sobre la demanda mensual de las 19 comunidades, 2015-2025 (sin meses imputados: en 2026 la suma salía anómala por el fallo de REData de julio-agosto, y se corrigió el análisis a años completos).

| Forma | Estacionarias (ADF, p < 0,05) | p mediano |
|---|---|---|
| Nivel | 0 de 19 | 0,61 |
| Logaritmo | 0 de 19 | 0,55 |
| Diferencia estacional Δ₁₂ log | 3 de 19 | 0,19 |
| **Doble diferencia Δ₁ Δ₁₂ log** | **19 de 19** | **< 0,001** |

- Lectura: la diferencia estacional quita la estacionalidad pero no del todo la tendencia (choques de 2020 y 2022); la doble diferencia es estacionaria en todas. Justifica que los modelos trabajen con el crecimiento interanual.

**I52 · Modelo sobre diferencias.** AR(1) sobre Δ₁₂ log (SARIMA(1,0,0)(0,1,0)₁₂): 96,1 % / 95,0 %, a la par del estacional y el Ridge. Pero entra en los 3 mejores por 0,003 puntos, desplaza al Ridge y la combinación empeora un poco en validación (MAPE 3,93 % frente a 3,90 %) → **no se usa** (queda detrás de `con_diferencias=True`).

**I58 · Winsorizing.** `Winsorizador` en `prob_cpd` (percentiles 1-99 **solo con el entrenamiento** de cada pliegue) y candidato `logistica_winsor`: log-loss 0,394 → 0,393, sin cambio de elegido (con 52 provincias los percentiles casi son el mínimo y el máximo). La feature más asimétrica es «terremotos por año» (asimetría 7,2).

- Checklist: **I51, I52 e I58 ✅**. Figura 21, sección del informe «Técnicas de clase: estacionariedad, diferencias y winsorizing». Tests: paseo aleatorio frente a su diferencia, winsorizador sin fuga y forma de la previsión sobre diferencias.

![[21_estacionariedad_demanda.png]]

*Figura 21.* Demanda de Madrid en sus cuatro formas, con la media de cada año ± una desviación: la media se aplana al diferenciar.


### 78. Subida de las técnicas de clase a la PR #6 (18/11/2026)

- Cuatro commits: técnicas I51, I52 e I58 en los modelos (`feat(modelos)`), informes y figuras (`docs(analisis)`: previsiones, métricas, ficha de prob_cpd, figura 21), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`).
- Push y descripción de la PR #6 con la sección «Técnicas de clase en los modelos: I51, I52 e I58». Tests: 175 Python y 26 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 79. Afinado de prob_cpd con las codificaciones de clase (I59, I61, I62) (18/11/2026)

- Petición: «Sigue afinando los modelos que ya existen. Y haz los que faltan». Del enunciado ya no falta ningún modelo; lo que faltaba eran tres técnicas de clase de modelado (polinómicas I59, frequency encoding I61, target encoding I62). Encajan en `prob_cpd`, el único modelo con una variable categórica (la comunidad autónoma).
- Candidatos nuevos (mismos pliegues, misma regla: menor log-loss):

| Candidato | Log-loss | ROC-AUC | Acierto con umbral |
|---|---|---|---|
| Solo población (antes elegido) | 0,377 | 0,882 | 90,4 % |
| + población² (polinómica, I59) | 0,371 | 0,880 | — |
| + frecuencia de la comunidad (I61) | 0,387 | 0,874 | — |
| **+ comunidad con target encoding (I62)** | **0,316** | **0,925** | **92,3 %** |

- **Nuevo elegido: target encoding.** Es la proporción de provincias con CPD en la comunidad, aprendida **solo con el entrenamiento** de cada pliegue y con validación cruzada interna (`TargetEncoder` de scikit-learn): ninguna provincia ve su propia etiqueta. Recoge el efecto regional (las tres provincias del País Vasco tienen CPD).
- Ejemplo en el mapa: Castellón no tiene CPD y sale al 71 % (parecida a las que sí tienen).
- Incidencias durante el trabajo: (1) un test mal planteado (entrenaba sin la comunidad que luego evaluaba; para una comunidad nunca vista el codificador usa la media global, que es lo correcto) → corregido; (2) aviso de scikit-learn 1.9 (`random_state` obsoleto en `TargetEncoder`) → se pasa un `StratifiedKFold` en `cv`; (3) el pipeline se rompió porque el ajuste final no tenía las columnas nuevas → corregido en `ejecutar_prob_cpd`; (4) la ficha del modelo decía «añadir variables no mejora» → texto reescrito; (5) curva ROC con 7 curvas ilegible → elegido destacado y leyenda debajo.
- Checklist: **I59, I61, I62 ✅**; B7 actualizado. Sección I: 47 ✅, 11 🟡, 12 ❌.

![[roc_prob_cpd.png]]

*Curva ROC fuera de pliegue:* elegido (naranja), baseline de solo población (azul) y el resto (gris).


### 80. Subida del afinado de prob_cpd a la PR #6 (18/11/2026)

- Cinco commits: modelo con target encoding (`feat(modelos)`), nombre en la ficha (`feat(mapa)`), métricas, ficha y figuras (`docs(analisis)`), datos del mapa (`data(mapa)`) y checklist/estado (`docs(metodologia)`).
- Push y descripción de la PR #6 con la fila de prob_cpd (92,3 %) y la sección «prob_cpd con target encoding de la comunidad». Tests: 177 Python y 26 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 81. Precio de la luz: segundo afinado (18/11/2026)

- Petición: «Sigue con el resto de IA's y si están todas hechas mejora la de la luz y etc». Todas las IA estaban hechas (de la clase solo queda I63, embeddings, opcional y sin sentido aquí).
- CO2: ICAP pide permiso previo por escrito; Ember archivado → no se usa.
- Diagnóstico con datos reales: + demanda 80,0 %; + emisiones CO2 REE 80,2 %; + reserva 78,3 % (no ayuda).
- Candidato `estructural_demanda` (`gas_tiempo.candidato_precio_estructural(..., demanda)`): validación 59,7 → **61,7 %**, test 61,4 → **57,1 %** (se elige con la validación y se dice tal cual).
- Nueva fila en el control: **precio medio de 12 meses** 70,5 % / 68,0 % (orientativo).
- Test de fuga: la demanda posterior al origen no cambia la previsión; si la demanda acaba antes del origen, la ETS se alarga.
- Detalle para la presentación en [[Precio de la luz (historia)]] (sección 7).


### 82. Subida del segundo afinado del precio a la PR #6 (18/11/2026)

- Cuatro commits: precio con la demanda y acierto de la media anual (`feat(modelos)`), informe y figuras (`docs(analisis)`), datos del mapa (`data(mapa)`) y estado (`docs(metodologia)`).
- Push y descripción de la PR #6 con las filas del precio (61,7 % / 57,1 %; media de 12 meses 70,5 % / 68,0 %) y la sección «Precio de la luz con la demanda». Tests: 178 Python y 26 frontend.
- `viabilidad.json` fuera (solo cambia la fecha).


### 83. Todo subido a GitHub (20/11/2026)
- Revisión: código y APIs (`src/cpd/fuentes/`, 25 módulos) ya estaban subidos. Las 7 ramas locales estaban sincronizadas con GitHub. No hay secretos: no existe `.env` y AEMET/ESIOS no se usan.
- Las PRs #1 a #6 estaban encadenadas y se han fusionado en `main` con merge commit. `main` ya tiene los 93 commits que le faltaban.
- Los datos no van en git (están en `.gitignore`; un CSV del censo pesa 266 MB, por encima del límite de 100 MB). Se han subido a la Release [datos-completos-2026-11-20](https://github.com/MarcMunta/Proyecto-3/releases/tag/datos-completos-2026-11-20):
  - contenido: `data/raw` (incluida la caché de todas las APIs), `data/clean`, `data/curated`, la DuckDB `p3_cpd.duckdb` y `models/`;
  - tamaño: 1767 ficheros, 915 MB sin comprimir y 204 MB en el zip;
  - verificación: SHA-256 del zip `529be1a0…0575` y manifiesto con el SHA-256 de cada fichero.
- Para restaurar los datos, descomprime el zip en la raíz del repo.
