---
tags: [clase, proyecto-3, modelos]
actualizado: 2026-11-18
---

# Modelos del Proyecto 3

Volver a [[00 Índice]]. Requisito del equipo (D8, ver [[Decisiones]]): **85 % ≤ acierto < 99,9 %** (objetivo 90 %). Acierto = 100 × (1 − WAPE) en regresión; accuracy en clasificación. Un modelo que no cumple se enseña como orientativo, con aviso, y no se usa como dato. Gráficos de todos en [[Figuras]].

| Modelo | Qué predice | Acierto validación | Acierto test | Estado |
|---|---|---|---|---|
| Demanda por comunidad a 1 año | Demanda eléctrica mensual de cada comunidad, 12 meses | 96,7 % | 95,6 % | cumple (objetivo 90 %) |
| Reservas de agua a 1 año | Reserva de los embalses de cada ámbito hidrográfico | 86,7 % | 85,3 % | cumple |
| Temperatura por provincia a 1 año | Temperatura media mensual (entra en el PUE) | 93,8 % | 92,8 % | cumple (objetivo 90 %) |
| Renovables por comunidad · % medio 12 meses | % de generación renovable de la comunidad | 89,4 % | 92,2 % | cumple |
| Renovables por comunidad · mes a mes | Lo mismo, mes a mes | 84,8 % | 88,6 % | no cumple por 0,2: orientativo |
| Generación renovable · mes a mes | MWh renovables de la comunidad | 86,2 % | 88,2 % | **cumple** (desde el 18/11/2026) |
| Generación renovable · total 12 meses | MWh renovables (→ cobertura renovable) | 92,3 % | 93,5 % | cumple (objetivo 90 %) |
| Precio de la luz a 1 año | Precio spot medio mensual | 61,7 % | 57,1 % | no cumple: orientativo, fuera del VAN (con gas, tiempo y demanda desde el 18/11) |
| Precio de la luz · media de 12 meses | Precio medio de los 12 meses (el del VAN) | 70,5 % | 68,0 % | no cumple: orientativo |
| · Gas (MIBGAS) a 1 año | Gas spot mensual, entrada del precio | 70,4 % | 52,3 % | **inestable**: solo para el precio |
| · Eólica (España) a 1 año | Generación eólica mensual (viento), entrada del precio | 86,6 % | 83,7 % | **inestable**: solo para el precio |
| · Solar (España) a 1 año | Generación solar mensual (sol), entrada del precio | 90,9 % | 90,9 % | **inestable**: solo para el precio |
| · Hidráulica (España) a 1 año | Generación hidráulica mensual (lluvia y embalses), entrada del precio | 72,9 % | 85,5 % | **inestable**: solo para el precio |
| Demanda nacional a 10 años | Demanda anual de España | 97,3 % (backtesting) | — | cumple (objetivo 90 %) |
| Temperatura por provincia a 10 años | Temperatura media anual hasta 2035 (medio plazo, A3) | 97,7 % | 94,8 % | cumple (objetivo 90 %) |
| Operación del CPD a 10 años · consumo | Temperatura prevista → PUE → consumo | 99,8 % | 99,5 % | cumple (por debajo del 99,9 %) |
| Reservas de agua a 10 años · media de la década | Agua media de los embalses del ámbito 2026-2035 | 91,1 % | 86,6 % | cumple |
| Reservas de agua a 10 años · año a año | Lo mismo, cada año | 83,3 % | 81,9 % | no cumple: orientativo |
| `prob_cpd` | Probabilidad de que una provincia tenga CPD (parecido a las que ya tienen) | 92,3 % (fuera de pliegue; antes 90,4 %) | — | cumple (objetivo 90 %); desde el 18/11, población + comunidad con target encoding |
| Operación del CPD a 1 año · consumo | Consumo del CPD de referencia (temperatura → PUE) | 99,7 % | — | cumple (por debajo del 99,9 % de sospecha) |
| Operación del CPD a 1 año · emisiones | Emisiones con el mix de su comunidad | 90,6 % | — | cumple (objetivo 90 %) |
| Impacto eléctrico local a 1 año (P2) | % del consumo del CPD sobre la demanda prevista de su comunidad | 96,1 % | — (sin test común) | cumple (objetivo 90 %) |
| Atracción empresarial (E42) · total 12 meses | Sociedades mercantiles creadas por provincia (INE) | 93,0 % | 92,1 % | cumple (objetivo 90 %) |
| Atracción empresarial (E42) · mes a mes | Lo mismo, mes a mes | 88,3 % | 85,4 % | **cumple** (desde el afinado por días hábiles, 18/11/2026) |
| Riesgo sísmico anual | Algún terremoto M ≥ 3 en la provincia el año siguiente (con la norma NCSE-02 como variable) | 74,2 % | 73,1 % | no cumple: no se usa |

