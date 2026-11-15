---
tags: [fuente, clase, feature-engineering, p3]
estado: revisada
actualizado: 2026-11-14
---

# Fuente · Clase 13/11/2026 · Advanced Feature Engineering

Archivo: `C:\Users\marcm\Downloads\20261113_Big_Data_Advanced_Feature_Engineering.pptx.pdf` (31 páginas; revisadas en texto y en las diapositivas clave). Volver a [[00_Indice]].

## Resumen

Feature engineering es el conjunto de transformaciones que hacen que el modelo aprenda mejor, porque los modelos no encuentran tendencias ni relaciones por sí solos. Se revisan las features temporales (lags, ventanas móviles, estacionariedad, diferencias, logaritmos, eventos), las numéricas (escalado, normalización, log, winsorizing, polinómicas), las categóricas (one-hot, frequency, target, embeddings) y las semánticas (conocimiento del dominio, rankings, extracciones). La clase termina con un ejercicio de equipo sobre los proyectos.

## Términos clave

Feature engineering · lags · rolling windows · estacionariedad · diferencias · transformación logarítmica · escalado · normalización (MAX-MIN) · estandarización (Z-SCORE) · winsorizing · polinómicas · one-hot · frequency encoding · target encoding · embeddings · features semánticas · rankings · extracciones · eventos (DANA, Black Friday) · estacionalidad · tendencia · ideas, debilidades y oportunidades.

## Acciones (lo que pide la clase)

**Obligatorias del proyecto (según la clase y el enunciado):**
1. Crear lags, con énfasis en que son lo más importante en previsión (p. 12-14).
2. Crear ventanas móviles (media, máximo, mínimo, desviación) para capturar la tendencia y reducir el ruido (p. 15).
3. Tratar la estacionariedad y la estacionalidad (p. 16) y las diferencias cuando ayuden (p. 17).
4. Aplicar escalado o normalización para que las variables sean comparables ("comparar peras con peras") (p. 23-24).
5. Usar transformación logarítmica en distribuciones asimétricas (p. 25-26).
6. Codificar las categóricas según su número de valores (p. 19-21).
7. Crear variables semánticas con conocimiento del dominio (p. 27-28).
8. Presentar el proyecto con ideas, debilidades y oportunidades (p. 30).

**Recomendaciones (no viene de clase):**
- Escalar **sin perder datos**: crear columnas nuevas y ajustar el escalador solo con entrenamiento (ver [[04_Reglas_de_datos]], R-7).
- Probar la transformación logarítmica con `log1p`, que evita el logaritmo de cero (la clase usa `np.log1p`, p. 26).
- Revisar la fuga de información en cada feature temporal (R-8).

## Enlaces

| Enlace | Dónde | Estado | Qué es |
|---|---|---|---|
| `https://ciec.edu.co/wp-content/uploads/2024/07/El-mito-de-la-inteligencia-artificial.pdf` | p. 5 (recomendación de libro) | Lectura parcial | PDF del libro "El mito de la inteligencia artificial" (en castellano). El texto no se pudo extraer; se leyeron el índice y los títulos de capítulo: Introducción; Primera parte, "El mundo simplificado"; Segunda parte, "El problema de la inferencia" (cap. 8, "No calcules, analiza"; cap. 11, "El aprendizaje automático y el big data"). El contenido completo no está leído. |
| `https://drive.google.com/file/d/1-mHmpwnjJ0QxU-adPv_JgXI9vYFnN_RP/view?usp=sharing` | Anotación del PDF (probablemente en la diapositiva de ejercicios o de cierre) | No leído | Archivo `All_Pokemon.csv` en Google Drive. Requiere iniciar sesión; no se pudo leer. Es el dataset del ejercicio de semántica (Pokémon). |

## Cómo se aplica a P3

- **Fase 6 (feature engineering):** es la guía principal de la fase. Lags de 1, 3 y 12 meses para demanda, reservas y precios; ventanas de 3, 6 y 12 meses; diferencias si hay tendencia; `log1p` en variables asimétricas.
- **Escalado para modelos:** distinto del escalado de scores. Para scores ya existe min-max; para modelos hay que ajustar el escalador solo con entrenamiento.
- **Variables semánticas para P3:** zona climática, ámbito hidrográfico, ranking, distancia a subestación o a un nodo de red, y eventos conocidos (sequías, cortes de luz, cambios de precio).
- **Categóricas:** one-hot para pocas categorías (tipo de refrigeración, CCAA); frequency encoding para muchos municipios; target encoding solo dentro de la partición de entrenamiento.
- **Winsorizing** como alternativa a borrar atípicos (ver [[03_Flujo_de_trabajo]], fase 2 y 3).

## Notas de estado en el repo

Ver [[06_Checklist_entrega]], filas I49 a I66. Resumen: ventana móvil de 12 meses en `agua.py` y factor estacional del baseline (🟡), normalización min-max para scores (✅). Lags, diferencias, logaritmos, one-hot y resto de codificaciones están pendientes (❌).
