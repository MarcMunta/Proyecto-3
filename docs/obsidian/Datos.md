---
tags: [clase, proyecto-3, datos]
actualizado: 2026-11-18
---

# Datos

Volver a [[00 Índice]]. Detalle de tablas: `docs/datos/tablas_api.md`. Todo se descarga con `python -m cpd.fuentes.actualizar` y cada descarga queda en `data/raw/_registro_descargas.csv`.

## Fuentes de partida

INE (población, renta), Red Eléctrica (REData: demanda y generación por comunidad, precios), MITECO (embalses), WRI (estrés hídrico), NASA POWER y Open-Meteo (clima), OMIE, MIBGAS (gas), SEPE (paro), OpenStreetMap (subestaciones), PeeringDB (CPD e IXP), EMSC (terremotos), EEA (Natura 2000).

## Fuentes añadidas el 17/11/2026 (para explicar con datos reales por qué se elige un sitio)

| Dato | Fuente | Qué aporta | Dónde entra |
|---|---|---|---|
| Capacidad de red **otorgada** y **pendiente** para demanda | Red Eléctrica, CSV mensual de capacidad de acceso (`red_capacidad.py`) | Huella real de los grandes consumos que se están conectando. Aragón es la primera: 3.938 MW otorgados y 3.244 MW pendientes; el nudo de Calatorao tiene 650 MW (los del campus anunciado allí) | Score, bloque mercado/ecosistema |
| Cobertura renovable prevista | Modelo propio (generación renovable / demanda) | Energía verde de sobra: Extremadura 315 %, Castilla y León 241 %, Castilla-La Mancha 199 %, Aragón 170 % | Score, bloque energía |
| Precio del suelo urbano | Ministerio de Transportes, «Precios de suelo», tabla 4 (`suelo.py`), mediana de 4 trimestres | Coste relativo del suelo (León 52 €/m², Zaragoza 140, Madrid 398). Es suelo urbano, no industrial: **no entra en el CAPEX** | Score, bloque suelo |
| Latencia a los dos grandes nodos | PeeringDB (provincias con más IXP: hoy Madrid y Barcelona) + coordenadas | Cercanía a los dos mercados a la vez (Zaragoza la mejor: 4,1 ms) | Score, bloque conectividad |
| Peligrosidad sísmica oficial | BOE núm. 244 (11/10/2002), norma NCSE-02, anejo 1, hecha con el mapa del IGN (`norma_sismica.py`, se lee el PDF con `pypdf`) | Aceleración sísmica básica de 2.615 municipios. Por provincia, la de la capital (0,04 g si no aparece). Granada 0,23 g, Murcia 0,15, Alicante y Almería 0,14; Aragón ≤ 0,04 | Filtro sísmico (≥ 0,16 g) y bloque riesgos |

## Datos añadidos el 18/11/2026 (para el precio de la luz)

Ver [[Precio de la luz (historia)]].

| Dato | Fuente | Qué aporta | Dónde entra |
|---|---|---|---|
| Generación de España **por tecnología** (eólica, solar, hidráulica, nuclear, ciclo combinado, carbón y total), mensual | REData, la misma descarga de generación por comunidad que ya se hacía, sumada a nivel nacional (`ree.generacion_nacional_detalle`) | El «tiempo» (viento, sol, lluvia) y el peso del gas en el mix de cada mes | Tabla `data/curated/tablas/generacion_nacional_detalle.csv` → modelos del gas y del tiempo y precio estructural |
| Generación por comunidad y tecnología | REData (misma descarga) | Suma de tecnologías en la generación renovable | `data/curated/tablas/ccaa_generacion_tecnologia.csv` |
| Futuros del gas (M+1, Q+1, Y+1) | MIBGAS (ya estaba en la tabla del gas) | Lo que el mercado esperaba del gas en cada origen | Candidato `futuros_gas` |

No ha hecho falta descargar nada nuevo: las tablas se han construido con la caché raw de REData (`data/raw/api/ree/generacion_ccaa`).

## Datos añadidos el 18/11/2026 (para el medio plazo, A3)

