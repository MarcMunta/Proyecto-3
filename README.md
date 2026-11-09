# Proyecto 3 – Sistema de Predicción de Viabilidad para la Instalación de un CPD

Prototipo inicial de un sistema de apoyo a la decisión para elegir municipios españoles donde instalar un
**CPD (centro de procesamiento de datos / data center)**. Dados los parámetros del CPD y los datos de cada
municipio, el sistema:

- Aplica **filtros eliminatorios** y devuelve un estado: `Viable`, `Viable con condiciones` o `No viable`.
- Calcula un **score global 0-100** y sub-scores por bloque, con la lista de **motivos** que explican el resultado.
- **Simula** energía, agua, OPEX, CO2, impacto local, latencia, VAN, ROI y payback.
- Genera una **previsión de demanda eléctrica a 10 años** a partir de datos reales de REData.
- Permite **escenarios** (precio de la electricidad, sequía, tipo de refrigeración) y compara los rankings.

Proyecto del máster *FP IA y Big Data* (Stucom). Entrega: 15/12/2026.

> **AVISO – datos de demostración sintéticos.** Los indicadores de `data/demo/municipios_demo.csv` son
> **inventados aunque plausibles** (los nombres de municipio, códigos INE y coordenadas sí son reales). Sirven
> para probar el sistema y no deben usarse para tomar decisiones. Cada fila lleva `origen_datos = "DEMO sintético"`.
> La única fuente de datos real incluida es la demanda mensual de REData (`data/clean/`).

## Estructura

```
p3-cpd/
  README.md
  requirements.txt          # versiones fijadas (pip freeze del entorno)
  pyproject.toml            # instalación editable del paquete src/cpd
  .env.example              # AEMET_API_KEY, ESIOS_TOKEN (no usados aún)
  config/settings.yaml      # pesos, umbrales, precios y parámetros por defecto
  data/
    demo/municipios_demo.csv  # 28 municipios, datos SINTÉTICOS
    raw/                      # JSON crudos de REData (ignorado por git)
    clean/                    # CSV limpios (ignorado por git)
    curated/                  # reservado
  src/cpd/
    config.py               # carga de settings.yaml y rutas
    simulator.py            # CPDParams y fórmulas (energía, agua, OPEX, CO2, latencia, VAN...)
    scoring.py              # filtros, sub-scores, score global, ranking, escenarios
    forecast.py             # previsión mensual baseline (tendencia + estacionalidad)
    etl/ree.py              # extractor REData (demanda mensual)
  app/streamlit_app.py      # simulador y dashboard (6 pestañas)
  tests/                    # pytest: simulador, scoring, previsión
  scripts/run_app.ps1       # activa el venv y lanza Streamlit
```

## Instalación (Windows, PowerShell)

Requisitos: Python 3.13 y Git.

```powershell
git clone https://github.com/MarcMunta/Proyecto-3.git
cd Proyecto-3
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

Si PowerShell bloquea la activación del venv, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, o usa siempre `.\.venv\Scripts\python.exe`.

Copia `.env.example` a `.env` solo si vas a usar las APIs de AEMET o ESIOS (todavía no integradas).

## Cómo ejecutar la aplicación

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_app.ps1
```

o directamente: `.\.venv\Scripts\streamlit.exe run app\streamlit_app.py`. Se abre en http://localhost:8501.

Pestañas: **Ranking**, **Mapa**, **Ficha municipio**, **Económico**, **Previsión demanda** y **Escenarios**.
La barra lateral permite cambiar los parámetros del CPD y los pesos del score global.

## Cómo ejecutar los tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Descargar la demanda real (REData)

No requiere clave. Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m cpd.etl.ree --inicio 2015 --fin 2025
```

Genera `data/raw/ree/<YYYYMMDD>/demanda_<año>.json` y `data/clean/ree_demanda_mensual.csv`
(columnas `fecha`, `demanda_mwh`). Sin ese CSV, la pestaña de previsión explica cómo generarlo.

## Metodología resumida

1. **Filtros eliminatorios** (`scoring.aplicar_filtros`): zona inundable, Red Natura, distancia a subestación
   para CPD > 20 MW, capacidad de acceso, latencia, y estrés hídrico con refrigeración evaporativa → `No viable`.
   Sismicidad ≥ 0,16 g, estrés hídrico con aire/inmersión, temperatura máxima ≥ 44 °C o poco suelo industrial
   → `Viable con condiciones`.
2. **Sub-scores 0-100** por bloque (energía, agua y refrigeración, conectividad, riesgos, suelo y regulación,
   costes, mercado y talento, impacto) mediante normalización min-max entre municipios, con el sentido correcto
   (p. ej. menor distancia o precio = mejor).
3. **Score global** = media ponderada de los sub-scores con los pesos de `config/settings.yaml`.
4. **Ranking**: primero los viables, luego los condicionados y al final los no viables; dentro de cada grupo, por score.
5. **Simulador** (`simulator.py`): consumo = potencia TI × factor de carga × PUE × 8760 h; PUE estimado por
   municipio con una heurística (no es un modelo físico); OPEX = energía + agua + personal + mantenimiento +
   impuestos; ingresos = alquiler de capacidad + energía repercutida al cliente (`repercusion_energia_pct`);
   VAN, ROI y payback sobre ingresos menos OPEX.
6. **Previsión** (`forecast.py`): tendencia lineal anual × estacionalidad mensual media; intervalo aproximado.
   Es una **línea base** para comparar después con SARIMA o Prophet.

## Limitaciones conocidas

- Todos los umbrales y precios de `config/settings.yaml` son **valores iniciales a calibrar**.
- El modelo económico es simplificado: flujos constantes, sin inflación ni degradación, y un porcentaje fijo de
  energía repercutida al cliente (80 % por defecto). Si se pone a 0, el VAN sale negativo en todos los municipios.
- El PUE estimado y la latencia son aproximaciones; la latencia usa la distancia en línea recta al IXP más
  próximo por la fórmula de `simulator.latencia_rtt_ms`.
- La previsión no modela ciclos económicos, regulación ni el efecto de un nuevo CPD sobre la demanda.
- Los datos de municipios son sintéticos; el ETL de REData sí usa datos reales.
