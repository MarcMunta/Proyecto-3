# Instrucciones para asistentes de IA (AGENTS.md)

Proyecto 3 · Sistema de Predicción de Viabilidad para la Instalación de un CPD (Máster FP IA y Big Data, Stucom). Entrega en Moodle: **15/12/2026**.

## Antes de cualquier tarea

1. Lee `docs/metodologia/00_Indice.md`, `docs/metodologia/03_Flujo_de_trabajo.md`, `docs/metodologia/04_Reglas_de_datos.md` y `docs/metodologia/05_Reglas_de_codigo_y_git.md`.
2. Comprueba la tarea contra `docs/metodologia/06_Checklist_entrega.md` y localiza el ID del requisito que cierra.
3. Si la tarea toca datos, aplica las reglas R-1 a R-16. Nunca inventes valores ni edites `data/raw/`.

## Durante la tarea

- Código, comentarios y nombres en español. Funciones principales con docstring (unidades incluidas).
- Haz commits pequeños y no hagas commit ni push sin que el usuario lo pida.
- Trabaja en una rama `feature/…`, `fix/…`, `docs/…` o `data/…` desde `main`, nunca sobre `main`.
- No subas secretos (`.env`), datos raw grandes ni `.venv/`.
- No cambies código de otros módulos si no hace falta para la tarea.

## Después de la tarea

1. Ejecuta los tests: `.\.venv\Scripts\python.exe -m pytest -q` y, si tocaste el frontend, `cd frontend && npm test && npm run build`.
2. Actualiza el estado y la evidencia de las filas afectadas en `docs/metodologia/06_Checklist_entrega.md` (✅ solo si la evidencia se puede verificar).
3. Di qué queda pendiente o qué se podría mejorar, con IDs de la checklist.
4. Si la tarea cambia el estado del proyecto de forma relevante, actualiza `docs/metodologia/07_Estado_actual.md`.

## Límites

- Ningún dato se inventa. Los datos demo se marcan como "DEMO sintético".
- Los textos del proyecto van en español (de España).
- Las recomendaciones que no vienen de clase se marcan como "recomendación (no viene de clase)".
- No publiques ni subas contenido a servicios externos sin permiso explícito.
