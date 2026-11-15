---
tags: [metodologia, reglas, datos, p3]
estado: borrador
actualizado: 2026-11-14
---

# 04 · Reglas de datos (no negociables)

Volver a [[00_Indice]]. Se aplican en todas las fases de [[03_Flujo_de_trabajo]]. Si una regla estorba, se discute en
equipo y se cambia **aquí**, no en el código.

| ID | Regla | Por qué | Cómo se comprueba |
|---|---|---|---|
| **R-1** | **Nunca inventar valores.** Si una fuente no tiene un dato, queda vacío (NaN) o se marca como ausente. Los datos sintéticos (demo) solo se usan si están etiquetados como tales. | Un valor inventado en un informe de viabilidad puede costar una inversión real. | Revisión en PR; columna `origen_datos` en los datos demo. Hoy: `data/demo/municipios_demo.csv` (`origen_datos = "DEMO sintético"`). |
| **R-2** | **La capa raw es inmutable.** `data/raw/` no se edita a mano ni se sobrescribe; cada descarga lleva fecha. | Permite repetir el análisis y auditar cambios. | Registro `data/raw/_registro_descargas.csv` y manifiesto SHA-256 en `docs/datos/`. |
| **R-3** | **Toda transformación se documenta.** Cada columna derivada tiene su fórmula, su ventana, su fuente y su unidad en el diccionario. | Sin documentación, el informe de origen y el de análisis no se pueden escribir. | Diccionario `data/curated/diccionario_*.csv`; test de que todas las columnas están en el diccionario. |
| **R-4** | **Códigos INE como texto con ceros a la izquierda.** Provincia = 2 dígitos (`"08"`), municipio = 5 dígitos (`"08019"`). Nunca como número. | `8` y `08` son el mismo número para Excel, pero distinta provincia para una clave. | Test: la columna de código tiene longitud fija y tipo texto al leer. |
| **R-5** | **Unidades en el nombre de la columna.** Ejemplos: `demanda_mwh`, `precipitacion_mes_mm`, `inversion_eur`, `potencia_ti_mw`. | Evita confundir MWh con MW, o € con miles de €. | Revisión del diccionario; `tests/test_datos_nuevos.py`. |
| **R-6** | **Particiones temporales.** Entrenamiento, validación y test se separan **por fecha**, nunca al azar. El test se usa una sola vez. | Con series temporales, un reparto aleatorio mezcla el futuro con el pasado y da resultados falsos. | Comprobar que la fecha máxima de entrenamiento < fecha mínima de validación < fecha mínima de test. |
| **R-7** | **Escalar sin perder datos.** Las transformaciones crean columnas nuevas; las originales se conservan. El escalador (media, min, max) se ajusta **solo con entrenamiento**. | Conservar el dato original permite revisar y reproducir; ajustar con todo el dataset filtra información del test. | Test: existen las columnas originales; el escalador se guarda y se reusa; revisión del código. |
| **R-8** | **Sin fuga de información.** Ninguna variable de entrada usa datos posteriores a la fecha que predice ni el propio objetivo. | La fuga de información es la causa de fallo más peligrosa, y la clase la menciona explícitamente [C3 p.4]. | Revisar cada feature con la pregunta: "¿lo sabría en esa fecha?" (ver [[03_Flujo_de_trabajo]], fase 6). |
| **R-9** | **Ausencias explicadas.** Cada columna tiene su nº de nulos y la regla de tratamiento (dejar NaN, imputar, eliminar). La imputación queda en una columna marcada. | Un hueco tratado en silencio cambia los resultados sin que nadie lo vea. | Informe de calidad (fase 2). |
| **R-10** | **Atípicos: decidir y registrar.** Un atípico no se borra sin anotar cuántos eran y por qué. Se distingue error de caso real. | Los atípicos pueden ser el dato más importante (p. ej., una sequía extrema). | Columna o log con el criterio por variable. |
| **R-11** | **Granularidad declarada.** Cada tabla dice qué es una fila (provincia × mes, CCAA × año, municipio…). No se mezclan granularidades sin una regla de reparto escrita. | Mezclar niveles duplica o pierde datos al unir. | Campo `granularidad` en el diccionario de tablas. |
| **R-12** | **Fuentes con licencia.** Solo se usan datos abiertos o con permiso. Se cita la fuente y la licencia (p. ej., CC-BY en Barcelona). | Obligación legal y ética. | Columna de fuente y licencia en `docs/datos/`. |
| **R-13** | **Datos personales fuera.** No se guardan datos personales (nombres, teléfonos, correos, fotos de personas). Si los datos propios de clase contienen personas, se anonimizan antes de subir nada. | Protección de datos (RGPD). | Revisión en PR; búsqueda de patrones de correo y teléfono antes de cada commit de datos (recomendación, no viene de clase). |
| **R-14** | **Datos grandes fuera de git.** Ficheros de más de 100 MB o carpetas enteras de datos raw no se suben al repositorio. Se distribuyen por Release con hash SHA-256. | GitHub no admite ficheros de más de 100 MB y el repo se clonaría lento. | `.gitignore` y `scripts/descargar_datos_raw.ps1`. |
| **R-15** | **Reproducibilidad.** Cualquier cifra de un informe se puede regenerar con un comando, con una semilla fija si hay aleatoriedad. | Es lo que evalúa la rúbrica (código y evidencias verificables). | El notebook o script de cada informe se ejecuta de principio a fin en un equipo limpio. |
| **R-16** | **Parámetros a calibrar, marcados.** Los umbrales y precios de `config/settings.yaml` que no estén calibrados se marcan "a calibrar" y se explican en el informe. | Evita presentar como hecho un supuesto. | Comentario en el YAML y limitación en el informe. |

## Codificación y formato

- **Texto:** UTF-8 en todas las salidas. Al leer fuentes oficiales, usar la codificación real de la fuente (el SEPE usa latin-1; el INE, CSV con `;`).
- **Números:** en los ficheros de salida, punto decimal y sin separador de miles. El INE usa miles con punto y decimales con coma: convertir al leer.
- **Fechas:** ISO 8601 (`AAAA-MM-DD`) y, para meses, `AAAA-MM`.
- **Nombres de columna:** minúsculas, sin tildes ni espacios (`tmedia_mes_c`, `paro_registrado`). Las unidades van al final.
- **Ficheros:** `.parquet` para tablas grandes; `.csv` para tablas pequeñas o para leer a simple vista.

## Fuentes: qué guardar de cada una

Para cada fuente, el informe de origen de datos debe responder:

1. ¿Qué organismo la publica y con qué URL o endpoint?
2. ¿Qué cubre (territorio, periodo, frecuencia)?
3. ¿Qué formato tiene y con qué codificación, separador y decimal?
4. ¿Con qué clave se une (código INE de provincia o municipio, código de CCAA, fecha)?
5. ¿Qué limitaciones conocidas tiene (secretos estadísticos, cambios de códigos, huecos)?
6. ¿Qué licencia tiene?
7. ¿Cuándo se descargó y cuál es su hash?

Estado: ya existe para la mayoría en `docs/datos/README.md` y `docs/datos/tablas_api.md`.

## Qué hacer si una regla choca con el trabajo

1. No saltársela en silencio.
2. Abrir una tarea con la plantilla de [[08_Plantillas]], etiqueta `datos`.
3. Decidir en equipo y cambiar esta nota con fecha.
4. Si la regla bloquea la entrega, dejar la limitación escrita en el informe y en [[06_Checklist_entrega]].
