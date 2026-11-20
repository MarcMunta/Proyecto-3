---
tags: [clase, proyecto-3, cpd, indice]
actualizado: 2026-11-18
---

# Proyecto 3 · Sistema de predicción de viabilidad para instalar un CPD

Máster FP IA y Big Data (Stucom). Entrega en Moodle: **15/12/2026**.
Repositorio: `p3-cpd` (GitHub `MarcMunta/Proyecto-3`). Rama de trabajo actual: `feature/modelos-largo-plazo` (PR #6, encima de #5).

Estas notas recogen **todo el proceso** (pasos, decisiones, datos, modelos, resultados y gráficos) para redactar después el documento de entrega con todos los pasos y el PDF.

## Notas

- [[Proceso]] — registro paso a paso, en orden, con lo que se hizo, por qué y qué salió.
- [[Precio de la luz (historia)]] — el modelo más difícil: del 60 % a los modelos del gas y del tiempo (para la presentación).
- [[Modelos]] — todos los modelos con su acierto y si cumplen el requisito.
- [[Figuras]] — todos los gráficos con su explicación (copias en `Figuras/`).
- [[Decisiones]] — decisiones del equipo y reglas de trabajo (D7, D8, «no forzar resultados», OMIP).
- [[Datos]] — fuentes de datos, cuáles se han añadido y por qué.
- [[Pendiente]] — lo que falta para la entrega.

## Dónde está cada cosa en el repo

- Modelos: `src/cpd/modelos/` (`anual.py`, `largo_plazo.py`, `operacion.py`, `sismico.py`, `gas_tiempo.py`, `medio_plazo.py`, `impacto_local.py`, `socioeconomico.py`, `escenarios.py`, `empresas.py`, `prob_cpd.py`, `metricas.py`).
- Fuentes de datos: `src/cpd/fuentes/` (`ree.py`, `red_capacidad.py`, `suelo.py`, `norma_sismica.py`, `nasa_power.py`, `ine.py`, `ine_tio.py`, `curado.py`, `actualizar.py`).
- Viabilidad: `src/cpd/scoring.py` (filtros + score por bloques) y `src/cpd/simulator.py` (PUE, consumo, OPEX, VAN).
- Informe de previsiones (generado): `docs/analisis/previsiones_1_anio.md`, figuras en `docs/figuras/previsiones/`.
- Metodología: `docs/metodologia/` (01 alcance y decisiones, 06 checklist, 07 estado).
- Mapa web: `frontend/` (Vite + React + MapLibre).

## Cómo se regenera todo

```
.\.venv\Scripts\python.exe -m cpd.modelos --sin-eda   # modelos, figuras e informes
cd frontend; npm run data                              # datos del mapa
.\.venv\Scripts\python.exe -m pytest -q; cd frontend; npm test; npm run build
```
