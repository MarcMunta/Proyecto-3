---
tags: [clase, proyecto-3, pendiente]
actualizado: 2026-11-18
---

# Pendiente para la entrega (15/12/2026)

Volver a [[00 Índice]]. Detalle por ID en `docs/metodologia/06_Checklist_entrega.md`.

## Modelos
- Precio de la luz: 59,7 % (no cumple D8). Ya se han hecho los modelos del gas y del tiempo; el siguiente paso solo sería posible con el **precio del CO2** en abierto (no lo hay). Se queda orientativo y fuera del VAN, explicado en [[Precio de la luz (historia)]].
- Renovables mes a mes (%): 84,8 %, orientativo. La media de 12 meses sí cumple.
- Riesgo sísmico anual: 74 %, no se usa (manda la NCSE-02).
- ~~A3 medio plazo (10 años)~~: hecho el 18/11/2026 (clima, consumo y agua). Emisiones a 10 años no validables (mix desde 2015).
- ~~P2 impacto local~~: hecho el 18/11/2026 (electricidad, red y agua por comunidad).
- ~~Impacto socioeconómico (E39-E41)~~: hecho el 18/11/2026 (input-output del INE). Falta calibrar el reparto del CAPEX. E42 hecho el mismo día (atracción empresarial).
- ~~Escenario de demanda a 10 años con los nuevos CPD (P5)~~: hecho el 18/11/2026. Falta calibrar la realización de lo otorgado (sin dato abierto).
- Reservas de agua a 10 años año a año: 83,3 %, orientativo (la media de la década sí cumple).

## Datos
- Agua concedida (Confederación Hidrográfica), tramitación autonómica, suelo industrial, rutas reales de fibra.
- B1: AEMET, Confederaciones Hidrográficas y CNMC (integrar o justificar la sustitución).
- E19: temperatura media anual en el panel provincial.
- P8: verificar la fuente de zonas inundables.
- ~~Peligrosidad sísmica oficial~~ (hecho el 17/11/2026 con la NCSE-02).
- ~~Generación por tecnología para el precio~~ (hecho el 18/11/2026).

## Documentación (entregables)
- F4/H4: informe de visualización (M4RA4).
- F3: informe de análisis final integrado.
- F1/B3: informe de origen y calidad de los datos.
- F5/B4: documento de almacenamiento y esquema en estrella.
- F7, F9, G3: vídeo con al menos tres casos de uso y manual de usuario.
- F8: manual de instalación probado en un equipo limpio.
- Presentación: contar la historia del precio de la luz (60 % → modelos del gas y del tiempo → 59,7 %, techo 78,9 % con datos reales). Material en [[Precio de la luz (historia)]] y [[Figuras]].

## Otros
- Revisar el simulador (el VAN depende casi solo del clima).
- Parámetros del CPD que faltan (D1-D4, D6, D7, D18-D20).
- PR #1 a #6 pendientes de revisión del equipo.
- ~~Subir a la PR #6 los modelos del gas y del tiempo~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 el medio plazo a 10 años~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 el impacto local~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 el impacto socioeconómico, los escenarios P5 y el afinado~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 la atracción empresarial E42~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 las técnicas de clase I51, I52 e I58~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 el afinado de prob_cpd (I59, I61, I62)~~ (subido el 18/11/2026).
- ~~Subir a la PR #6 el afinado del precio de la luz con la demanda~~ (subido el 18/11/2026).
- Precio del CO2: pedir permiso al ICAP si el equipo lo quiere usar (recomendación). I59, I61 e I62 hechos el mismo día en `prob_cpd`. Queda en ❌ I63 (embeddings, opcional).
- Modelos: **ya no falta ningún modelo** del enunciado; lo pendiente de la sección E es de datos (fibra, 5G, autopistas, puertos, aeropuertos, parcelas, calificación urbanística, calidad del agua).
