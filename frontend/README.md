# Frontend · Mapa de viabilidad de un CPD en España

Mapa interactivo de España para el Proyecto 3. Cada provincia se pinta según la **rentabilidad** de construir allí
un CPD (centro de datos): verde = alta, amarillo = media, naranja = baja, rojo = no rentable, rayado = sin datos.
Pulsas una provincia, el mapa entra en ella (con sus municipios reales) y el panel muestra la clase, VAN, ROI,
recuperación, viabilidad, luz, clima, agua, inversión, mercado y los motivos. Precio de la luz **en directo** (Red
Eléctrica) y tiempo actual de cada capital (Open-Meteo).

![Vista nacional](.impeccable/review/desktop.png)

## Cómo ejecutarlo

Requisitos: Node.js 20 o superior (probado con Node 24).

```powershell
cd frontend
npm install
npm run dev
```

Se abre en http://localhost:5173. No hace falta ninguna clave de API.

| Comando | Qué hace |
| --- | --- |
| `npm run dev` | Servidor de desarrollo |
| `npm run build` | Comprueba tipos y genera `dist/` (estático, se puede abrir con cualquier servidor web) |
| `npm run preview` | Sirve la versión de `dist/` |
| `npm test` | Tests (vitest): el recálculo en TypeScript da las mismas cifras que el modelo de Python |
| `npm run data` | Regenera `public/data/provincias_simuladas.json` (52 provincias, datos reales) y `viabilidad.json` (demostración) con el modelo de Python |
| `npm run geo` | Regenera los límites de provincias y municipios (`public/data/*.geojson`) |

## Cómo se usa

- **Vista de España:** el color de cada provincia es su clase de rentabilidad. Además del color, cada clase lleva un
  icono de barras (3 = alta, 2 = media, 1 = baja, cruzado = no rentable) y su nombre, para leerse también con
  daltonismo o en blanco y negro. El panel muestra el reparto en una barra y la lista agrupada por clase (ordenada
  por VAN); las provincias sin datos quedan plegadas al final.
- **Pulsar una provincia** (en el mapa, en la lista o en el recuadro de Canarias) hace zoom y abre su ficha.
  Dentro se ven sus municipios reales; pasar el ratón muestra el nombre y la superficie.
- **Volver:** botón *Toda España* o tecla `Esc`. Cada vista tiene su enlace (`#/provincia/28`).
- **Teclado:** la lista es navegable con `Tab` y tiene buscador; el mapa admite flechas y `+`/`−`.
  Con *reducir movimiento* activado en el sistema no hay animaciones de vuelo ni de números.

### Paleta de rentabilidad

`#40b97a` alta · `#dcbc55` media · `#e47b2f` baja · `#b8383f` no rentable, sobre el fondo `#111214`.
Validada con el script de la skill *dataviz* (`validate_palette.js --mode dark --pairs all`): separación para
daltonismo ΔE ≥ 11 entre cualquier par, visión normal ΔE ≥ 15,2 y contraste ≥ 3:1 con el fondo. El color solo se
usa para la rentabilidad; el resto de la interfaz va en tinta cálida.

## De dónde sale cada dato

### Las 52 provincias: simulación con datos reales

`npm run data` ejecuta también `scripts/simular_provincias.py`: toma los datos **reales** de cada provincia
(`data/curated/provincias_actual` y los últimos 12 meses de `panel_provincia_mes`) y los pasa por el **mismo modelo
determinista** del proyecto (`cpd.scoring.evaluar()` y `cpd.simulator`, sin modificarlos y sin entrenar nada):

| Dato real de la provincia | Qué alimenta en el modelo |
| --- | --- |
| Temperatura media de 12 meses | PUE estimado → consumo → coste de la energía |
| Precio spot medio de 12 meses (nacional) | Coste de la energía, OPEX, VAN, ROI, recuperación |
| Estrés hídrico WRI (comunidad), reservas de los embalses | Filtro de agua (M6) y aviso de reservas bajas |
| Distancia al IXP más cercano | Latencia (M3) |
| Capacidad de acceso disponible (comunidad), subestaciones 220/400 kV | Red eléctrica (M1) |
| Humedad, días ≥ 35 °C, máxima mensual, población, paro, demanda de la comunidad | Sub-scores |

