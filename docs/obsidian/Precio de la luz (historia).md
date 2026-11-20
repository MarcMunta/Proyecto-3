---
tags: [clase, proyecto-3, precio-luz, presentacion]
actualizado: 2026-11-18
---

# El precio de la luz: el modelo más difícil (historia para la presentación)

Volver a [[00 Índice]] · ver también [[Modelos]], [[Decisiones]], [[Proceso]].

**Mensaje para la presentación:** el precio de la luz fue lo más difícil del proyecto. El primer modelo a 1 año daba en torno a un **60 % de precisión**. Para intentar subirla añadimos los cálculos de un **modelo del gas** y de un **modelo del tiempo** (viento, sol y agua a través de la generación eléctrica), entre otras cosas. Lo subimos un poco, pero no llegamos al 85 % exigido, y explicamos por qué con datos: ni sabiendo el gas y el tiempo reales de cada mes se explica más de un 79 % del precio.

## 1. Punto de partida (17/11/2026)

- Previsión mensual del precio spot de los 12 meses siguientes, con backtesting de 24 orígenes (2022-2025).
- Candidatos: último valor, media de 12 meses, mismo mes del año anterior, ETS, Ridge, Ridge con el gas de MIBGAS, gradient boosting y la combinación de los 3 mejores.
- Resultado: **59,0 % de acierto en validación y 62,4 % en test**. El mejor modelo para el mes siguiente solo llega al 77 %.
- Causa: en validación el precio fue de 14 €/MWh (abril de 2024) a 133 €/MWh (febrero de 2023); el gas y el tiempo de dentro de un año no se saben.
- Decisión D7: el simulador usa la media real de 12 meses para el VAN; la previsión del precio se enseña como escenario orientativo.

![[01_precio_luz_1_anio.png]]
*Figura 1 del informe: precio real, lo que habría previsto el modelo hace un año, previsión a 1 año con su intervalo y el gas de MIBGAS en su propio panel.*

![[05_backtesting_precio.png]]
*Figura 2: las 24 previsiones a 1 año de validación frente al precio real (la previsión tarda en reaccionar a los cambios bruscos).*

## 2. Fuentes que se buscaron (17-18/11/2026)

- **Futuros de electricidad de OMIP**: no hay histórico abierto (su web carga los precios con JavaScript; las descargas solo traen la lista de contratos). La CNMC los cita en sus informes en PDF, solo el contrato del mes siguiente. Extraerlos de la web de OMIP choca con sus condiciones de uso → decisión: no se usan.
- **Precio del CO2 (derechos de emisión UE)**: sin fuente abierta (la bolsa EEX es de pago; la EEA solo publica emisiones).

## 3. Primer intento con datos propios: el % renovable previsto (18/11/2026)

- Se añadió como variable del precio la previsión del % renovable de España (modelo de tecnologías) junto a los futuros del gas.
- **Empeoró: 29 % en validación** (pocos años con datos por tecnología y la crisis de 2022 lo desestabilizan). Descartado.

## 4. Modelos del gas y del tiempo (18/11/2026) — **inestables, añadidos para la luz**

Código: `src/cpd/modelos/gas_tiempo.py`. Datos nuevos: `generacion_nacional_detalle` (REData: eólica, solar, hidráulica, nuclear, ciclo combinado, carbón y total de España).

| Modelo (entrada del precio) | Qué prevé | Acierto validación | Acierto test | Lectura |
|---|---|---|---|---|
| Gas natural (MIBGAS) | Precio spot mensual del gas | 70,4 % | 52,3 % | muy inestable |
| Eólica de España (tiempo: viento) | MWh eólicos al mes | 86,6 % | 83,7 % | inestable |
| Solar de España (tiempo: sol) | MWh solares al mes | 90,9 % | 90,9 % | estable |
| Hidráulica de España (tiempo: lluvia y embalses) | MWh hidráulicos al mes | 72,9 % | 85,5 % | muy inestable |

