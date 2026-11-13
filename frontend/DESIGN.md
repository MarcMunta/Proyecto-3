---
name: Tablero de Salidas
description: Mapa de España de viabilidad de un centro de datos, presentado como tablero de salidas split-flap.
colors:
  suelo: "#111214"
  contexto: "#1d1e21"
  junta: "#08090a"
  modulo: "#1b1d20"
  modulo-alto: "#24272b"
  regla: "#2e3136"
  caracter: "#f1ecdf"
  caracter-2: "#b6b0a3"
  caracter-3: "#8f8a80"
  amarillo: "#ffcc33"
  tinta-sobre-activo: "#141414"
  viable: "#3fd27f"
  condiciones: "#ff9c40"
  no-viable: "#ff5b4b"
  sin-datos: "#6c6f75"
  puntuacion-0: "#2a2a2c"
  puntuacion-25: "#4b463e"
  puntuacion-50: "#7d715c"
  puntuacion-75: "#bdaa80"
  puntuacion-100: "#f3e3b8"
typography:
  display:
    fontFamily: "Martian Mono Variable, ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "clamp(3.4rem, 5.2vw, 5.6rem)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "normal"
  board:
    fontFamily: "Martian Mono Variable, ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "1.55rem"
    fontWeight: 520
    lineHeight: 1
    letterSpacing: "normal"
  headline:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "1.45rem"
    fontWeight: 700
    lineHeight: 1.45
    letterSpacing: "normal"
  title:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 700
    lineHeight: 1.45
    letterSpacing: "normal"
  body:
    fontFamily: "Archivo Variable, system-ui, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  label:
    fontFamily: "Martian Mono Variable, ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "0.7rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "0.08em"
rounded:
  none: "0px"
spacing:
  xs: "0.3rem"
  sm: "0.6rem"
  md: "1rem"
  lg: "1.6rem"
components:
  volver:
    backgroundColor: "{colors.modulo}"
    textColor: "{colors.caracter}"
    rounded: "{rounded.none}"
    padding: "0.4rem 0.7rem"
  volver-hover:
    backgroundColor: "{colors.modulo-alto}"
  fila:
    backgroundColor: "{colors.modulo}"
    textColor: "{colors.caracter}"
    rounded: "{rounded.none}"
    padding: "0.4rem 0.7rem"
  fila-hover:
    backgroundColor: "{colors.modulo-alto}"
  fila-sin-datos:
    textColor: "{colors.caracter-3}"
  cifra:
    backgroundColor: "{colors.modulo}"
    textColor: "{colors.caracter}"
    rounded: "{rounded.none}"
    padding: "0.65rem 0.75rem 0.7rem"
  buscador:
    backgroundColor: "{colors.junta}"
    textColor: "{colors.caracter}"
    rounded: "{rounded.none}"
    padding: "0.6rem 0.75rem"
  conmutador-activo:
    backgroundColor: "{colors.caracter}"
    textColor: "{colors.suelo}"
  sitio-activo:
    backgroundColor: "{colors.amarillo}"
    textColor: "{colors.tinta-sobre-activo}"
---

# Design System: Tablero de Salidas

<!-- Escrito a partir del código construido (src/styles.css, src/components, src/model/colores.ts). Los tokens del frontmatter son normativos. -->

## Overview

**Creative North Star: "El Tablero de Salidas"**

España como panel de salidas de una estación: cada provincia es un destino anunciado con su estado, su score y la hora de su dato. El mapa ocupa la izquierda (unos 62 % del ancho en escritorio) y es el protagonista; el tablero de la derecha (unos 38 %) lista las provincias como filas de módulos negros mate separados por juntas de 1 px. La densidad es alta pero ordenada: nada flota, nada redondea, todo se lee en filas.

La materia es la de un panel físico: módulos casi negros, caracteres split-flap blanco cálido en Martian Mono condensada, prosa en Archivo. El amarillo no decora; solo marca lo elegido. El tono de la rampa de score es cálido (de un panel apagado a un panel encendido), no un verde-rojo de semáforo. Las cifras se mueven como las letras de un tablero real: cada casilla gira y se asienta. El mapa vuela a su destino en 1,7 s.

La honestidad es parte del sistema: cada número dice de dónde viene (en directo, demo, supuesto, dato oficial o modelo), y un score nunca aparece sin sus motivos. Se rechaza de forma confirmada el panel oscuro de tarjetas de vidrio con KPI sueltos.

