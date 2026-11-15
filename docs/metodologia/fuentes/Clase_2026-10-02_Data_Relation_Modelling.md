---
tags: [fuente, clase, datos, git, p3]
estado: revisada
actualizado: 2026-11-14
---

# Fuente · Clase 02/10/2026 · Data Modelling

Archivo: `C:\Users\marcm\Downloads\20261002_Data_Relation__Modelling.pptx.pdf` (14 páginas, leídas en texto y revisadas). Volver a [[00_Indice]].

## Resumen

Introduce los tipos de datos (relacionales, no relacionales, tabulares, no tabulares; cualitativos y cuantitativos) y la adquisición de datos desde dos fuentes: open data de Barcelona y datos propios (fotos, registros o encuestas). Después plantea un ejercicio de equipo como empresa con git: ramas por grupo, roles y reglas para las carpetas del proyecto.

## Términos clave

Datos relacionales · no relacionales · tabulares · no tabulares (imágenes, audio, vídeo, proteínas) · cualitativos · cuantitativos · open data · formato común ("common ground") · brainstorming · roles de grupo (Dirección, Data Cleaners, Data Visualization, Data Filters, R&D) · rama `feature/…` · `git fetch`, `git checkout develop`, `git pull --rebase`, `git checkout -b` · carpetas `data/`, `utils/`, `config/` · enums.

## Acciones (lo que pide la clase)

**Obligatorias del proyecto (según la clase):**
1. Adquirir datos de dos fuentes: open data (Barcelona) y datos propios (p. 5). Para P3, el enunciado no pide datos propios.
2. Convertir todos los datos a un formato común (p. 5).
3. Trabajar con ramas por tarea y en equipo (p. 10-11).
4. Mantener las carpetas limpias: `data/` solo con datos usados; `utils/` con funciones directas; `config/` para configuración global (p. 12-13).
5. Usar enums; la clase dice que dan puntos extra (p. 13).

**Recomendaciones (no viene de clase):**
- Decidir la base de ramas: la clase usa `develop`; el repo usa `main`. Ver [[05_Reglas_de_codigo_y_git]].
- Documentar la granularidad y los tipos de cada tabla (ver [[04_Reglas_de_datos]], R-11).

## Enlaces

| Enlace | Dónde | Estado | Qué es |
|---|---|---|---|
| `https://opendata-ajuntament.barcelona.cat/` | p. 5 ("This link") | Leído | Portal de datos abiertos del Ayuntamiento de Barcelona. 558 conjuntos de datos, cinco temas (Territori, Població, Ciutat i serveis, Administració, Economia i Empresa), clasificación por ODS, licencia CC-BY. |
| `https://github.com/ericn65/chatbot_template` | Anotación del PDF (página no determinada con certeza) | Leído | Plantilla Python de chatbot con `uv`, `pytest`, guía de Telegram en español. Útil como ejemplo de estructura de repo, no como fuente de datos. |

## Cómo se aplica a P3

- **Ingesta:** P3 ya usa open data (INE, REE, MITECO, etc.). El concepto de "formato común" es el paso de ETL de [[03_Flujo_de_trabajo]] fase 3.
- **Modelado:** la clase separa datos relacionales y no relacionales. P3 usa DuckDB relacional con esquema en estrella; hay que justificarlo (fase 5).
- **Git:** las ramas `feature/…` y el `pull --rebase` se aplican tal cual en [[05_Reglas_de_codigo_y_git]].
- **Roles:** asignar responsables en la fase 0 (ver [[06_Checklist_entrega]], I7).
- **Enums:** pendiente en el repo (I9).

## Notas de estado en el repo

Ver [[06_Checklist_entrega]], filas I1 a I11. Resumen: formato común (✅), ramas y roles (🟡/❌), enums (❌).
