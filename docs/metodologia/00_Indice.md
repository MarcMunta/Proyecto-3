---
tags: [metodologia, indice, p3]
estado: borrador
actualizado: 2026-11-14
---

# Metodología del equipo · Proyecto 3 (CPD)

Esta carpeta es un **vault de Obsidian** con la metodología, las reglas y el estado del proyecto.
Está en el repositorio para que todo el equipo tenga la misma versión por Git.

> Proyecto 3 – Sistema de Predicción de Viabilidad para la Instalación de un CPD (data center).
> Máster FP IA y Big Data (Stucom). **Entrega en Moodle: 15/12/2026.**

## Cómo abrir el vault en Obsidian

1. Abre Obsidian y pulsa **Abrir carpeta como vault** (*Open folder as vault*).
2. Selecciona la carpeta `docs/metodologia` dentro del repositorio (`p3-cpd/docs/metodologia`).
3. No hace falta instalar plugins. Los enlaces `[[...]]` funcionan con el visor normal.
4. Si Obsidian pregunta por la configuración de enlaces, deja "Ruta relativa" o "Ruta más corta".

Sin Obsidian también se puede leer todo en GitHub: los enlaces `[[nota]]` son texto plano.

## Mapa de notas

| Nota | Para qué sirve | Cuándo leerla |
|---|---|---|
| [[01_Objetivo_y_alcance]] | Objetivo real del proyecto, preguntas que debe responder, decisiones de alcance, entregables y fechas | Al empezar y cada vez que haya dudas sobre "qué hay que hacer" |
| [[02_Conceptos_clave]] | Glosario de todos los términos importantes de los 4 PDF de clase y del enunciado | Cuando aparezca un término que no entiendas |
| [[03_Flujo_de_trabajo]] | **El método paso a paso**, fase a fase (0 a 11), con técnicas, salidas y "hecho cuando" | Para saber qué toca hacer ahora y en qué orden |
| [[04_Reglas_de_datos]] | Reglas no negociables sobre datos (no inventar valores, capas raw, códigos INE, fugas de información…) | Antes de tocar cualquier dato |
| [[05_Reglas_de_codigo_y_git]] | Flujo de ramas, commits, pull requests, tests y convenciones de código | Antes de escribir código o abrir una PR |
| [[06_Checklist_entrega]] | Checklist que cruza **cada requisito del enunciado y cada técnica de clase** con su estado real | Para revisar qué falta y asignar responsables |
| [[07_Estado_actual]] | Auditoría del repositorio: hecho, parcial, pendiente, riesgos y plan semanal hasta el 15/12 | Cada semana, en la reunión de equipo |
| [[08_Plantillas]] | Plantillas de tarea/issue, PR, cabecera de notebook, sección de informe, ficha de modelo (model card) | Al crear una tarea, una PR o un informe |

Carpeta `fuentes/`: una nota por documento de origen (enunciado y 4 clases), con resumen, términos clave,
acciones obligatorias o recomendadas, enlaces y cómo se aplica a P3.

| Fuente | Nota |
|---|---|
| Enunciado (brief oficial) | [[Enunciado]] |
| Clase 02/10/2026 · Data Modelling | [[Clase_2026-10-02_Data_Relation_Modelling]] |
| Clase 09/10/2026 · Visualización y correlación | [[Clase_2026-10-09_Data_Visualization_Correlation]] |
| Clase 23/10/2026 · Forecasting y métricas | [[Clase_2026-10-23_Forecasting_Metricas]] |
| Clase 13/11/2026 · Advanced Feature Engineering | [[Clase_2026-11-13_Advanced_Feature_Engineering]] |

## Orden de lectura recomendado

1. [[01_Objetivo_y_alcance]]: qué se pide y qué no.
2. [[Enunciado]]: el brief completo, con su rúbrica.
3. [[02_Conceptos_clave]]: vocabulario.
4. [[03_Flujo_de_trabajo]]: el método.
5. [[04_Reglas_de_datos]] y [[05_Reglas_de_codigo_y_git]]: reglas del juego.
6. [[07_Estado_actual]]: dónde estamos.
7. [[06_Checklist_entrega]]: qué falta, fila a fila.
8. [[08_Plantillas]]: para empezar a trabajar.
9. Las notas de `fuentes/` cuando haga falta el detalle de una clase.

## Convenciones de esta carpeta

- **Idioma:** español (de España), frases cortas.
- **Estados** (en frontmatter `estado:` y en tablas): `borrador`, `revisada`, `obsoleta`.
- **Estado de cada requisito** (en la checklist):
  - ✅ hecho: existe en el repositorio y se puede comprobar con una ruta de archivo.
  - 🟡 parcial: existe algo, pero incompleto o sin validar.
  - ❌ pendiente: no existe en el repositorio.
- **Recomendación propia:** todo lo que no viene de clase ni del enunciado va marcado como
  *recomendación (no viene de clase)*.
- **Fechas:** formato `dd/mm/aaaa` en el texto.
- Tras cualquier tarea, actualizar la checklist ([[06_Checklist_entrega]]) y el estado ([[07_Estado_actual]]).
  Esto también lo piden los `CLAUDE.md` y `AGENTS.md` de la raíz.

## Reglas para asistentes de IA

Ver `CLAUDE.md` y `AGENTS.md` en la raíz del repositorio. Resumen: leer este índice, [[03_Flujo_de_trabajo]],
[[04_Reglas_de_datos]] y [[05_Reglas_de_codigo_y_git]] antes de cualquier tarea; comprobar la tarea contra
[[06_Checklist_entrega]]; al terminar, actualizar la checklist y decir qué falta.