## Cómo se ha buscado el menor error (protocolo común)

1. **Backtesting a 1 año con 24 orígenes**: en cada origen se entrena solo con lo que se sabía entonces y se prevén los 12 meses siguientes.
2. **Candidatos**: baselines (último valor, mismo mes del año anterior, media 12 meses, climatología), ETS de Holt-Winters, ML (Ridge, gradient boosting, logística) y la **combinación** de los 3 mejores.
3. **Elección con la validación** (la combinación salvo que un modelo solo la mejore > 5 %). El **test** es un año que ningún modelo ha visto.
4. **Control de acierto** automático en cada ejecución (`python -m cpd.modelos`), con tabla y figura 08.

## Impacto local (P2, 18/11/2026)

Código: `src/cpd/modelos/impacto_local.py`. Figura 17 ([[Figuras]]). Pasos en [[Proceso]] (60-63).

- Peso previsto del CPD sobre la **electricidad** (demanda prevista de su comunidad), la **red** (capacidad de acceso libre, REE) y el **agua** (agua distribuida, INE) de su comunidad, con habitantes equivalentes.
- Validación de punta a punta del % eléctrico: **96,1 %** (20 orígenes).
- Hallazgos: pesa la electricidad (mediana 3,7 %), no el agua (0,10 %). Aragón usaría el 82 % de la red libre; Madrid, Navarra y Ceuta tienen 0 MW libres.

## Atracción empresarial (E42, 18/11/2026)

Código: `src/cpd/modelos/empresas.py`. Figura 20. Pasos en [[Proceso]] (73). Sociedades mercantiles creadas por provincia (INE, tabla 6295, 2008-2025), previsión a 1 año con el protocolo común; desde el afinado, combinación con candidatos **por día hábil** (mes a mes 84,6 % → 85,4 % en test). Indicador por 10.000 habitantes: Málaga 47,0, Madrid 41,9, Baleares 41,7… Ávila 9,7, Ceuta 8,4.

## Escenarios de demanda a 10 años (P5, 18/11/2026)

Código: `src/cpd/modelos/escenarios.py`. Figura 19. Pasos en [[Proceso]] (69). **Escenario, no previsión** (sin acierto).

- Tendencial validado (244 TWh en 2035) + energía de la red otorgada por REE (18.535 MW) en 25 / 50 / 100 %: 276 / 309 / 374 TWh; techo con lo pedido 539 TWh.
- Aragón: red otorgada = 243 % de su demanda actual.

## Afinado (18/11/2026)

- **Precio de la luz con la demanda:** candidato estructural + demanda prevista; validación 59,7 → 61,7 %, test 61,4 → 57,1 % (se elige con la validación). CO2: ICAP pide permiso, Ember archivado → no se usa. Ver [[Precio de la luz (historia)]] (7).

- **prob_cpd con target encoding de la comunidad (I62):** elegido por la regla de siempre; log-loss 0,377 → 0,316, ROC-AUC 0,882 → 0,925, acierto 90,4 % → 92,3 %. Polinómica (I59) y frequency encoding (I61) probadas, sin ganar.