**Key Characteristics:**
- Negro mate en capas tonales, con juntas de 1 px en lugar de sombras.
- Radio cero en todo el sistema.
- Caracteres split-flap cálidos para cifras, nombres de provincia y estados.
- Un solo acento (amarillo) reservado para la selección.
- Lámparas de estado con forma propia (círculo, triángulo, aspa, aro): el estado nunca depende solo del color.
- Rayado diagonal = sin datos, sin excepciones.
- Origen visible en cada cifra (EN DIRECTO, DEMO, SUPUESTO, GISCO, MODELO, SIN CONEXIÓN).

## Colors

Neutros cálidos casi negros con una única luz de texto cálida y un solo amarillo de selección. Los colores de dato (estados y rampa de score) son los únicos que cargan significado; ningún otro color debe competir con ellos.

### Primary
- **Blanco de carácter** (`caracter` #f1ecdf): texto principal, caracteres del flap, cifras, contorno de foco (`:focus-visible`, 2 px), fondo de la opción activa del conmutador (sobre `suelo`).
- **Amarillo de selección** (`amarillo` #ffcc33): el único acento. Contorno de la provincia elegida en el mapa, etiqueta del emplazamiento activo (con texto `tinta-sobre-activo` #141414) y subrayado del emplazamiento pulsado en el tablero de la ficha. Ver The Yellow Is Selection Rule.

### Secondary
- **Viable** (`viable` #3fd27f): estado "VIABLE". Forma: círculo lleno.
- **Viable con condiciones** (`condiciones` #ff9c40): estado "CON CONDICIONES" o "CONDIC." en el tablero. Forma: triángulo.
- **No viable** (`no-viable` #ff5b4b): estado "NO VIABLE" y errores de conexión. Forma: aspa.
- **Sin datos** (`sin-datos` #6c6f75): estado "SIN DATOS". Forma: aro abierto. En el mapa, el "sin datos" se pinta con rayado, no con este color.

### Tertiary
- **Rampa de score** (`puntuacion-0` a `puntuacion-100`: #2a2a2c, #4b463e, #7d715c, #bdaa80, #f3e3b8): luminancia cálida que interpola linealmente entre paradas (0, 25, 50, 75, 100). Colorea provincias y municipios analizados. Desde score 58 el texto sobre la casilla pasa a `tinta-sobre-activo` (#141414); por debajo, `caracter`.

### Neutral
- **Suelo** (`suelo` #111214): fondo de página, fondo del mapa y del tablero, color de la tinta sobre el blanco.
- **Contexto** (`contexto` #1d1e21): Portugal y Francia en el mapa. Es el valor que pinta el mapa WebGL (ver nota de divergencia).
- **Junta** (`junta` #08090a): juntas entre módulos, huecos hundidos, fondo de campos y de etiquetas sobre el mapa.
- **Módulo** (`modulo` #1b1d20): cara de filas, cifras, botones y leyenda.
- **Módulo alto** (`modulo-alto` #24272b): estado de paso del ratón y foco de filas y botones.
- **Regla** (`regla` #2e3136): reglas de 1 px, bordes y anillos de paneles.
- **Carácter 2** (`caracter-2` #b6b0a3): texto secundario, unidades, etiquetas de campo.
- **Carácter 3** (`caracter-3` #8f8a80): texto terciario, notas, guiones de "sin dato", ejes.

**Sincronía de tokens:** `src/model/colores.ts` (lo que pinta el mapa WebGL) y `:root` en `styles.css` comparten valores: `contexto` #1d1e21 y `caracterTenue` = `caracter-2` #b6b0a3. Si se cambia uno, hay que cambiar el otro.

### Named Rules
**The Yellow Is Selection Rule.** El amarillo señala solo lo activo: la provincia elegida y el emplazamiento elegido. No se usa para cabeceras, badges ni estados.

## Typography

**Display Font:** Martian Mono Variable (con ui-monospace, Cascadia Mono, Consolas, monospace), con `font-stretch` 78 % para las casillas del flap y 75–80 % para etiquetas.
**Body Font:** Archivo Variable (con system-ui, Segoe UI, sans-serif).
**Label/Mono Font:** la misma Martian Mono. Las cifras y los códigos van siempre en mono; la prosa siempre en Archivo.

Ambas fuentes se cargan desde `@fontsource-variable` (martian-mono y archivo, versión 5.3.0) en `src/main.tsx`.

**Character:** un tablero que habla en mayúsculas mono condensadas y una prosa de sans legible. El contraste entre el mono de salidas y la prosa es lo que hace que el dato parezca anunciado y la explicación parezca escrita.

**Escala raíz:** `html { font-size: clamp(15px, 0.42vw + 10.5px, 19px) }`. Todos los `rem` de este documento escalan con la pantalla; los valores son relativos a esa raíz.

### Hierarchy
- **Display** (Martian Mono, 600, `clamp(3.4rem, 5.2vw, 5.6rem)`, line-height 1): solo el score grande de la ficha de provincia (`flap-cartel`). En móvil, 3.2 rem.
- **Board** (Martian Mono, 520, 1.55 rem, line-height 1): estado de la ficha (`flap-l`, p. ej. "VIABLE"). `flap-xl` (1.75 rem) para código y nombre de la provincia en la cabecera de la ficha. En móvil bajan a 1.15 rem y 1.35 rem.
- **Headline** (Archivo, 700, 1.45 rem): título del tablero "Provincias".
- **Title** (Archivo, 700, 1.2 rem, `font-stretch` 92 %): encabezados de bloque de la ficha (Energía, Agua, Costes…).
- **Body** (Archivo, 400, 1 rem, line-height 1.45): explicaciones y motivos. Medida máxima 60–70 ch (`.explica` 62 ch, `.motivo` 70 ch).
- **Label** (Martian Mono, 600, 0.6–0.8 rem, tracking 0.05–0.08 em, mayúsculas): cabeceras de columna, origen de cifra, etiquetas del teletipo, ejes del gráfico. Son las etiquetas más pequeñas del sistema y quedan por debajo de lo que pide la proyección a distancia (ver Do's and Don'ts; el tamaño no es una regla).

### Named Rules
**The Caps Are The Board Rule.** Las mayúsculas pertenecen al tablero: casillas del flap, códigos, estados y etiquetas de dato. La prosa, los títulos largos y las explicaciones van en Archivo, en caja normal.

## Layout

**Estructura de escena (escritorio):** cabecera (franja) a todo el ancho y debajo una escena de dos columnas, `minmax(0, 1.62fr)` para el mapa y `minmax(25rem, 1fr)` para el tablero (≈ 62 / 38). La aplicación ocupa `100dvh`; el tablero hace scroll propio y el mapa no.

**Franja superior:** una rejilla de tres columnas (marca, reloj, sello) y debajo la tira de teletipo a todo el ancho con fondo `junta`. Padding 0.55 rem / 1 rem.

**Mapa:** llena su columna (`position: absolute; inset: 0`). Canarias como recuadro inset abajo a la izquierda (13 rem, o 30 vw si es menor); leyenda abajo a la derecha (15.5 rem) con el conmutador de agregado, la rampa 0–100 y las cuatro lámparas.

**Tablero:** cabecera (título, recuento, lámparas de conteo, nota del modelo, buscador) y después el panel de salidas con margen de 0.75 rem.

**Ritmo de espaciado:** no hay una cuadrícula de 4 u 8 px. Se usan `0.3 / 0.4 / 0.45 / 0.55 / 0.6 / 0.7 / 0.75 / 1 / 1.2 / 1.6 rem`. Los valores recurrentes son gutter horizontal de 1 rem, separaciones de 0.6 rem y padding de bloque de 1.6 rem arriba y 1.2 rem abajo.

### Breakpoints observados
- **1280 px:** cada fila del tablero pierde el texto del estado y deja solo la lámpara (la forma y el color bastan), con la cabecera de columna como apoyo.
- **1100 px:** el tablero se estrecha (`minmax(21rem, 0.9fr)`) y la leyenda pasa a 13.5 rem.
- **900 px:** la escena pasa a bloque; el mapa tiene altura `clamp(24rem, 112vw, 62svh)`; el reloj desaparece; el teletipo se parte en líneas y muestra las cuatro lecturas; la leyenda se oculta cuando hay una provincia abierta; la tecla Esc se oculta en pantallas táctiles o estrechas.
- **560 px:** se oculta el subtítulo de la marca; las etiquetas de provincia del mapa desaparecen; la leyenda se convierte en un recuadro compacto arriba a la izquierda; desaparece la columna de dato de las filas; los medidores ceden a 7 rem.

### Named Rules
**The Fluid Board Rule.** Todo el sistema escala con la raíz fluida; no se fijan tamaños en píxeles para texto. Las dimensiones fijas son solo lámparas (12–26 px), marcadores del mapa, la muestra de rayado de la leyenda y los segmentos del medidor.

## Elevation & Depth

Sistema plano por capas tonales. La profundidad se da con los escalones `suelo` → `contexto` → `modulo` → `modulo-alto` y con juntas `junta` de 1 px, no con sombras. Las únicas sombras son de flotación (la pista del mapa) o anillos de 1 px de `regla` o `junta` que delimitan paneles.

### Shadow Vocabulary
- **Pista flotante** (`box-shadow: 0 8px 24px rgb(0 0 0 / 0.45)`): solo la etiqueta que sigue al cursor sobre el mapa. Es la única sombra difusa del sistema.
- **Anillo de panel** (`box-shadow: 0 0 0 1px var(--regla)`): carcasa del panel de salidas y de los botones de control del mapa.
- **Anillo de junta** (`box-shadow: 0 0 0 1px var(--junta)`): módulos de cifra y gráfico.
- **Regla inferior de la franja** (`box-shadow: 0 1px 0 var(--regla)`): una regla de 1 px, no una sombra.

### Named Rules
**The Flat Board Rule.** Nada flota en reposo. Una superficie se distingue por su escalón tonal o su junta, y solo la pista del mapa se separa del fondo con sombra.

## Shapes

Radio cero en todo el sistema: módulos, botones, campos, barras de desplazamiento (`border-radius: 0`), controles de MapLibre (forzados a 0 con `!important`) y atribución. Los bordes miden 1 px. Las formas que sí son redondas son las lámparas de estado, que son símbolos y no radios.

Formas recurrentes:
- **Casilla de flap:** rectángulo con una mitad superior y otra inferior de tonos ligeramente distintos y una línea negra de 1 px en la juntura. Cada casilla es un módulo.
- **Lámpara de estado:** círculo (Viable), triángulo (Con condiciones), aspa (No viable), aro abierto (Sin datos). Es el único lenguaje de forma geométrica del sistema.
- **Medidor:** diez segmentos rectangulares de 2 px de separación.
- **Borde discontinuo (1 px dashed):** solo para el sello "Datos de demostración" y la etiqueta DEMO. Marca lo que es ficticio.
- **Pantalla de estado sin datos:** rayado diagonal a 45° (ver Components).

### Named Rules
**The Zero Radius Rule.** Ninguna esquina se redondea. Si un elemento necesita diferenciarse, se hace con juntas, tonos o una forma de estado, no con radio.

## Components

Cada componente tiene carácter de panel: se lee como un módulo de tablero y se comporta como una casilla que cambia de valor.

### Split-flap (Flap)
- **Forma:** casillas de `min-width: 1.04ch`, con padding 0.16 em / 0.09 em / 0.13 em, fondo gradiente de dos mitades y línea negra central de 1 px. Código de provincia en tono hundido (`#2c2f34` → `#23262a`, texto `caracter-2`).
- **Animación:** cada casilla gira en `flap-cae` (rotateX de -85° a 0, brillo de 0.55 a 1) durante **110 ms** con `cubic-bezier(0.25, 0.8, 0.35, 1)`. En JS, cada carácter recorre letras del alfabeto cada 55 ms (secuencia determinista) antes de asentarse en el valor nuevo.
- **Escalonado:** las filas del tablero entran con 30 ms de retardo por fila (máximo 26 filas), el nombre con +40 ms y el score con +90 ms.
- **Ancho fijo:** la cifra o el nombre ocupan un número fijo de casillas (relleno a la derecha si es numérico y alineado a la derecha, a la izquierda en el resto). El texto va siempre en mayúsculas.
- **Accesibilidad:** el texto visible va en `aria-hidden`; un `sr-only` lleva el valor legible.

### Lámpara de estado (Lampara)
- Cuatro formas, una por estado (ver Shapes). Tamaños de 12–26 px según el contexto.
- Siempre acompaña a la etiqueta o al número del estado; el color nunca es el único canal.

### Filas del tablero (Fila)
- **Forma:** rejilla de cinco columnas (código, nombre, estado, score, dato). Ancho completo, padding 0.4 rem / 0.7 rem, fondo `modulo`. Separación de 1 px por la junta de la carcasa.
- **Estados:** paso del ratón o foco → `modulo-alto`. Sin datos → nombre y estado en `caracter-3`, score como guion "—".
- **Cabecera:** fila fija (`sticky`) con fondo `#0d0e10`, borde inferior de 2 px `regla`, etiquetas de label.

### Teletipo
- Tira continua bajo la cabecera, fondo `junta`, con cuatro lecturas nacionales de Red Eléctrica: Luz spot (€/MWh), Media hoy (€/MWh), Demanda (MW), Renovable ayer (%). Cada lectura lleva su hora de dato.
- Sello inicial con un cuadrado que late (2.4 s de ciclo, opacidad entre 1 y 0.25) e indica "En directo · Red Eléctrica · nacional".
- Errores: "— sin conexión" en `no-viable`.

### Cifra (Cifra)
- **Forma:** módulo con fondo `modulo`, anillo de junta de 1 px, padding 0.65 rem / 0.75 rem. Rejilla de módulos con `auto-fill` de 10.5 rem y juntas de 1 px.
- **Partes:** etiqueta (Archivo 600, 0.76 rem, `caracter-2`), valor (Martian Mono 1.12 rem; "grande" 1.35 rem), unidad (Archivo 0.74 rem, `caracter-2`), origen (etiqueta de origen), nota opcional (0.74 rem, `caracter-3`).
- CAPEX, OPEX y VAN son cifras "grandes" (`cifra-grande`).

### Origen (Origen)
Etiqueta de cada cifra de la ficha. Van en mayúsculas mono de 0.6 rem, con un borde de 1 px.
- **EN DIRECTO** (`origen-vivo`): borde y texto `caracter-2`/`caracter`, cuadrado que late, hora del dato y fuente (REData o Open-Meteo).
- **GISCO** (`origen-real`): dato oficial real, con el nombre de la fuente ("GISCO LAU 2024"). Borde `regla`.
- **DEMO** (`origen-demo`): modelo con indicadores sintéticos. Borde discontinuo `caracter-3`.
- **SUPUESTO**: valor de referencia del modelo (p. ej. precio de electricidad usado por el modelo). Texto plano sin variante.
- **MODELO**: columna Dato de cada fila del tablero cuando el modelo no es de demostración.
- **SIN CONEXIÓN** (`origen-error`): borde y texto `no-viable`.

### Named Rules
**The Honest Origin Rule.** Cada cifra de la ficha de provincia lleva su origen. Las lecturas del teletipo llevan su hora y la etiqueta de la tira, y las filas del tablero indican MODELO o DEMO en su columna Dato. Un precio nacional nunca se presenta como precio de provincia.

### Mapa (MapaEspana)
- **Relleno por provincia:** la rampa de score (`puntuacion-*`) según el mejor emplazamiento o la media provincial (conmutador de la leyenda). Sin datos → rayado.
- **Selección:** la provincia elegida conserva opacidad 1; las demás bajan a 0.2. Su contorno es amarillo de 2.6 px.
- **Municipios analizados:** misma rampa; los no analizados, módulo apagado; el paso del ratón sobre un municipio usa `#2b2e33`.
- **Bordes:** líneas `caracter` de anchura creciente con el zoom; provincias con línea `junta`.
- **Emplazamientos:** marcadores circulares de 15–20 px sobre fondo `junta`; el activo tiene su etiqueta en amarillo.
- **Pista del cursor:** etiqueta `junta` con borde `regla` y la única sombra difusa del sistema.
- **Controles de MapLibre:** módulo `modulo`, anillo de 1 px `regla`, sin radio, iconos invertidos a claro. Atribución compacta.
- **Canarias:** recuadro inset con las dos provincias; las sin datos van rayadas, y el paso del ratón da contorno `caracter` de 1.5 px.

### Vuelo de cámara (movimiento del mapa)
- Al elegir una provincia, `fitBounds` con duración **1700 ms**, `essential: true`, zoom máximo 9.5 y margen de `clamp(24 px, 7 % del ancho, 90 px)`.
- Al volver a España, el encuadre vuelve a `fitBounds` de la península con margen máximo de 32 px, con la misma duración.
- Con reducir movimiento la duración es 0.

### Botones y controles de volver
- **Forma:** rectángulo `modulo` con borde de 1 px `regla`, padding 0.4 rem / 0.7 rem. Sin icono de flecha en el sistema; la tecla Esc aparece como `kbd` en la ficha (oculta en táctil o en pantallas de 900 px o menos).
- **Estados:** paso del ratón → `modulo-alto`. Foco visible → contorno de 2 px `caracter` a 2 px del borde.

### Conmutador (agregado)
- Dos opciones en rejilla de dos columnas, separadas por juntas de 1 px `junta`. Cada opción: `modulo`, altura mínima 2.4 rem (2 rem en móvil).
- Opción activa: fondo `caracter`, texto `suelo`, peso 650.

### Buscador
- Campo de texto de ancho completo, fondo `junta`, borde de 1 px `regla`, radio 0, texto `caracter`, marcador `caracter-3`.

### Ficha de provincia
- Entra con un revelado vertical en `clip-path` durante 380 ms (`cubic-bezier(0.16, 1, 0.3, 1)`).
- Orden: cabecera (volver, código y nombre, capital y municipios, origen GISCO), veredicto (lámpara, estado en Board, score grande, explicación), bloques por área (ocho, según `BLOQUES`), medidores, índices con umbral (estrés hídrico 0.7, barra que pasa a `condiciones` al superarlo), gráfico de precio de 15 minutos con referencia del modelo, créditos.
- Sin datos: "SIN DATOS TODAVÍA" en Board, lámpara de aro y explicación; no se muestran estado, score ni cifras económicas.

### Rayado (no-data pattern)
- **Mapa, provincias:** líneas diagonales de color `#56595f` en un patrón de 8 píxeles de periodo y 2 de grosor (imagen de 16 × 16 a 2x), con opacidad completa.
- **Mapa, municipios sin análisis:** mismo color con periodo 16 y grosor 1, opacidad 150/255, para que se lean sus límites.
- **Canarias:** patrón SVG de 6 unidades, trazo de 1.4, girado -45°.
- **Leyenda:** muestra de 13 px con `repeating-linear-gradient` a 45°, trazo de 1.5 px cada 4 px.
- Es la única manera de indicar ausencia de dato en el mapa.

### Named Rules
**The Hatching Means No Data Rule.** El rayado indica ausencia de dato y no se usa para nada más.

**The Lamp Shape Rule.** Un estado se lee por forma y color a la vez. Quitar la forma, o usar solo el color, no es válido.

**Movimiento y reducción.** Con `prefers-reduced-motion: reduce`, se desactivan las animaciones de `.flap-g` (la casilla gira), `.ficha` (revelado), `.origen-vivo i` y `.teletipo-sello i` (cuadrados que laten); el flap cambia de golpe; el mapa salta sin vuelo; el scroll del tablero es instantáneo.

## Do's and Don'ts

### Do:
- **Do** poner el origen junto a cada cifra (EN DIRECTO con hora, DEMO, SUPUESTO, GISCO, MODELO o SIN CONEXIÓN).
- **Do** marcar el estado con forma y color a la vez: círculo para Viable, triángulo para Con condiciones, aspa para No viable, aro para Sin datos.
- **Do** reservar `amarillo` (#ffcc33) para la provincia o el emplazamiento activo.
- **Do** usar el rayado solo para "sin datos".
- **Do** mostrar cada score junto a sus motivos.
- **Do** mantener radio cero, juntas de 1 px y escalones tonales en lugar de sombras.
- **Do** mantener la casilla de flap en 110 ms y el vuelo de mapa en 1,7 s, y anularlos con reducir movimiento.
- **Do** dar la electricidad y la demanda como nacionales (peninsulares) y decirlo en la etiqueta.

### Don't:
- **Don't** redondear esquinas ni añadir sombras de caída como decoración.
- **Don't** usar amarillo en cabeceras, badges, estados o decoración.
- **Don't** usar rayado para algo que no sea ausencia de dato.
- **Don't** quitar la forma de la lámpara para dejar solo el color.
- **Don't** mostrar una cifra sin su origen, ni un número sin datos reales o modelados.
- **Don't** presentar un precio o una demanda nacional como si fuera de provincia.
- **Don't** inventar valores: sin datos se muestra "sin datos todavía" o un guion "—".
- **Don't** escribir prosa en mayúsculas o mono; el mono es del tablero.
