# Fuentes en tiempo real: qué se puede recopilar y cómo

Análisis del **13/11/2026** sobre todas las fuentes del proyecto (las 12 ya descargadas el 09/11/2026 y las
pendientes del catálogo). Cada fuente se ha **probado en vivo** con `src/ingesta/sondeo_fuentes.py`, que pide
una muestra pequeña y comprueba si responde, si pide clave y la fecha del dato más reciente. El resultado
completo está en [`sondeo_fuentes.csv`](sondeo_fuentes.csv); el script se puede repetir en cualquier momento.

Resultado: **21 de 24 fuentes accesibles ahora mismo**; 2 piden una clave gratuita y 1 falla.

## 1. Clasificación

### Tiempo real (minutos u horas), sin clave — listas para usar

| Fuente | Datos | Frecuencia comprobada | Último dato en la prueba | Uso en el proyecto |
|---|---|---|---|---|
| Red Eléctrica · REData `demanda/demanda-tiempo-real` | Demanda peninsular real, prevista y programada | **Cada 5 min** (288 valores al día) | 13/11 19:00 (12 min de retraso) | M2, panel "ahora mismo" |
| Red Eléctrica · REData `mercados/precios-mercados-tiempo-real` | Precio spot y PVPC | Spot **cada 15 min, incluye mañana**; PVPC horario | Hasta 14/11 23:45 | M2, M7: coste de la energía |
| OMIE | Precio marginal del mercado diario (fichero `marginalpdbc`) | Diaria; el de mañana se publica a mediodía | Fichero del 14/11, 96 periodos de 15 min | M7, contraste del precio de REE |
| Open-Meteo `forecast` | Temperatura, humedad, viento actuales y previsión | Cada 15 min | 13/11 19:00 | M6 (refrigeración), panel por provincia |
| IGN · Sismología (RSS) | Últimos terremotos con magnitud y coordenadas | Continua | 13/11 07:30 | M5 (riesgo), capa del mapa |
| OpenStreetMap · Overpass | Subestaciones de 220/400 kV (896 en España) | Continua | Datos de hace minutos | M1; **intermitente** (ver §3) |

### Tiempo real con clave gratuita

| Fuente | Datos | Qué pasa sin clave | Cómo conseguirla |
|---|---|---|---|
| Red Eléctrica · ESIOS | Más de 1.900 indicadores en minutos (demanda por sistema, generación, precios, emisiones) | Devuelve los metadatos pero **no los valores** (HTTP 403) | Token gratuito pidiéndolo por correo a Red Eléctrica (consultasios@ree.es) |
| AEMET OpenData | Observación horaria de estaciones oficiales | Responde HTTP 200 con el **cuerpo vacío** | Clave gratuita por correo en opendata.aemet.es |

Las dos claves van en `.env` (`ESIOS_TOKEN`, `AEMET_API_KEY`; ya están en `.env.example`). REData y
Open-Meteo cubren casi todo lo que necesitamos de ellas, así que **no son imprescindibles** para empezar.

### Diaria

| Fuente | Datos | Último dato | Uso |
|---|---|---|---|
| REData `generacion/estructura-generacion` | Generación por tecnología (15 series) | Hoy, 00:00 | M2, M9 |
| REData `generacion/evolucion-renovable-no-renovable` | % renovable | Hoy, 00:00 | M9 (CO₂ del CPD) |
| REData `generacion/no-renovables-detalle-emisiones-CO2` | Emisiones por tecnología | Hoy, 00:00 | M9: factor de emisión real de la red |
| REData `balance/balance-electrico` | Balance nacional (21 series) | Hoy, 00:00 | M2 |
| Open-Meteo `archive` (ERA5) | Temperatura horaria histórica | Hasta ayer | M6: **horas de free cooling** por municipio |
| Geofabrik | Extracto completo de OpenStreetMap de España (1,5 GB) | Hoy, 01:24 | Alternativa estable a Overpass |

### Semanal y mensual

