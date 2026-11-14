---
name: "Mapa de rentabilidad de centros de datos"
description: "Mapa de España de viabilidad y rentabilidad de un centro de datos: el color solo significa rentabilidad."
colors:
  suelo: "#111214"
  superficie: "#17181b"
  contexto: "#1b1c1f"
  linea: "#26282c"
  texto: "#f1ecdf"
  texto-2: "#b6b0a3"
  texto-3: "#8f8a80"
  alta: "#40b97a"
  media: "#dcbc55"
  baja: "#e47b2f"
  no-rentable: "#b8383f"
  sin-datos: "#2b2d32"
  rayado: "#4f525a"
typography:
  cifra:
    fontFamily: "Martian Mono Variable, ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "clamp(1.4rem, 2.2vw, 2.1rem)"
    fontWeight: 560
    lineHeight: 1
    letterSpacing: "normal"
    fontVariation: "'wdth' 82"
  titulo-ficha:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "2.1rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  titulo-bloque:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 700
    lineHeight: 1.45
    letterSpacing: "normal"
  body:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "0.92rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  etiqueta:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
rounded:
  sm: "3px"
  radio: "6px"
  lg: "10px"
  pill: "999px"
spacing:
  xs: "0.35rem"
  sm: "0.6rem"
  md: "0.9rem"
  lg: "1.6rem"
components:
  volver:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.7rem 0.35rem 0.55rem"
  volver-hover:
    backgroundColor: "{colors.linea}"
  fila:
    textColor: "{colors.texto}"
    rounded: "{rounded.radio}"
    padding: "0.42rem 0.5rem 0.42rem 1.75rem"
  fila-hover:
    backgroundColor: "{colors.superficie}"
  pista:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
    rounded: "{rounded.radio}"
    padding: "0.5rem 0.7rem"
  sello:
    textColor: "{colors.texto-2}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.6rem"
  barra-pista:
    backgroundColor: "{colors.linea}"
    rounded: "{rounded.sm}"
    height: "6px"
  clase:
    rounded: "{rounded.lg}"
    padding: "0.95rem 1.1rem"
---

# Design System: Mapa de rentabilidad de centros de datos

<!-- Escrito a partir del código construido (src/styles.css, src/components, src/model/colores.ts) el 2026-11-14. Sustituye al sistema anterior («Tablero de Salidas», split-flap con casillas). Los tokens del frontmatter son normativos. -->

## Overview

**Creative North Star: "El mapa de una sola señal"**

El mapa es el protagonista: ocupa unos 64 % del ancho en escritorio (`minmax(0, 1.75fr)` frente a `minmax(23rem, 1fr)`). Cada provincia se lee de un vistazo por su color de rentabilidad, y ese color no significa nada más. El resto de la interfaz es tinta cálida sobre un negro casi puro: pocas líneas, mucho aire, cifras grandes en Martian Mono y explicación en Archivo.

Lo que el sistema rechaza, confirmado en el build: paneles de tarjetas con bordes, etiquetas de cabecera en mayúsculas, sombras de decoración y color de acento. Las cifras cambian con un giro corto de carácter, como un panel de salidas, pero sin casillas ni fondos: el giro es el único gesto de movimiento que acompaña al dato.

La honestidad es parte del sistema: un dato en directo lleva su hora y su fuente; los datos de demostración se marcan con un sello y la clase se etiqueta como relativa; una clase nunca aparece sin sus motivos; el precio y la demanda de la luz se rotulan como nacionales (peninsulares), nunca como de provincia.

**Key Characteristics:**
- Negro casi puro en dos escalones tonales (`suelo`, `superficie`) y hairlines `linea` de 1 px.
- Cuatro colores de rentabilidad (`alta`, `media`, `baja`, `no-rentable`) reservados a la codificación de clase.
- Un icono ordinal de barras por clase: la forma dice la clase además del color.
- Rayado diagonal = sin datos, y solo eso.
- Cifras en Martian Mono que giran al cambiar; prosa en Archivo.
- Radios pequeños (3 a 10 px) y píldoras para acciones.