- **Técnicas de clase (I51, I52, I58):** estacionariedad con ADF (doble diferencia estacionaria en 19 de 19 comunidades; nivel en 0); modelo sobre diferencias AR(1) a la par del estacional pero sin mejorar la combinación (no se usa); winsorizing en `prob_cpd` sin cambio apreciable. Figura 21.

- **Días hábiles** (`features/calendario.py`): versiones «por día hábil» de los candidatos. Atracción empresarial: el mes a mes pasa a cumplir (88,3 % / 85,4 %). Demanda eléctrica: probado y descartado (por día hábil empeora; por día natural no mejora).

- `prob_cpd`: probados PIB y población + renta. Mejor log-loss (0,342) pero acierto 84,6 % (< 85 %): no es mejora clara con 52 provincias; se mantiene «solo población» (90,4 %).

## Impacto socioeconómico (E39-E41, 18/11/2026)

Código: `src/cpd/modelos/socioeconomico.py`. Figura 18 ([[Figuras]]). Pasos en [[Proceso]] (65-68). **Es un cálculo, no una previsión**: no tiene acierto (no entra en el control).

- Modelo input-output de Leontief tipo I con las Tablas Input-Output 2022 del INE (inversa interior y empleo por rama).
- Obra: 400 M€ → 295 M€ en España → **3.402 empleos-año**, 217 M€ de VAB. Reparto del CAPEX = supuesto a calibrar.
- Operación: **60 directos + 217 indirectos** al año (×4,6); 78 M€ de VAB al año.
- VAB directo / PIB provincial: Soria 1,5 %, Madrid 0,01 %.

## Medio plazo: clima y agua a 10 años (18/11/2026) · objetivo A3

Código: `src/cpd/modelos/medio_plazo.py`. Figura 16 ([[Figuras]]). Pasos detallados en [[Proceso]] (55-58).

- **Por qué**: A3 pide previsiones a corto **y medio plazo** de la sostenibilidad operativa del CPD; el corto (1 año) ya estaba. A 10 años lo que cambia es el clima (temperatura → PUE → consumo) y el agua.
- **Dato nuevo**: temperatura mensual de NASA POWER desde 1981 (la diaria empieza en 2015). Mismo dato que la diaria (diferencia media 0,003 °C).
- **Protocolo**: test desde 2015 (2016-2025); validación con orígenes 1995-2005, cuyos 10 años acaban antes del test.
- **Candidatos**: sin cambio, media de 10 años, media larga (30 años), tendencia de 30 años, media de 10 años + tendencia, Holt amortiguado, combinación.
- **Resultado**: temperatura 97,7 % / 94,8 % (combinación de medias y Holt); consumo 99,8 % / 99,5 %; agua media de la década 91,1 % / 86,6 %; agua año a año 83,3 % / 81,9 % (orientativo).
- **Hallazgo**: el modelo elegido se quedó corto con el calentamiento de 2016-2025 (test). La validación cae en 1996-2015, cuando subió más despacio. No se cambia la elección; se da una **sensibilidad**: con la tendencia de 30 años (+0,48 °C por década), 2035 a 16,1 °C en vez de 15,5 °C → PUE 1,455 → 1,461, consumo +0,5 %.
- **No se prevé**: emisiones a 10 años (mix por comunidad solo desde 2015; depende del PNIEC).

## Modelos del gas y del tiempo (18/11/2026) · entradas del precio, inestables

Historia completa para la presentación en [[Precio de la luz (historia)]]. Código: `src/cpd/modelos/gas_tiempo.py`. Figura: `15_gas_y_tiempo.png` ([[Figuras]]).

