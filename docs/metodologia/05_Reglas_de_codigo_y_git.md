---
tags: [metodologia, git, codigo, p3]
estado: borrador
actualizado: 2026-11-14
---

# 05 · Reglas de código y Git

Volver a [[00_Indice]]. Relacionadas: [[04_Reglas_de_datos]], [[08_Plantillas]], [[03_Flujo_de_trabajo]].

El repositorio público es `MarcMunta/Proyecto-3` (rama `main`). Lo que sigue es la forma de trabajar en equipo, basada
en las prácticas de clase [C1 p.6-13] y en recomendaciones marcadas como tales.

## 1. Ramas

**Rama principal:** `main`. Está protegida en la práctica: nadie hace commits directos en `main` (recomendación, no viene de clase).

**Nombres de rama** (como en la clase [C1 p.10-11]):

| Tipo | Patrón | Ejemplo |
|---|---|---|
| Funcionalidad | `feature/<tema>` | `feature/features-lags`, `feature/eda-correlacion` |
| Corrección | `fix/<tema>` | `fix/codigo-ine-ceros` |
| Documentación | `docs/<tema>` | `docs/manual-instalacion` |
| Datos | `data/<tema>` | `data/ingesta-aemet` |

Las ramas se nombran en minúsculas, sin tildes, con guiones.

**Flujo** (comandos de la clase [C1 p.11], adaptados a `main`):

```powershell
git fetch origin
git checkout main
git pull --rebase origin main
git checkout -b feature/mi-tema
# ... trabajo, commits ...
git push -u origin feature/mi-tema
```

> Nota: la clase usa la rama `develop` como base [C1 p.11]. El repositorio trabaja sobre `main`.
> **Decisión pendiente** del equipo: usar solo `main` (recomendado para un equipo pequeño) o crear `develop`.
> Hasta que se decida, la base es `main`.

**Rebase o merge.** Antes de abrir una PR, actualizar la rama con `git pull --rebase` [C1 p.11]. No reescribir ramas que ya están compartidas (sin `push --force` en ramas de otros).

## 2. Commits

**Formato: Conventional Commits en español.** Cabecera corta en imperativo y, si hace falta, cuerpo con el porqué.

```
tipo(ámbito): resumen en imperativo

Cuerpo opcional con el motivo del cambio y el impacto.
```

Tipos: `feat` (nueva funcionalidad), `fix` (corrección), `docs` (documentación), `test` (tests), `refactor` (sin cambio de comportamiento), `data` (cambios en datos o ingesta), `chore` (mantenimiento).

Ejemplos:

- `feat(features): añade lags de 1, 3 y 12 meses al panel`
- `fix(curado): mantiene el cero inicial del código INE`
- `docs(metodologia): completa la checklist de la fase 4`

**Reglas:**
- Commits pequeños: un cambio lógico por commit.
- Un commit no mezcla código y datos regenerados. Los datos regenerados van en un commit aparte (`data(...)`).
- Nunca commitear: `.env`, claves, contraseñas, tokens, datos raw grandes (ver [[04_Reglas_de_datos]], R-14), `node_modules/`, `.venv/`.
- Antes de commitear: `git status` y revisar qué entra.

## 3. Pull requests

- Toda rama entra en `main` mediante **PR**.
- La PR usa la plantilla `.github/pull_request_template.md` (ver [[08_Plantillas]]).
- **Revisión:** al menos **un compañero** revisa y aprueba antes de integrar (recomendación, no viene de clase; la clase habla de revisión de grupo [C1 p.10]).
- Quien abre la PR no aprueba su propia PR.
- Título de la PR en el mismo formato que los commits.
- Si la PR cambia datos, indicar fuente, fecha y hash SHA-256.

## 4. Tests antes de la PR (obligatorio)

Desde la raíz del repo, en PowerShell:

```powershell
# Python: simulador, scoring, previsión, ingesta, datos
.\.venv\Scripts\python.exe -m pytest -q

# Frontend: tests y build
cd frontend
npm test
npm run build
cd ..
```

- Ningún PR se integra con tests en rojo.
- Si se añade una función a `src/cpd/`, debe tener al menos un test.
- Si se cambia un umbral o una fórmula, el test se actualiza **con una explicación** en el commit.

## 5. Código: estructura y convenciones

**Carpetas** (regla de la clase: "cada cosa en su sitio" [C1 p.12-13]):

