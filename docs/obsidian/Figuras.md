---
tags: [clase, proyecto-3, figuras]
actualizado: 2026-11-18
---

# Figuras del proyecto (para el documento)

Volver a [[00 Índice]]. Copias de `docs/figuras/` del repositorio (se regeneran con `python -m cpd.modelos`). Los archivos están en `Clase/Proyecto 3/Figuras/`. Todas usan el mismo estilo: real en azul, previsión en naranja, un solo eje Y por gráfico y colores comprobados para daltonismo.

## Previsiones a 1 año

![[01_precio_luz_1_anio.png]]
**Precio de la luz.** Arriba, precio real desde 2021, lo que el modelo habría previsto hace un año (punteado), la previsión de los próximos 12 meses con su intervalo y la media de 12 meses que usa el simulador. Abajo, en su propio eje, el gas de MIBGAS. Acierto 59,7 % / 61,4 %: orientativo (ver [[Precio de la luz (historia)]]).

![[05_backtesting_precio.png]]
**Backtesting del precio.** Las 24 previsiones a 1 año de validación frente al precio real.

![[15_gas_y_tiempo.png]]
**Gas y tiempo (entradas del precio, inestables).** Gas de MIBGAS y generación eólica, solar e hidráulica de España, con su acierto.

![[02_demanda_ccaa_1_anio.png]]
**Demanda por comunidad.** Últimos 3 años y previsión a 1 año de cada comunidad (acierto 96,7 % / 95,6 %).

![[06_reservas_ambitos_1_anio.png]]
**Reservas de agua por ámbito.** Últimos 3 años y previsión a 1 año (86,7 % / 85,3 %).

![[09_temperatura_provincias_1_anio.png]]
**Temperatura por provincia.** Último año real y previsión de los próximos 12 meses con su intervalo (93,8 % / 92,8 %). Es la variable del PUE.

![[10_temperatura_mensual.png]]
**Temperatura mensual** de las 4 provincias más frías y las 4 más cálidas según la previsión.

![[11_renovables_ccaa_1_anio.png]]
**% renovable por comunidad.** Último año y previsión de los próximos 12 meses (media anual 89,4 % / 92,2 %; mes a mes 84,8 %, orientativo).

![[12_renovables_mensual.png]]
**% renovable mensual** de cada comunidad.

![[13_cobertura_renovable_ccaa.png]]
**Cobertura renovable** (generación renovable / demanda) por comunidad. Por encima del 100 % sobra energía verde.

![[14_operacion_cpd_emisiones.png]]
**Operación del CPD a 1 año (A3, corto plazo).** Emisiones del CPD de referencia por provincia con el mix de su comunidad (90,6 %).

![[17_impacto_local.png]]
**Impacto local del CPD (P2, 18/11/2026).** Por comunidad: (a) % de la demanda eléctrica prevista, (b) % de la capacidad de acceso libre de la red (REE; «0 MW libres: no cabe» en Madrid, Navarra y Ceuta), (c) % del agua distribuida (INE 2024). Acierto del % eléctrico 96,1 %.

![[18_impacto_socioeconomico.png]]
**Impacto socioeconómico (E39-E41, 18/11/2026).** Tablas input-output 2022 del INE: (a) empleo de la obra por producto (3.402 empleos-año), (b) empleo de un año de operación (60 directos en azul + 217 en proveedores), (c) VAB directo / PIB de las 15 provincias donde más pesa.

![[20_atraccion_empresarial.png]]
**Atracción empresarial (E42, 18/11/2026).** Sociedades mercantiles creadas al año por cada 10.000 habitantes: últimos 12 meses (azul) y próximos 12 (naranja). Acierto del total anual 93,4 % / 92,6 %.

## Medio y largo plazo (10 años)

![[16_medio_plazo_10_anios.png]]
**Medio plazo: clima y agua a 10 años (A3, 18/11/2026).** (a) Temperatura media anual de España (media de las 52 capitales, NASA POWER desde 1981): real, lo que se habría previsto desde 2015 (test, punteado) y previsión a 2035 con su intervalo (97,7 % / 94,8 %). Se ve que el modelo se quedó corto con el calentamiento de 2016-2025. (b) Reserva media de los embalses por ámbito: últimos 10 años y próxima década (media de la década 91,1 % / 86,6 %).