| Fuente | Frecuencia | Último dato | Estado de nuestra copia del 09/11 |
|---|---|---|---|
| MITECO · Boletín Hidrológico (embalses) | Semanal | 10/11/2026 | **Desactualizada**: hay una versión posterior |
| SEPE · Paro por municipio | Mensual (primeros días del mes) | Octubre 2026 | **Desactualizada**: tenemos hasta septiembre |
| Red Eléctrica · Capacidad de acceso de demanda | Mensual | 03/11/2026 | Al día |

### Continua pero estructural (cambia poco)

| Fuente | Datos | Comprobado |
|---|---|---|
| PeeringDB `fac` | Centros de datos existentes | 72 en España (última ficha editada el 16/10) |
| PeeringDB `ix` | Puntos neutros de Internet | 18 en España |

Sirven para M3 (latencia) y para la **etiqueta del modelo**: municipios donde ya hay CPD.

### Anual o estática (no son de tiempo real)

INE Padrón (última publicación 11/12/2025), INE Atlas de Renta (19/10/2026), INE Censo 2021,
Eurostat GISCO, EEA Natura 2000 (servicio de mapas accesible), WRI Aqueduct, diccionario de municipios.
Se descargan una vez y se refrescan cuando se publica la edición nueva.

## 2. Qué es "tiempo real" para este proyecto

La decisión de dónde poner un CPD se toma con datos **estructurales** (suelo, red eléctrica, riesgos, clima
medio), que cambian poco. El tiempo real aporta otra cosa:

- **Coste de la energía actualizado**: el precio spot de hoy y de mañana recalcula el OPEX y el VAN.
- **Estado del sistema eléctrico**: demanda y % renovable de ahora, para el CO₂ real del CPD.
- **Clima actual** por provincia, para enseñar el efecto en la refrigeración.
- **Eventos**: terremotos recientes como capa informativa del mapa.

El precio y la demanda eléctrica son **nacionales (sistema peninsular)**, no por provincia. Baleares, Canarias,
Ceuta y Melilla tienen sistemas propios en REData.

## 3. Problemas encontrados

| Fuente | Problema | Solución |
|---|---|---|
| OpenStreetMap · Overpass | Las tres instancias públicas fallaron en la primera prueba (502, 504 y tiempo agotado); en la segunda respondió en 42 s | Para el dato estructural (subestaciones), usar el extracto diario de **Geofabrik** o guardar el resultado de Overpass y no consultarlo en cada uso |
| MITECO · SNCZI (zonas inundables) | Certificado SSL no válido en `wms.mapama.gob.es` | No desactivar la verificación SSL. Descargar las capas desde el centro de descargas del MITECO o datos.gob.es |
| ESIOS y AEMET | Sin clave no dan valores | Pedir las claves gratuitas, o usar REData y Open-Meteo |
| Datadis (consumo por municipio) | Requiere autorización de cada titular del suministro | No viable para el proyecto |
| Copernicus CDS (ERA5) | Requiere cuenta | Open-Meteo `archive` sirve ERA5 sin cuenta |

## 4. Recomendación de recogida

| Frecuencia | Fuentes |
|---|---|
| Cada hora (o al abrir el mapa) | REData demanda y precios · Open-Meteo actual |
| Diaria | REData generación, % renovable, CO₂ y balance · OMIE · IGN terremotos · Open-Meteo histórico |
| Semanal | MITECO embalses |
| Mensual | SEPE paro · Red Eléctrica capacidad de acceso · PeeringDB |
| Anual | INE, GISCO, Natura 2000, WRI Aqueduct, Censo |

Normas para recogerlas bien:

- **Guardar todo en `data/raw/`** con fecha y anotarlo en `_registro_descargas.csv` (ya lo hace `utils.descargar`).
- **Peticiones pequeñas y espaciadas**: REData por tramos cortos de fechas; PeeringDB y Overpass tienen límites
  por minuto; Open-Meteo es gratuito solo para uso no comercial y admite varias coordenadas en una petición.
- **Reintentos con espera** y aviso claro si una fuente falla (no rellenar con datos inventados).
- **Ejecutar `sondeo_fuentes.py` antes de cada ingesta** para saber qué fuentes están caídas o tienen dato nuevo.