| Carpeta | Qué va | Estado en el repo |
|---|---|---|
| `src/cpd/` | Lógica del sistema (simulador, scoring, previsión, almacén, fuentes) | Existe |
| `src/ingesta/` | Scripts de descarga de la fase de ingesta | Existe |
| `config/` | Configuración global (`settings.yaml`) | Existe |
| `data/raw/`, `data/clean/`, `data/curated/`, `data/almacen/` | Datos por capas (la mayoría fuera de git) | Existe |
| `notebooks/` | Análisis exploratorio y reportes | **Pendiente** |
| `tests/` | Pruebas automáticas y fixtures | Existe |
| `app/` | Aplicación Streamlit | Existe |
| `frontend/` | Mapa web (Vite + React) | Existe |
| `scripts/` | Scripts de PowerShell (ejecutar, descargar datos) | Existe |
| `docs/` | Documentación, metodología y manuales | Existe |
| `utils/` | Funciones auxiliares sueltas (propuesta de la clase [C1 p.13]) | No existe; las utilidades están en `src/cpd/` y `src/ingesta/utils.py` (decisión: no crear `utils/` para no duplicar) |

**Nombres:** español, claros y sin abreviaturas raras (`coste_energia_eur`, no `ce`). Funciones en `minusculas_con_guiones_bajos`; clases en `PascalCase`.

**Comentarios (requisito del enunciado).** Cada función principal lleva una **docstring** breve en español que dice qué hace, qué recibe, qué devuelve y las unidades. El enunciado pide comentarios "en las funciones principales" [E, entregables]; la rúbrica de nivel 6 pide un código "perfectamente organizado" [E, rúbrica].

```python
def coste_energia_eur(consumo_mwh: float, autoproduccion_mwh: float, precio_eur_mwh: float) -> float:
    """Coste anual de energía comprada (€).

    Args:
        consumo_mwh: consumo anual total del CPD (MWh).
        autoproduccion_mwh: energía propia que no se compra (MWh).
        precio_eur_mwh: precio de compra (€/MWh).
    """
```

**Enumeraciones.** Las categorías cerradas (tipo de refrigeración, tier, estado de viabilidad) se definen como `enum` (en Python, `enum.Enum` o `StrEnum`) y no como cadenas repetidas [C1 p.13]. Hoy no hay ninguna enumeración en `src/`: pendiente.

**Configuración.** Umbrales, pesos y precios en `config/settings.yaml`, no en el código. Cada valor con un comentario de unidad y de origen (ver [[04_Reglas_de_datos]], R-16).

**Secretos.** Claves de API en `.env` (ignorado por git). En el repo solo `.env.example` con nombres de variables y valores vacíos.

**Rutas.** Usar `pathlib` y rutas relativas a la raíz del proyecto (`cpd.config`), nunca rutas absolutas de un ordenador.

## 6. Notebooks

- Un notebook por tema: `01_eda_panel.ipynb`, `02_correlacion.ipynb`, `03_previsiones.ipynb`.
- Primera celda: cabecera con la plantilla de [[08_Plantillas]] (objetivo, entradas, salidas, autor, fecha).
- Se ejecuta **de arriba abajo** antes de commitear (`Kernel → Restart & Run All`).
- Las salidas grandes (tablas de miles de filas) se borran antes de commitear. Las figuras que van a informe se guardan en `docs/figuras/`.
- Los notebooks no contienen claves ni rutas personales.
- Lo que se reutiliza, se pasa a `src/cpd/` como función con test.

## 7. Dashboards y frontend

- Todo cálculo de la app sale de `src/cpd/` (no duplicar fórmulas en la interfaz).
- Antes de una PR que cambia la interfaz, probarla en navegador en escritorio y en móvil (ancho de 375 px).
- `npm test` y `npm run build` deben pasar.

## 8. Entregas y etiquetas

- Para la entrega del 15/12/2026 se crea una etiqueta (`git tag v1.0-entrega`) sobre `main` (recomendación, no viene de clase).
- El repositorio entregado contiene solo código, documentos y configuración. Los datos se obtienen con `scripts/descargar_datos_raw.ps1` o con la ingesta.

## 9. Seguridad y privacidad (repositorio público)

- Antes de hacer público un cambio, buscar claves (`grep -i "api_key\|token\|password"`).
- No subir fotos ni datos personales de compañeros.
- Si se sube una clave por error: **revocarla primero**, después limpiar el historial. Avisar al equipo.

## 10. Checklist antes de abrir una PR

- [ ] La rama sale de `main` actualizada.
- [ ] `pytest` pasa y `npm test` + `npm run build` pasan.
- [ ] Las funciones nuevas tienen docstring en español y, si aplica, un test.
- [ ] No hay secretos ni datos raw grandes en el diff.
- [ ] La plantilla de PR está rellenada.
- [ ] [[06_Checklist_entrega]] se ha actualizado para los requisitos que este cambio cierra.