## Colors

Negro casi puro con tinta cálida en tres niveles. Cuatro colores de rentabilidad que solo codifican clase; todo lo demás es neutro.

### Primary
- **Tinta cálida** (`texto` #f1ecdf): texto principal, cifras, contorno de la provincia elegida (2,4 px) y del hover (1,5 px), relleno de la barra de la fila de comparación en directo, fondo de la opción activa de los municipios (con texto `suelo`) y contorno de foco (2 px, desplazado 2 px).

### Secondary (clase de rentabilidad, reservada)
- **Alta** (`alta` #40b97a): verde. Icono de tres barras encendidas.
- **Media** (`media` #dcbc55): ocre amarillento. Icono de dos barras.
- **Baja** (`baja` #e47b2f): naranja. Icono de una barra.
- **No rentable** (`no-rentable` #b8383f): rojo. Icono sin barras encendidas y con una cruz.

Estos cuatro colores aparecen solo en: relleno de provincias y Canarias en el mapa, leyenda del mapa, insignia de clase de la ficha, barra de reparto del ranking, puntos de los municipios analizados, y el icono de clase en cualquier sitio donde aparezca. La paleta se validó con `validate_palette.js` (skill dataviz) sobre `suelo` #111214: ΔE de daltonismo ≥ 11, ΔE de visión normal ≥ 15,2, contraste ≥ 3:1. La comprobación de banda de luminosidad queda fuera de alcance; el icono y el nombre de clase la compensan.

### Neutral
- **Suelo** (`suelo` #111214): fondo de página, fondo del mapa, base de la leyenda y de los recuadros sobre el mapa (con transparencia), tinta sobre el texto invertido de la selección.
- **Superficie** (`superficie` #17181b): fondo del tooltip, de las filas en hover, de la píldora de volver en la ficha y de la ficha sin datos.
- **Línea** (`linea` #26282c): hairlines de 1 px: pista de las barras, subrayado del buscador, borde de los municipios, barra de desplazamiento y hover de los botones de volver.
- **Tinta 2** (`texto-2` #b6b0a3): texto secundario, etiquetas, unidades, motivos, la marca «en directo» y el mensaje «sin conexión».
- **Tinta 3** (`texto-3` #8f8a80): notas, ejes del gráfico, marcadores de los campos, créditos y borde del sello de demostración.
- **Sin datos** (`sin-datos` #2b2d32) y **Rayado** (`rayado` #4f525a): el patrón de sin datos es el rayado de `rayado` sobre `sin-datos`, a 45°.
- **Contexto** (`contexto` #1b1c1f): Portugal y Francia en el mapa. No tiene variable CSS: vive solo en `src/model/colores.ts`, que pinta el mapa WebGL.

### Named Rules
**The Class Color Is Profitability Rule.** La paleta de rentabilidad codifica clase y nada más: mapa, leyenda, insignia, reparto, puntos de municipios e iconos. Ningún botón, enlace, cabecera ni estado de conexión toma un color de clase.

**The Warm Ink Rule.** Todo lo que no es rentabilidad va en tinta cálida (`texto`, `texto-2`, `texto-3`) sobre `suelo`. La marca «en directo» es neutra (su punto es `texto-2`); el dato en vivo no tiene color propio.

**The Hatching Means No Data Rule.** El rayado indica ausencia de dato y no se usa para otra cosa: provincias sin modelo en el mapa, Canarias, la muestra de la leyenda, el tramo «sin datos» de la barra de reparto y el resumen de provincias sin datos.

**Sincronía.** `src/model/colores.ts` (lo que pinta el mapa WebGL) repite los valores de `:root` en `styles.css`; si se cambia uno, se cambia el otro. `styles.css` es la fuente normativa.

## Typography

**Fuente de cifras:** Martian Mono Variable (`--f-num`), con el eje de anchura `wdth` a 78–82 % (`font-stretch`). Fallback: ui-monospace, Cascadia Mono, Consolas, monospace.
**Fuente de prosa:** Archivo Variable (`--f-texto`). Fallback: system-ui, Segoe UI, sans-serif.

Ambas se cargan desde `@fontsource-variable` (martian-mono y archivo, variante `wdth.css`) en `src/main.tsx`.

**Character:** cifras de panel en mono condensado y prosa en sans legible. La mono se reserva a cifras, códigos y la tecla Esc; la prosa, los nombres y las etiquetas van siempre en Archivo.

**Escala raíz:** `html { font-size: clamp(15px, 0.42vw + 10.5px, 19px) }`. Todos los `rem` de este documento escalan con la pantalla.

### Hierarchy
- **Cifra grande** (Martian Mono, 560, `clamp(1.4rem, 2.2vw, 2.1rem)`, line-height 1, `wdth` 82): VAN, ROI y recuperación de la ficha. 1.3 rem a 1100 px y 1.1 rem a 560 px. Su unidad va en Archivo 0.85 rem, `texto-2`.
- **Título de ficha** (Archivo, 700, 2.1 rem, line-height 1.15, tracking -0.01em): nombre de la provincia. 1.7 rem a 560 px. El título del ranking («Rentabilidad de un CPD por provincia») es 1.6 rem.
- **Título de bloque** (Archivo, 700, 1.05 rem): Luz, Clima y agua, Inversión y mercado, Por qué.
- **Clase** (Archivo, 700, 1.45 rem): nombre de la clase en la insignia.
- **Prosa** (Archivo, 400, 0.92 rem, line-height 1.45): motivos, explicación y fuente. Medida máxima 68 ch. Subtítulos y avisos van en 0.86–0.9 rem.
- **Etiqueta** (Archivo, 400, 0.8 rem, `texto-2` o `texto-3`): etiquetas de pares, la etiqueta «Luz nacional ahora», notas, ejes y créditos. Es el tamaño mínimo de texto del sistema. Los ejes del gráfico de precio se dibujan en unidades SVG de 12 px y escalan con el gráfico.
- **Cifra de fila y de pares** (Martian Mono, 560, `wdth` 82, 0.85–1.15 rem): valores de las filas del ranking, de los pares y de la barra de comparación.

### Named Rules
**The Numerals Are Mono Rule.** Las cifras, los códigos y la tecla Esc van en Martian Mono; la prosa, los nombres de provincia y las etiquetas van en Archivo. No se escribe prosa en mono.

## Layout

**Escena de escritorio:** la aplicación ocupa `100dvh`. Arriba, la cabecera a todo el ancho; debajo, una escena de dos columnas: el mapa en `minmax(0, 1.75fr)` y el panel de detalle en `minmax(23rem, 1fr)` (≈ 64 / 36). El mapa llena su columna (`position: absolute; inset: 0` dentro de un marco con margen de 0,75 rem a la izquierda y abajo). El panel hace su propio scroll; el mapa no.

**Cabecera:** una línea flexible con la marca (sigla «CPD» y título), la luz nacional en directo a la derecha y, solo con datos de demostración, el sello. Padding 0,8 rem / 1,25 rem.

**Panel:** padding 1,75 rem (1,75 rem arriba, 1,25 rem abajo). Entre bloques de la ficha y entre secciones del ranking hay 1,6 rem; dentro de un bloque, 0,85 rem.

**Ritmo de espaciado:** no hay cuadrícula de 4 u 8 px. Los valores recurrentes son 0,35 / 0,5 / 0,6 / 0,75 / 0,85 / 0,9 / 1 / 1,6 rem. Los tokens `spacing` del frontmatter son esos pasos.

### Breakpoints
- **1100 px:** la escena pasa a `minmax(0, 1.4fr)` y `minmax(20rem, 1fr)`; el panel reduce su padding a 1,4 rem / 1,25 rem; las cifras grandes bajan a 1,3 rem.
- **900 px:** la escena y la aplicación pasan a bloque (altura automática); el marco del mapa mide `clamp(20rem, 96vw, 62svh)` con margen lateral de 0,5 rem; la cabecera se parte y la marca ocupa todo el ancho; el panel deja de tener scroll propio; la tecla Esc se oculta. En el móvil, elegir una provincia sube la vista al mapa.
- **560 px:** la leyenda del mapa desaparece (la barra de reparto del panel ya lleva iconos); la marca baja a 0,98 rem; Canarias mide 8,5 rem; los puntos de municipios (solo en la vista nacional de la demostración) bajan a 8 px; las cifras grandes bajan a 1,1 rem; las filas de comparación pasan a dos columnas con la barra a ancho completo.

### Named Rules
**The Phone Goes To The Map Rule.** En pantallas de 900 px o menos, elegir una provincia sube la vista al mapa, porque el zoom es la respuesta y el panel queda debajo.

**The Fluid Type Rule.** El texto escala con la raíz fluida; no se fijan píxeles para texto. Las dimensiones fijas son iconos de clase (13–34 px), puntos del mapa, la muestra de rayado, la barra de 6 px y los marcadores de los municipios.

### Vistas: nacional y provincia

- **Vista nacional:** el mapa muestra todas las provincias por clase, la leyenda abajo a la derecha, Canarias abajo a la izquierda; el panel muestra el ranking.
- **Vista de provincia:** el mapa hace zoom y muestra los puntos de municipios con su etiqueta; la leyenda y Canarias desaparecen; el botón «Toda España» aparece arriba a la izquierda; el panel muestra la ficha.

## Elevation & Depth

Sistema plano por escalones tonales (`suelo` → `superficie`) y hairlines `linea` de 1 px. Las superficies se separan por tono o por línea, no por sombra. La única sombra difusa es la del tooltip del mapa. Los recuadros sobre el mapa (leyenda, Canarias, botón de volver) son fondos translúcidos de `suelo` (86 %) o de `superficie` (92 %), no elevaciones.

### Shadow Vocabulary
- **Tooltip del mapa** (`box-shadow: 0 10px 28px rgb(0 0 0 / 0.5)`): solo la pista que sigue al cursor sobre el mapa.
- **Anillo de punto** (`box-shadow: 0 0 0 2px #111214, 0 0 0 3.5px rgb(241 236 223 / 0.85)`): delimita los puntos de municipios sobre el mapa; en 560 px baja a 1,5 y 2,5 px. Es un contorno de lectura, no una sombra.

### Named Rules
**The Tonal Depth Rule.** Una superficie se distingue por su escalón tonal o su hairline. Solo la pista del mapa flota con sombra.

## Shapes

Radios observados, de menor a mayor: 2 px (muestra de rayado pequeña), 3 px (barras de progreso, reparto), 4 px (sigla de la marca, etiqueta de punto, muestra de rayado grande), 6 px (`--radio`: tooltip, leyenda, Canarias, filas, bloque de error, controles de MapLibre), 10 px (marco del mapa, insignia de clase) y 999 px (píldoras). Los bordes miden 1 px, en `linea` o, en el sello, discontinuos en `texto-3`.

**Formas recurrentes:**
- **Icono de clase:** tres barras de altura creciente (como la cobertura de un móvil). Encendidas según la clase: 3 alta, 2 media, 1 baja, 0 no rentable (con una cruz). Las barras apagadas son `#3b3d43`.
- **Muestra de rayado:** cuadrado con rayado a 45° (1,5 px de trazo cada 5 px).
- **Barra de progreso:** pista de 6 px con relleno de la misma altura y umbral de 2 px.

### Named Rules
**The Pill Is Action Rule.** Las acciones (volver, municipios, reintentar) y el sello de demostración van en píldora de 999 px. Los contenedores de datos van de 3 a 10 px.

**The Dashed Seal Rule.** El borde discontinuo se usa solo en el sello «Datos de demostración». Marca lo ficticio y no se reutiliza.

## Components

Cada componente se lee como una pieza del mapa o de la ficha, sin fondo decorativo. Los estados son de tono y de línea.

### Insignia de clase (`.clase`)
- **Forma:** radio 10 px, padding 0,95 rem / 1,1 rem, fondo mezclado: 15 % del color de la clase sobre `suelo` (`color-mix`).
- **Contenido:** icono de clase de 34 px, nombre de la clase (Archivo 700, 1,45 rem). Con datos de demostración, debajo, la nota «relativa · demostración» (0,8 rem, `texto-2`).
- **Sin datos (`.clase-sin`):** fondo `superficie`, muestra de rayado de 34 px, «Sin datos todavía» y una explicación de hasta 60 ch.

### Cifras grandes (`.heroes`)
- Tres columnas de igual anchura (VAN, ROI, recuperación). Etiqueta 0,8 rem en `texto-2`; cifra en Martian Mono; unidad («M€», «%», «años») en 0,85 rem `texto-2`.
- Sin dato: guion «—»; sin recuperación: «no se recupera» en 1 rem `texto-2`.
- Cada cifra gira al cambiar; ROI con 80 ms de retardo y recuperación con 160 ms.

### Barra (`.barra`)
- Etiqueta 0,88 rem `texto-2` a la izquierda; valor en Martian Mono 560 `texto` a la derecha.
- Pista de 6 px, radio 3 px, en `linea`; relleno en `texto-2`. La barra no toma color de clase.
- Umbral opcional: marca de 2 px en `texto` en la posición del umbral (estrés hídrico, 0,7). Lleva `role="meter"`.
- Nota opcional a 0,8 rem `texto-3`.
- Usos: viabilidad (0–100), probabilidad de instalación de un CPD, horas de free cooling, reserva hídrica, estrés hídrico.

### Comparativa (`.comparativa`)
- Filas en rejilla: etiqueta (`minmax(8.5rem, 1fr)`), pista de 6 px (`minmax(5rem, 1.4fr)`), valor en Martian Mono con unidad pequeña `texto-3`.
- Filas de modelo: relleno `texto-3`. Fila en directo (`es-vivo`): relleno `texto` y su marca «en directo» con hora.
- Con 560 px, dos columnas y la pista ocupa la fila inferior.

### Gráfico de precio (`.grafico-precio`)
- SVG de 6 rem de alto con 96 barras (una por cuarto de hora). Pasado `#5f5c55`, instante actual `texto`, futuro `#33353a`. Son valores fijos del gráfico, no tokens.
- Línea de referencia discontinua (5 4) en `texto-2`, 1,2 px, con el precio del modelo.
- Ejes 0/6/12/18 h en Martian Mono de 12 px, `texto-3`. Pie de 0,8 rem `texto-3`.

### Ranking por clase (`.ranking`)
- **Cabecera:** título 1,6 rem 700, subtítulo 0,9 rem `texto-2` (predicción con su hora, o «Demostración con datos sintéticos · N de M provincias»).
- **Reparto:** barra de 0,7 rem de alto, radio 3 px, con tramos proporcionales al número de provincias de cada clase en su color; el tramo «sin datos» va rayado. Bajo ella, la leyenda del reparto con icono, cifra en mono y nombre.
- **Buscador:** sin fondo; solo una línea inferior de 1 px en `linea` que pasa a `texto-2` al enfocarse; marcador en `texto-3`.
- **Grupos:** un grupo por clase en el orden alta, media, baja, no rentable. Encabezado 0,95 rem 650 con icono de 15 px, nombre y cuenta en Martian Mono a la derecha (`texto-3`). Dentro, provincias ordenadas por VAN.
- **Sin datos:** un bloque colapsado («Sin datos todavía», con muestra rayada y cuenta), que se abre al buscar.

### Fila de provincia (`.fila`)
- Botón de ancho completo, radio 6 px, padding 0,42 rem / 0,5 rem / 0,42 rem / 1,75 rem (el hueco izquierdo es para la sangría del grupo).
- Nombre en Archivo, una línea con elipsis; VAN en Martian Mono 0,85 rem `texto-2`.
- Hover y foco: fondo `superficie`. Al pasar el puntero o enfocar, la provincia se resalta en el mapa con su contorno.

### Leyenda del mapa (`.leyenda`)
- Esquina inferior derecha del mapa, solo en la vista nacional. Fondo `suelo` al 86 %, radio 6 px, texto 0,82 rem.
- Título «Rentabilidad» 0,8 rem 600 `texto-3`. Cuatro filas: icono de 14 px, nombre y cuenta en Martian Mono; la última fila, «Sin datos», con su muestra rayada de 14 px.
- Oculta a 560 px.

### Canarias (`.canarias`)
- Recuadro inset abajo a la izquierda del mapa, en la vista nacional. Ancho `min(12rem, 30vw)` (8,5 rem a 560 px). Fondo `suelo` al 86 %, radio 6 px.
- Las dos provincias se rellenan con su color de clase; sin datos, con rayado a -45° (paso de 5 u, trazo de 1 u). Foco y hover: contorno `texto` de 1,5 px.
- Leyenda «Canarias» a 0,8 rem `texto-3`. Pulsar una provincia vuela a su posición real.

### Tooltip del mapa (`.pista`)
- Sigue al cursor con 14 px de desplazamiento. Fondo `superficie`, radio 6 px, padding 0,5 rem / 0,7 rem, la única sombra del sistema.
- Título 650; línea de 0,82 rem `texto-2`. En una provincia, lleva el icono de clase de 13 px y su nombre de clase, y el VAN si existe; en un municipio, su superficie en km².
- No captura el puntero y es `aria-hidden`: la misma información está en la lista.

### Botones de volver (`.mapa-volver`, `.volver`)
- **Forma:** píldora de 999 px. `.mapa-volver` flota arriba a la izquierda del mapa con fondo `suelo` / `superficie` al 92 %. `.volver` es la cabecera de la ficha, con fondo `superficie`.
- **Texto:** «Toda España», o «Volver a la península» cuando la provincia es Canarias. La ficha añade la tecla Esc como `kbd` (0,8 rem `texto-3`), oculta en táctil y en 900 px o menos.
- **Estados:** hover → `linea`. Foco visible → contorno de 2 px `texto` desplazado 2 px.
- Ambos llevan una flecha de trazo dibujada en SVG. No es un patrón del sistema a replicar.

### Municipios analizados (`.sitios`)
- Píldoras de 999 px con borde de 1 px `linea`, texto 0,86 rem, con icono de clase de 13 px.
- Activa (`aria-pressed`): fondo `texto`, texto y borde del mismo color `suelo`.

### Puntos de municipios (`.sitio`)
- Punto de 11 px (15 px en la vista de provincia) del color de clase, con anillo de lectura. Su etiqueta aparece solo en la vista de provincia, sobre fondo `suelo` al 85 %; la etiqueta activa invierte a fondo `texto` con texto `suelo`.

### Sello de demostración (`.sello`)
- Píldora de 999 px, borde discontinuo de 1 px `texto-3`, texto 0,8 rem 600 `texto-2`: «Datos de demostración». Su `title` explica qué es sintético y qué es real.
- Aparece en la cabecera solo cuando la predicción es de demostración.

### Marca «en directo» (`.vivo-marca`)
- Texto 0,8 rem `texto-3`: «en directo», hora del dato y fuente («Red Eléctrica», «Open-Meteo»).
- Punto de 0,42 em en `texto-2` que late: 2,4 s, opacidad de 1 a 0,25 en el 50 %.
- Es neutra: el dato en directo no tiene color.

### Números que giran (`Flap`)
- Cifras sin casillas ni fondos: cada carácter va en un hueco con `overflow: hidden` y la cifra nueva entra desde arriba. Es el único gesto de movimiento del dato.

### Buscador, avisos y errores
- **Aviso** (`.aviso-vivo`): 0,86 rem `texto-2`; el botón «Reintentar» es una píldora de `superficie`.
- **Línea en directo** (`.linea-vivo`): 0,88 rem `texto-2`, con las cifras en mono `texto`.
- **Error de carga** (`.error-carga`): radio 6 px, borde de 1 px `texto-3`, con `role="alert"`.
- **Sin conexión** (`.sin-conexion`): texto 0,85 rem `texto-2`. No usa un color de clase.

### Movimiento

- **Giro de cifra (`Flap`):** en CSS, `gira` 120 ms con `cubic-bezier(0.25, 0.8, 0.35, 1)`, de `translateY(-45 %)` y opacidad 0,2 a la posición. En JS, cada carácter recorre el alfabeto y los dígitos cada 55 ms antes de asentarse; cada casilla se asienta tras un número de pasos que crece con su posición en la cifra.
- **Revelado de la ficha (`.ficha`):** 320 ms con `cubic-bezier(0.16, 1, 0.3, 1)`, de opacidad 0 y 6 px hacia abajo a la posición.
- **Vuelo del mapa:** `fitBounds` de 1600 ms, `essential`, zoom máximo 9,5. El margen es `clamp(24 px, 7 % del ancho, 90 px)`. Al volver a España, el margen máximo es 32 px y la duración es la misma.
- **Latido de «en directo»:** 2,4 s, `ease-in-out`, infinito.
- **Hover y foco:** sin transiciones. Los cambios de fondo son inmediatos.

**Reducir movimiento** (`prefers-reduced-motion: reduce`, leído por `useMovimientoReducido`): las cifras cambian de golpe; la ficha aparece sin revelado; el latido se detiene; el mapa salta sin vuelo (duración 0); el scroll del panel es instantáneo.

### Estados de dato

- **Demostración (sello y nota relativa):** con predicción de demostración, la cabecera muestra el sello «Datos de demostración», la insignia dice «relativa · demostración» y el pie de la ficha explica que los indicadores son sintéticos y la clase es relativa (tercios del VAN; «no viable» = no rentable). Con la predicción real, no hay sello ni nota.
- **Sin datos (rayado):** una provincia sin modelo se pinta rayada en el mapa, en Canarias, en la leyenda y en el reparto. Su ficha dice «Sin datos todavía» con la muestra rayada; no muestra estado, score ni cifras económicas.
- **Sin conexión:** si una fuente en directo falla, la luz de la cabecera dice «sin conexión» en `texto-2` y el bloque afectado ofrece «Reintentar». No hay color de error.
- **Cargando:** la cabecera muestra «cargando…» y el mapa, «Cargando mapa…».
- El sello de demostración solo aparece cuando los datos ya han cargado y se sabe que no hay predicción real.

## Do's and Don'ts

### Do:
- **Do** usar la paleta de rentabilidad solo para clase, y siempre con su icono de barras y su nombre.
- **Do** rotular cada cifra con su origen: la hora y la fuente en la marca «en directo», o «Datos de demostración» y «relativa · demostración» cuando lo son.
- **Do** mostrar cada clase con sus motivos («Por qué»).
- **Do** rotular el precio y la demanda de la luz como nacionales (peninsulares).
- **Do** usar el rayado solo para «sin datos».
- **Do** separar superficies con tono y hairline de 1 px.
- **Do** mantener el giro de cifra en 120 ms y el vuelo del mapa en 1600 ms, y anularlos con reducir movimiento.
- **Do** dar a cada cifra un valor real, modelado o marcado como sin datos.

### Don't:
- **Don't** usar un color de clase en cabeceras, enlaces, botones, insignias que no sean de clase ni en estados de conexión.
- **Don't** quitar el icono de barras y dejar solo el color de la clase.
- **Don't** usar rayado para algo que no sea ausencia de dato.
- **Don't** mostrar una cifra de demostración sin su marca.
- **Don't** presentar un precio o una demanda nacional como si fuera de provincia.
- **Don't** inventar valores: sin datos se muestra «Sin datos todavía» o un guion «—».
- **Don't** reintroducir elementos del sistema anterior: casillas split-flap, amarillo de selección, lámparas de estado con formas propias o etiquetas de origen en mayúsculas.
- **Don't** añadir sombras decorativas ni tarjetas con bordes.