- **Por qué se hacen**: el precio de la luz no pasaba del 60 %. En España lo marca casi siempre la central de gas (ciclo combinado) y baja cuando hay viento, sol o agua. Si se prevén el gas y el tiempo por separado, se puede construir un precio «estructural».
- **Gas**: último valor, ETS sobre el logaritmo y **futuros del gas** de MIBGAS (M+1 el mes siguiente, Q+1 hasta 4 meses, Y+1 el resto) negociados en el origen.
- **Tiempo**: generación de España por tecnología (REData) — eólica (viento), solar (sol), hidráulica (lluvia; con el Ridge sobre anomalías de la reserva de los embalses). Mismos candidatos que las renovables.
- **Precio estructural**: Ridge sobre log(precio) con log(gas), cuotas de eólica, solar, hidráulica, nuclear, ciclo combinado y carbón, ciclo combinado × gas y mes. Se ajusta con los meses reales hasta el origen y se alimenta con el gas y la generación previstos (ETS). Entra como un candidato más del precio.
- **Resultado**: el precio sube en validación de 59,0 % a **59,7 %**; en test baja de 62,4 % a 61,4 %. Se dice tal cual: se elige con la validación.
- **Por qué son inestables**: el gas de dentro de un año no se puede saber (validación 70,4 % y test 52,3 %); la hidráulica depende de la lluvia (72,9 % / 85,5 %). Los aciertos cambian mucho entre validación y test. Por eso **no se usan como dato** en el mapa: solo alimentan el precio.
- **Diagnóstico**: con el gas y la generación **reales** de cada mes (no es previsión), el precio estructural acierta un **78,9 %**. Ni sabiendo el gas y el tiempo se llega al 85 %. Falta el **precio del CO2** (EEX es de pago; la EEA solo da emisiones), la demanda horaria y las interconexiones.
- Probado y descartado: usar la cuota renovable prevista como variable del precio (29 %).

## Mejoras del 18/11/2026 (elegidas solo con la validación)

- **Suma de tecnologías** (generación renovable): solar, eólica, hidráulica y resto se prevén por separado y se suman. Datos: generación por tecnología de REData que ya se descargaba. El mes a mes pasa de 84,9 % a 85,6 %.
- **Hidráulica desde los embalses** dentro de la suma de tecnologías: 85,6 % → **86,2 %**.
- **Ridge sobre anomalías con la reserva de los embalses** (% renovable): 84,3 % → 84,8 % mes a mes; media anual 88,7 % → 89,4 %.
- Probado y **descartado** (no mejoraba la validación): el Ridge en las reservas de agua, la interacción embalses × comunidad, la suma de tecnologías y la hidráulica desde los embalses para el %.
- El test de las renovables bajó un poco (89,5 → 88,6 %): se elige con la validación y se dice tal cual.
- Aviso del mapa: el acierto se enseña con **un decimal** (84,8 %); redondeado a 0 decimales salía «85 %» y parecía que cumplía.

## Por qué algunos no llegan (sin forzarlos)

- **Precio de la luz**: ni a 1 mes vista se pasa del 77 % (ETS). En validación el precio fue de 14 €/MWh (abril 2024) a 133 €/MWh (febrero 2023). Con los modelos del gas y del tiempo sube a 59,7 %, y aun con el gas y la generación reales solo se explica un 78,9 %. La fuente que podría ayudar (futuros de OMIP) no está en abierto: haría falta extraerla de su web, lo que choca con sus condiciones de uso; y el mercado de futuros también falló mucho en 2022-2024.
- **Renovables mes a mes (%)**: dependen del viento, la lluvia y el sol de cada mes; tras cinco variantes con base física se queda en 84,8 %. En la media de 12 meses sí cumple.
- **Reservas de agua a 10 años, año a año**: el año concreto de una sequía no se puede saber con 10 años de antelación (83,3 %). La media de la década, que es lo que importa para invertir, sí cumple.
- **Riesgo sísmico**: que haya un M ≥ 3 en un periodo concreto es aleatorio; a 1 año 74 % y a 3 años 74,5 %. Para P8 manda la peligrosidad oficial (NCSE-02), en el filtro y el score.