![[07_demanda_nacional_10_anios.png]]
**Demanda nacional a 10 años** (backtesting 97,3 %).

![[19_escenarios_demanda.png]]
**Escenarios de demanda (P5, 18/11/2026).** (a) Tendencial con su intervalo y escenarios con el 25, 50 y 100 % de la red otorgada por REE, más el techo con lo pedido. (b) Red otorgada y en trámite frente a la demanda de cada comunidad (Aragón 243 %).

![[21_estacionariedad_demanda.png]]
**Estacionariedad y diferencias (I51, I52, 18/11/2026).** Demanda de Madrid en nivel, logaritmo, diferencia estacional y doble diferencia, con la media de cada año ± una desviación y el p-valor del test ADF: solo la doble diferencia es estacionaria.

## Comparación de modelos

![[03_error_por_horizonte.png]]
**Error por horizonte** de cada modelo y serie (el elegido en naranja, el resto en gris).

![[04_comparacion_modelos.png]]
**Comparación de modelos**: error a 1 año en validación y en test.

![[08_control_acierto.png]]
**Control de acierto** de todos los modelos frente al requisito D8 (85 % ≤ acierto < 99,9 %). Desde el 18/11 incluye también los modelos a 10 años del clima, el consumo y el agua.

## prob_cpd y modelos iniciales

![[roc_prob_cpd.png]]
**Curva ROC** fuera de pliegue de los modelos de `prob_cpd`. Desde el 18/11/2026: el elegido (población + comunidad con target encoding, AUC 0,92) en naranja grueso, el baseline de solo población en azul y el resto en gris; leyenda debajo.

![[prob_cpd_provincias.png]]
**prob_cpd por provincia**, matriz de confusión y métricas con el umbral elegido.

![[prevision_demanda_test.png]]
**Demanda a 1 mes** (primer modelo, test).

![[prevision_precio_luz.png]]
**Primer modelo del precio de la luz** (ficha del modelo).

## Capturas del mapa

![[mapa_precio_59_y_renovables_84_8.png]]
**Mapa (18/11/2026):** gráfico del precio con el aviso de orientativo y gráfico de las renovables con su acierto con un decimal.

![[mapa_precio_59_y_renovables_redondeo_85.png]]
**Mapa antes del arreglo del redondeo:** «acierta un 85 %, por debajo del mínimo del 85 %».

![[mapa_icono_no_viable_antes.png]]
**Icono de «No viable» antes del cambio** (barras grises cruzadas por una raya roja); ahora es «sin cobertura»: barras vacías y un distintivo rojo con ×.


![[mapa_medio_plazo_zaragoza.png]]
**Mapa (18/11/2026), ficha de Zaragoza, bloque «Clima y agua»:** línea nueva «A 10 años (2035)»: temperatura media 16,1 °C (15,5-16,9 °C) frente a 15,7 °C de media en 2016-2025, PUE 1,46, reserva media de los embalses del Ebro en la década 69 %, y los aciertos de test (temperatura 94,8 %, agua media de la década 86,6 %). Los 17,0 °C de «temperatura media anual» son los últimos 12 meses (año caluroso); no es una contradicción.

![[mapa_impacto_local_zaragoza.png]]
**Mapa (18/11/2026), ficha de Zaragoza:** línea «Impacto en su comunidad (12 meses)»: 4,4 % de la electricidad (como 61.300 habitantes), 82 % de la capacidad libre de la red (89 MW), 0,18 % del agua (como 2.470 habitantes).


![[mapa_socioeconomico_soria.png]]
**Mapa (18/11/2026), ficha de Soria, bloque «Inversión, red y mercado»:** línea «Empleo y economía (INE, tablas input-output)»: obra 3.402 empleos-año (295 M€ del CAPEX se quedan en España), operación 60 directos + 217 en proveedores al año, VAB del CPD = 1,54 % del PIB de la provincia (2024).

![[mapa_atraccion_empresarial_malaga.png]]
**Mapa (18/11/2026), ficha de Málaga:** líneas «Empleo y economía» y «Atracción empresarial: 47,0 sociedades nuevas al año por cada 10.000 habitantes (+4,9 %)».