El resultado (`public/data/provincias_simuladas.json`) cubre las 52 provincias con estado, score, VAN, ROI,
recuperación, CAPEX, OPEX, PUE, latencia y motivos; si a una provincia le falta un dato (p. ej. embalses en Baleares,
Canarias, Ceuta y Melilla) se calcula con lo que hay y la ficha dice qué falta. Lo que solo existe por parcela (zona
inundable, Red Natura de la parcela, distancia a subestación, sismicidad en g, suelo) no se evalúa a escala
provincial. La **clase de rentabilidad es relativa**: «no viable» o VAN ≤ 0 → no rentable; el resto, tercios del VAN
(con los supuestos actuales todas las viables tienen VAN positivo, entre unos 20 y 26 M€). La interfaz muestra la
fecha de los datos. Test: `.venv\Scripts\python.exe -m pytest frontend/scripts -q`.

### Orden de las fuentes

Al arrancar, la app busca primero **`data/curated/predicciones_provincia.json`** (raíz del repositorio): una lista con un
objeto por provincia (`codigo_provincia`, `provincia`, `ccaa`, `rentabilidad_clase` = `alta | media | baja |
no_rentable`, `score_viabilidad`, `estado`, `van_eur`, `roi`, `payback_anos`, `capex_eur`, `opex_eur_anual`,
`precio_luz_actual_eur_mwh`, `precio_luz_previsto_eur_mwh`, `temp_media_anual_c`, `horas_free_cooling_anual`,
`reserva_hidrica_pct`, `estres_hidrico`, `prob_cpd`, `cpd_existentes`, `motivos`, `generado_en`; cualquier número
puede ser `null`).

- **Si existe**, el plugin de `vite.config.ts` lo sirve en desarrollo y lo copia a `dist/` al compilar; el mapa usa
  esos datos tal cual (lo ausente se muestra como «—» o no se muestra; nunca se rellena) y **no hay sello de
  demostración**. No hace falta `npm run data`. Para probar otro fichero: variable `PREDICCIONES_JSON`.
- **Si no existe**, usa la simulación de las 52 provincias (`public/data/provincias_simuladas.json`), sin sello.
- **Si tampoco existe**, se usa la demostración (`public/data/viabilidad.json`, generada con `npm run data`) con el sello
  *Datos de demostración*. Como esos datos no traen clase de rentabilidad, se aplica una **regla relativa y solo de
  demostración** (`src/data/prediccion.ts`): «No viable» → no rentable; el resto, por tercios de su VAN (alta, media,
  baja). No es un umbral económico.

| Dato | Origen | ¿Real? |
| --- | --- | --- |
| Límites de provincias y municipios, nº de municipios, superficie | Eurostat GISCO, LAU 2024 (`data/raw/municipios`) | **Real** |
| Clase, viabilidad, VAN, ROI, recuperación, CAPEX, OPEX, clima, agua, mercado, motivos | `data/curated/predicciones_provincia.json` | **Real** (cuando el fichero existe) |
| Estado, score, motivos, CAPEX, OPEX, VAN, ROI, payback, temperatura, estrés hídrico (respaldo) | Modelo del proyecto (`src/cpd/scoring.py` → `evaluar()`) sobre `data/demo/municipios_demo.csv` | **Sintético** (28 municipios con indicadores inventados pero plausibles; nombres, códigos INE y coordenadas reales) |
| Precio spot de la luz (cada 15 min, hoy y mañana), media del día | REData de Red Eléctrica, `mercados/precios-mercados-tiempo-real` | **Real, en directo** (nacional) |
| Demanda eléctrica peninsular (cada 5 min) | REData, `demanda/demanda-tiempo-real` | **Real, en directo** (nacional) |
| % renovable de ayer y t CO₂/MWh de la red | REData, `generacion/evolucion-renovable-no-renovable` y `generacion/no-renovables-detalle-emisiones-CO2` | **Real, en directo** (nacional) |
| Temperatura, humedad y viento ahora en cada capital | Open-Meteo (`/v1/forecast?current=…`, una sola llamada para las 52 capitales) | **Real, en directo** |

Los datos en directo llevan un punto y su hora («en directo 21:15»). Con la demostración hay un sello permanente
*Datos de demostración* arriba a la derecha y una nota al pie de cada ficha.

Las provincias sin datos **no tienen ninguna cifra inventada**: salen rayadas, con *Sin datos todavía*, sus datos
geográficos reales y el tiempo en directo de su capital.

### Datos en directo

- Se piden desde el navegador (REData y Open-Meteo permiten CORS, no hace falta proxy) y se refrescan solos:
  precio y demanda cada 5 min, mix cada 30 min, tiempo cada 10 min. Se pausan con la pestaña oculta.
- Precio y demanda son **nacionales (sistema peninsular)**: son los mismos para todas las provincias y así se indica.
- Si una fuente falla, se ve *SIN CONEXIÓN*, un mensaje claro y un botón *Reintentar*; las cifras económicas siguen
  usando el precio del modelo. Si falla una actualización posterior, se conserva el último dato bueno.