![[15_gas_y_tiempo.png]]
*Figura 15: gas y generación eólica, solar e hidráulica de España, últimos 3 años y previsión a 1 año, con su acierto.*

**Precio estructural:** log(precio) = f(log(gas), cuotas de eólica, solar, hidráulica, nuclear, ciclo combinado y carbón, ciclo combinado × gas, mes), ajustado con los meses reales y alimentado con las previsiones del gas y de cada tecnología. Es el **mejor candidato individual en validación (60,9 %)** y entra en la combinación.

## 5. Resultado final del precio

| Momento | Acierto validación | Acierto test |
|---|---|---|
| Primer modelo (17/11) | 59,0 % | 62,4 % |
| Con el precio estructural de gas y tiempo (18/11) | **59,7 %** | 61,4 % |

**Diagnóstico clave:** aun usando el gas y la generación **reales** de cada mes (sin previsión), el precio solo se explica en un **78,9 %** (76,4 % sin nuclear ni ciclo combinado). Faltan datos que no son abiertos o no son mensuales: el precio del CO2, la demanda hora a hora y las interconexiones con Francia y Portugal. Conclusión: el límite no es el algoritmo, son la información disponible y la imprevisibilidad del gas y del tiempo a un año.

![[mapa_precio_59_y_renovables_84_8.png]]
*Captura del mapa (18/11/2026): el gráfico del precio sale con el aviso «previsión orientativa, 59,0 %» y no se usa en el VAN.*

## 6. Otros detalles que contar

- El mapa redondeaba el acierto a 0 decimales y el % renovable (84,8 %) aparecía como «acierta un 85 %, por debajo del 85 %». Corregido: ahora sale con un decimal.

![[mapa_precio_59_y_renovables_redondeo_85.png]]
*Captura antes del arreglo: «acierta un 85 %, por debajo del mínimo del 85 %».*

- Todas las mejoras se eligieron solo con la validación y el test se cuenta tal cual, aunque baje.


## 7. Segundo afinado: la demanda y la media anual (18/11/2026, noche)

- **CO2, otra vez:** se buscaron fuentes abiertas del precio de los derechos de emisión. El **ICAP Allowance Price Explorer** solo permite reutilizar sus datos con **permiso previo por escrito**, y el **Carbon Price Viewer de Ember** está archivado. Misma regla que con OMIP: sin permiso, no se usan.
- **Techo con datos reales** (diagnóstico, cada mes con el gas, la generación y la variable nueva reales):

| Variables | Precio explicado |
|---|---|
| Gas + mix de generación (antes) | 78,9 % |
| + reserva de los embalses | 78,3 % (no ayuda) |
| **+ demanda eléctrica nacional** | **80,0 %** |
| + emisiones de CO2 del sistema (REE) | 80,2 % |

- **Candidato nuevo:** el precio estructural con la **demanda** prevista (ETS desde su último dato real; la demanda limpia llega a diciembre de 2025). Entra en la combinación por la regla de la validación.

| Precio de la luz | Validación | Test |
|---|---|---|
| Primer modelo (17/11) | 59,0 % | 62,4 % |
| Con gas y tiempo (18/11) | 59,7 % | 61,4 % |
| **Con gas, tiempo y demanda (18/11, noche)** | **61,7 %** | **57,1 %** |
| Media de 12 meses (lo que pesaría en el VAN) | 70,5 % | 68,0 % |

- **Se dice tal cual:** la validación sube 2 puntos y el test baja 4. Se elige con la validación (cambiar la decisión después de ver el test sería trampa). El precio sigue siendo **orientativo y fuera del VAN**; ni la media anual llega al 85 %.
- **Mensaje para la presentación:** en tres rondas (gas y tiempo, demanda, media anual) el precio mensual a 1 año pasó del 59 al 62 % en validación; el techo con datos reales es del 80 %, y lo que falta (precio del CO2, futuros de la luz) no es abierto.

![[01_precio_luz_1_anio.png]]
*Figura 1 actualizada: previsión del precio con la combinación nueva.*