| Dato | Fuente | Qué aporta | Dónde entra |
|---|---|---|---|
| Temperatura media **mensual** por provincia desde **1981** | NASA POWER, endpoint mensual (`nasa_power.temperatura_mensual_larga`), misma fuente y mismo punto que la diaria | 45 años de historia para validar una previsión a 10 años (la diaria empieza en 2015). Coincide con la diaria: 0,003 °C de diferencia media en 6.864 meses comunes | `data/curated/tablas/clima_mensual_largo.csv` → `medio_plazo.py` (temperatura → PUE → consumo a 10 años) |
| Reservas de los embalses desde 1988 | MITECO (ya estaba) | Agua media de la próxima década por ámbito | `medio_plazo.py` |

## Datos añadidos el 18/11/2026 (para el impacto local, P2)

| Dato | Fuente | Qué aporta | Dónde entra |
|---|---|---|---|
| Agua de la red pública por comunidad (suministrada, registrada y distribuida, pérdidas), bienal 2014-2024 | INE, «Estadística sobre el suministro y saneamiento del agua», tabla 53447 (`ine.agua_ccaa`) | Consumo de agua local (E14 por comunidad) para medir el peso del CPD. La suma de comunidades da el total de España. Ceuta y Melilla juntas | `data/curated/tablas/agua_ccaa.csv` → `impacto_local.py` |

## Datos añadidos el 18/11/2026 (para el impacto socioeconómico, E39-E41)

| Dato | Fuente | Qué aporta | Dónde entra |
|---|---|---|---|
| Tablas Input-Output 2022: producción, VAB, importaciones, oferta y empleo ETC de 65 productos, e inversa interior de Leontief | INE, Contabilidad Nacional Anual (Revisión 2024), `cne_tio_22.xlsx` (`ine_tio.py`) | Empleo y VAB que genera cada euro de demanda, directo e indirecto; cuota de importación real | `tio_ramas.csv`, `tio_leontief_interior.csv` → `socioeconomico.py` |
| PIB por provincia (precios corrientes), 2024 | INE, Contabilidad Regional, tabla 82284 (`ine.pib_provincias`) | Peso del VAB del CPD en la economía de cada provincia (no hay PIB municipal) | `pib_provincia.csv` → `socioeconomico.py` |

## Datos añadidos el 18/11/2026 (para la atracción empresarial, E42)

| Dato | Fuente | Qué aporta | Dónde entra |
|---|---|---|---|
| Sociedades mercantiles constituidas por provincia y mes, 2008-2025 | INE, Estadística de Sociedades Mercantiles, tabla 6295 (`ine.sociedades_provincias`) | Dinamismo empresarial de cada provincia; la suma da el total nacional | `sociedades_provincia.csv` → `empresas.py` |

### Datos que harían falta y no hay en abierto

- **Precio del CO2** (derechos de emisión EU ETS): EEX es de pago; la EEA solo publica emisiones, no precios. Es la pieza que más falta en el precio de la luz.
- **Futuros de la luz** (OMIP): solo en su web, y extraerlos choca con sus condiciones de uso. Decisión: no se usan ([[Decisiones]]).
- Demanda horaria e interconexiones con Francia y Portugal: no se han integrado (el precio es mensual).

## Dependencias nuevas

- `xlrd` (leer el XLS del Ministerio de Transportes) y `pypdf` (leer el PDF del BOE), en `requirements.txt`.

## Limitaciones conocidas

- REData publicó la demanda de jul-ago 2026 sin el saldo de intercambios: se filtra en el curado (`calidad.py`).
- Red Eléctrica solo publica el CSV del último mes: no hay serie para un modelo de capacidad de red.
- Capacidad de red y renovables son por comunidad; las provincias heredan el valor.
- El IGN actualizó su mapa de peligrosidad en 2012-2015, pero sin tabla abierta por municipio: se usa la NCSE-02 (norma vigente).
- El mix de generación por comunidad solo existe desde 2015: no permite validar emisiones a 10 años.
- La generación nacional por tecnología se corta en el último mes que tienen **todas** las comunidades, para no sumar meses incompletos.