- Open-Meteo es gratuito para uso no comercial (como este proyecto académico).

### «Si todo el año la luz costara como hoy»

En la ficha de cada provincia con datos se recalcula la economía con la **media del precio spot de hoy** en lugar de
los 75 €/MWh de `config/settings.yaml`. Se usan exactamente las fórmulas de `simular_municipio()`
(`src/model/finanzas.ts`): solo cambia el precio; el 80 % del coste eléctrico se repercute al cliente, por eso el VAN
cambia menos que la factura. Un test comprueba que, con 75 €/MWh, el resultado es idéntico al de Python para los 28
municipios.

## Regenerar los datos

**Modelo (`public/data/viabilidad.json`).** Desde `frontend/`:

```powershell
npm run data
```

Usa el Python de `..\.venv` (o el de la variable `PYTHON`). Equivale a:

```powershell
..\.venv\Scripts\python.exe scripts\export_data.py
```

Cuando exista la tabla maestra real (mismas columnas que `municipios_demo.csv`), basta con:

```powershell
npm run data -- --csv ..\data\curated\tabla_maestra.csv
```

El mapa se actualiza solo: las provincias que entren en la tabla dejarán de salir rayadas, y el sello de datos de
demostración desaparece si ninguna fila de `origen_datos` es sintética.

**Límites (`public/data/provincias.geojson`, `contexto.geojson`, `municipios/*.geojson`).** Ya están generados y
versionados. Para rehacerlos hacen falta los datos raw (`scripts\descargar_datos_raw.ps1` en la raíz):

```powershell
npm run geo
```

Las provincias se obtienen disolviendo los 8.132 municipios LAU por los dos primeros dígitos de su código INE, así
encajan exactamente con sus municipios (Baleares y Canarias incluidas, que en NUTS-3 van por islas). Los municipios
de cada provincia se guardan en un fichero aparte (máx. ~250 KB) y solo se descargan al entrar en ella.

## Tecnología y por qué

- **Vite + React + TypeScript:** arranque inmediato, tipos estrictos para el contrato de datos con Python.
- **MapLibre GL JS (WebGL):** zoom y vuelo de cámara fluidos, estilos según los datos y estado *hover* por
  provincia y municipio, sin mapa base de terceros: **sin claves, sin teselas externas y funciona sin internet**
  (salvo los datos en directo).
- **mapshaper** (solo en desarrollo) para simplificar y disolver los límites oficiales.
- Tipografías autoalojadas (Martian Mono y Archivo, vía Fontsource), sin Google Fonts en tiempo de ejecución.

## Diseño

Minimalista y orientado al mapa: fondo casi negro, el color reservado a la rentabilidad, pocas líneas y mucho aire.
La información la cargan el mapa coloreado, tres números grandes (VAN, ROI, recuperación) y barras pequeñas; los
números entran girando (herencia del primer diseño de tablero de salidas). Pensado para leerse proyectado en la
defensa y de cerca en el portátil o el móvil. Contexto de producto en [PRODUCT.md](PRODUCT.md) y sistema visual en
[DESIGN.md](DESIGN.md).

## Estructura

```
frontend/
  index.html, vite.config.ts, tsconfig.json, package.json
  public/data/             viabilidad.json, provincias.geojson, contexto.geojson, municipios/<código>.geojson
  scripts/export_data.py   modelo de Python -> viabilidad.json
  scripts/run_export.mjs   lanza export_data.py con el Python del .venv
  scripts/build_geo.mjs    límites GISCO LAU 2024 -> GeoJSON simplificados
  src/App.tsx              estado, rutas (#/provincia/..), datos en directo
  src/data/prediccion.ts   lee predicciones_provincia.json o construye la demostración (con test)
  src/components/          MapaEspana, Ranking, Ficha, Franja, Leyenda, IconoClase, CanariasRecuadro, Piezas…
  src/live/                clientes de REData y Open-Meteo, sondeo con pausa y reintento
  src/model/               recálculo financiero (con test) y colores
```

## Pendiente / limitaciones

- Mientras no exista `data/curated/predicciones_provincia.json` se ve la **demostración sintética**: 28 municipios
  en 25 provincias; el resto aparece como *sin datos todavía*, y la clase de rentabilidad es relativa (tercios de VAN).
- Con datos reales solo hay cifras por provincia: los puntos de municipios analizados y el selector de municipio
  son exclusivos de la demostración.
- El recálculo con el precio de hoy es una ilustración («si todo el año fuera como hoy»), no una previsión.
- ESIOS y AEMET (más detalle, necesitan clave gratuita) no se usan.
