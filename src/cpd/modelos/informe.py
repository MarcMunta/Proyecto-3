"""Informes en Markdown generados a partir de los resultados (R-15: cada cifra se regenera con un comando).

Escribe `docs/analisis/eda_panel.md`, `docs/analisis/metricas.md`, `docs/modelos/demanda_ccaa.md` y
`docs/modelos/prob_cpd.md`. No editar a mano: se sobrescriben con `python -m cpd.modelos`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

AVISO = "> Generado por `python -m cpd.modelos` el {fecha}. No editar a mano: se sobrescribe al volver a ejecutar."


def _n(valor: float | None, decimales: int = 1) -> str:
    """Número en formato español (punto de miles, coma decimal)."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _tabla(df: pd.DataFrame) -> str:
    """DataFrame → tabla Markdown (sin dependencias extra)."""
    cabecera = "| " + " | ".join(str(c) for c in df.columns) + " |"
    separador = "|" + "|".join("---" for _ in df.columns) + "|"
    filas = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in fila) + " |" for fila in df.itertuples(index=False)]
    return "\n".join([cabecera, separador, *filas])


NOMBRES_MODELO = {
    "naive": "Último valor (naive)",
    "estacional": "Mismo mes del año anterior (estacional)",
    "tendencia_estacionalidad": "Tendencia + estacionalidad (`forecast.py`)",
    "media_12m": "Media de los últimos 12 meses (la del simulador)",
    "ets": "ETS (Holt-Winters amortiguado)",
    "ridge_gas": "Ridge con gas (ML)",
    "estacional_tendencia": "Mismo mes del año anterior × tendencia",
    "combinacion": "Combinación de los 3 mejores",
    "climatologia": "Climatología (media del mes en los años anteriores)",
    "anomalia_persistente": "Anomalía persistente (φ común)",
    "anomalia_por_cuenca": "Anomalía persistente (φ de cada cuenca)",
    "anomalia_por_provincia": "Anomalía persistente (φ de cada provincia)",
    "anomalia_por_comunidad": "Anomalía persistente (φ de cada comunidad)",
    "ets_5_anios": "ETS de 5 años con tendencia amortiguada",
    "ets_5_anios_sin_tendencia": "ETS de 5 años sin tendencia",
    "ets_5_anios_log": "ETS de 5 años sobre el logaritmo",
    "persistencia": "Persistencia (como el año anterior)",
    "ridge_anomalias": "Ridge sobre anomalías con la reserva de los embalses (ML)",
    "suma_tecnologias": "Suma de tecnologías (ETS de solar, eólica, hidráulica y resto)",
    "tecnologias_hidro_embalses": "Suma de tecnologías con la hidráulica desde los embalses",
    "estructural_gas_tiempo": "Precio estructural con el gas y el tiempo previstos",
    "futuros_gas": "Futuros del gas (MIBGAS)",
    "sin_cambio": "Sin cambio (último año)",
    "media_3_anios": "Media de 3 años",
    "deriva": "Deriva (cambio medio anual)",
    "tendencia_lineal": "Tendencia lineal",
    "holt_amortiguado": "Holt con tendencia amortiguada",
    "media_10_anios": "Media de 10 años",
    "media_larga": "Media larga (30 años)",
    "tendencia_30_anios": "Tendencia lineal de 30 años",
    "media_10_con_tendencia": "Media de 10 años + tendencia de 30",
    "ridge": "Ridge (ML)",
    "gradient_boosting": "Gradient boosting (ML)",
    "mayoritaria": "Clase mayoritaria (baseline)",
    "solo_poblacion": "Logística solo con población (baseline)",
    "logistica": "Logística con todas las features (ML)",
    "bosque": "Random forest (ML)",
}


def _tabla_metricas_demanda(metricas: pd.DataFrame) -> str:
    tabla = metricas.pivot_table(index=["modelo", "configuracion"], columns="particion", values=["mae", "rmse", "mape_pct"], sort=False)
    filas = []
    for (modelo, config), fila in tabla.iterrows():
        filas.append(
            {
                "Modelo": NOMBRES_MODELO.get(modelo, modelo),
                "Configuración": config,
                "MAPE validación": f"{_n(fila[('mape_pct', 'validacion')], 2)} %",
                "MAPE test": f"{_n(fila[('mape_pct', 'test')], 2)} %",
                "MAE test (GWh)": _n(fila[("mae", "test")] / 1e3, 1),
                "RMSE test (GWh)": _n(fila[("rmse", "test")] / 1e3, 1),
            }
        )
    return _tabla(pd.DataFrame(filas))


def informe_eda(eda: dict[str, Any], fecha: str) -> str:
    """Informe de análisis exploratorio (`docs/analisis/eda_panel.md`)."""
    fig = {k: "../../" + v for k, v in eda["figuras"].items()}
    resumen = eda["resumen"].copy()
    resumen["nulos_pct"] = resumen["nulos_pct"].map(lambda v: f"{_n(v, 1)} %")
    resumen = resumen.rename(columns={"columna": "Columna", "tipo": "Tipo", "nulos_pct": "Nulos", "minimo": "Mínimo", "maximo": "Máximo", "distintos": "Distintos"})
    sp = eda["correlaciones"]["spearman"]
    pe = eda["correlaciones"]["pearson"]
    et = eda["etiquetas"]
    filas_corr = []
    for col in [c for c in sp.columns if c not in ("n_centros_datos", "van_meur", "score_viabilidad")]:
        fila = {"Variable": et[col], "Spearman con nº CPD": _n(sp.loc[col, "n_centros_datos"], 2), "Pearson con nº CPD": _n(pe.loc[col, "n_centros_datos"], 2)}
        if "score_viabilidad" in sp.columns:
            fila["Spearman con score"] = _n(sp.loc[col, "score_viabilidad"], 2)
            fila["Spearman con VAN"] = _n(sp.loc[col, "van_meur"], 2)
        filas_corr.append(fila)
    colineales = "\n".join(f"- {et.get(a, a)} y {et.get(b, b)}: Spearman {_n(r, 2)}" for a, b, r in eda["colineales"]) or "- Ninguno."
    diferencias = "\n".join(f"- {et.get(a, a)} y {et.get(b, b)}: |Pearson − Spearman| = {_n(r, 2)}" for a, b, r in eda["diferencias_pearson_spearman"][:6]) or "- Ninguna."
    atipicos = eda["atipicos_demanda"].assign(
        mes=lambda d: d["mes"].dt.strftime("%Y-%m"),
        demanda_gwh=lambda d: (d["demanda_mwh"] / 1e3).map(lambda v: _n(v, 1)),
        cociente_interanual=lambda d: d["cociente_interanual"].map(lambda v: _n(v, 2)),
    )[["ccaa", "mes", "demanda_gwh", "cociente_interanual", "motivo_atipico"]]
    atipicos.columns = ["Comunidad", "Mes", "Demanda (GWh)", "Cociente interanual", "Motivo"]
    tabla_prov = eda["tabla_provincias"]
    n_cpd = int(tabla_prov["n_centros_datos"].sum())
    con = int((tabla_prov["n_centros_datos"] > 0).sum())
    corr_temp_van = sp.loc["tmedia_anual_c", "van_meur"] if "van_meur" in sp.columns else float("nan")
    corr_cpd_van = sp.loc["n_centros_datos", "van_meur"] if "van_meur" in sp.columns else float("nan")
    c = eda["cifras"]
    meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    precio = c["precio_anual"]
    asim = c["asimetria"]
    dem = c["demanda_anual_twh"]
    reservas = "; ".join(f"{a}: mínimo del {_n(v, 1)} % en {m}" for a, (m, v) in c["minimos_reserva"].items())
    rango_pre = (min(precio[a] for a in range(2015, 2020) if a in precio), max(precio[a] for a in range(2015, 2020) if a in precio))
    rango_post = (min(v for a, v in precio.items() if a >= 2024), max(v for a, v in precio.items() if a >= 2024))
    return f"""# Informe de análisis exploratorio · panel provincia × mes

{AVISO.format(fecha=fecha)}

Fase 4 de [la metodología](../metodologia/03_Flujo_de_trabajo.md). Responde a B5 (EDA) y B6 (correlaciones con la
viabilidad) de la [checklist](../metodologia/06_Checklist_entrega.md). Código: `src/cpd/modelos/eda.py`.

## 1. Resumen general

**Datos.** `data/curated/panel_provincia_mes`: {_n(eda['filas_panel'], 0)} filas (52 provincias × meses de
{eda['rango_meses'][0]} a {eda['rango_meses'][1]}) y {eda['columnas_panel']} columnas. Una fila = provincia × mes (R-11).
Las variables de comunidad (demanda, capacidad de acceso, estrés hídrico) se repiten en cada provincia de la comunidad.

<details><summary>Tabla de una página: tipo, nulos, rango y cardinalidad de cada columna</summary>

{_tabla(resumen)}

</details>

**Nulos que importan.** El PVPC solo existe desde junio de 2021; la renta del INE llega hasta 2024; las reservas de
embalses no cubren Baleares, Canarias, Ceuta ni Melilla; el índice de sequía necesita 12 meses previos. No se imputa
nada en el panel (R-1); los modelos tratan los huecos a su manera y lo documentan.

## 2. Distribuciones (univariante)

![Histogramas]({fig['histogramas']})

**Figura 1.** Histogramas de las variables mensuales. Las horas de free cooling tienen forma de U: muchos meses con
el 100 % (invierno) o casi el 0 % (verano en el sur). La precipitación (asimetría {_n(asim['precipitacion_mes_mm'], 2)}) y el
precio spot ({_n(asim['precio_spot_medio_mes_eur_mwh'], 2)}) tienen una cola larga a la derecha; la renta
({_n(asim['renta_neta_media_persona_eur'], 2)}) y el paro ({_n(asim['paro_por_1000_hab'], 2)}) son algo asimétricos. En las
variables con cola larga conviene el logaritmo o Spearman (C4 p.25; C2 p.23).

![Box plots]({fig['boxplots']})

**Figura 2.** Box plots. La temperatura tiene una estacionalidad clara: la mediana va de {_n(c['temp_mediana_min'][1], 1)} °C en
{meses[c['temp_mediana_min'][0]]} a {_n(c['temp_mediana_max'][1], 1)} °C en {meses[c['temp_mediana_max'][0]]}. El precio spot
cambia de nivel por años: media de {_n(precio.get(2022), 1)} €/MWh en 2022 frente a {_n(precio.get(2019), 1)} en 2019. 2022
es un atípico real (crisis del gas), no un error, y se conserva (R-10).

## 3. Series temporales

![Demanda por comunidad]({fig['serie_demanda']})

**Figura 3.** Demanda eléctrica mensual de las seis comunidades con más consumo. Se ven la estacionalidad (picos en
invierno y verano), la caída del confinamiento (abril de 2020) y una bajada lenta después: la suma de las 19
comunidades pasa de {_n(dem.get(2021), 1)} TWh en 2021 a {_n(dem.get(2023), 1)} TWh en 2023. Las cruces son datos atípicos que
se excluyen del modelado (ver el apartado 7).

![Precio y agua]({fig['series_precio_agua']})

**Figura 4.** Precio spot mensual y reserva de los embalses de cuatro ámbitos ({reservas}). El precio baja desde el
máximo de 2022 a una media anual de {_n(rango_post[0], 0)}-{_n(rango_post[1], 0)} €/MWh en 2024-2026, todavía por encima de
2015-2019 ({_n(rango_pre[0], 0)}-{_n(rango_pre[1], 0)} €/MWh).

## 4. Centros de datos y variables por provincia

![CPD por provincia]({fig['barras_cpd']})

**Figura 5.** {n_cpd} centros de datos en {con} provincias (PeeringDB). Madrid y Barcelona concentran el
{_n(100 * tabla_prov['n_centros_datos'].nlargest(2).sum() / max(n_cpd, 1), 0)} %. La etiqueta del modelo `prob_cpd` es
"tiene al menos uno" ({con} de 52 provincias).

![Dispersión]({fig['dispersion']})

**Figura 6.** Izquierda: los CPD aparecen en las provincias más pobladas (relación monótona pero no lineal: por eso se
usa Spearman y el logaritmo de la población). Derecha: el score de viabilidad simulado sube con el free cooling.

## 5. Correlaciones (Pearson, Spearman y Kendall)

**Método.** Matrices de correlación por provincia (n = 52) con Pearson (lineal, sensible a atípicos) y Spearman
(monótona, por rangos) [C2 p.23-24]. Kendall se calcula en el código (`cpd.modelos.eda.correlaciones`) para
comprobar la robustez con una muestra tan pequeña.

![Pearson]({fig['correlacion_pearson']})

![Spearman]({fig['correlacion_spearman']})

**Figuras 7 y 8.** Matrices de correlación de Pearson y Spearman.

{_tabla(pd.DataFrame(filas_corr))}

**Interpretación.**

- **Correlación no es causalidad** [C2 p.18-21]. Que las provincias con más población tengan más CPD no prueba que la
  población los atraiga: también se concentran allí la fibra, los IXP, las empresas clientes y la demanda.
- El **número de CPD** se relaciona sobre todo con la población (Spearman {_n(sp.loc['log_poblacion', 'n_centros_datos'], 2)}).
  El clima y el agua apenas se relacionan con dónde están hoy los CPD.
- El **VAN simulado** depende casi solo de la temperatura (Spearman {_n(corr_temp_van, 2)}): en el simulador, la única
  diferencia económica entre provincias es el PUE, que se estima a partir del clima. Por eso el VAN solo varía unos
  pocos millones entre provincias y la clase de rentabilidad del mapa es tan sensible.
- El VAN simulado y el número real de CPD van en **sentido contrario** (Spearman {_n(corr_cpd_van, 2)}): el simulador
  premia el clima frío, mientras que el mercado se ha instalado donde están la conectividad y los clientes. Es una
  limitación del simulador que hay que explicar en la memoria y que el modelo `prob_cpd` ayuda a ver.

**Multicolinealidad** (|Spearman| ≥ 0,8, recomendación, no viene de clase):

{colineales}

Decisión: en los modelos se conserva el % de free cooling o la temperatura con cuidado; en la regresión logística, la
regularización L2 reparte el peso entre las dos.

**Diferencias grandes entre Pearson y Spearman** (indican atípicos o relaciones no lineales):

{diferencias}

## 6. Pair plot

![Pair plot]({fig['pair_plot']})

**Figura 9.** Pair plot de cuatro variables por provincia, en naranja las que tienen CPD. Las provincias con CPD se
separan sobre todo por la población; en renta, free cooling y estrés hídrico se mezclan con las demás.

## 7. Datos atípicos de la demanda (R-10)

Regla (`cpd.fuentes.calidad.marcar_atipicos_demanda`, aplicada en el curado): demanda ≤ 0, cociente con el mismo mes
del año anterior fuera de [0,6; 1,6] o mes en el que fallan la mitad o más de las comunidades peninsulares (fallo de
la fuente). Los valores marcados quedan en NaN en el panel; el original y el motivo se guardan en
`data/curated/calidad_demanda_ccaa.csv`.

{_tabla(atipicos)}

**Causa (comprobada el 17/11/2026 con `balance/balance-electrico` de REData).** En julio y agosto de 2026 REData aún
no publica el *saldo de intercambios* de las comunidades peninsulares, y su "demanda en barras de central" es solo la
generación propia: Madrid sale con 72.822 + 50.297 = 123.120 MWh (lo habitual son unos 2.500.000), Cantabria en
negativo y Extremadura o Castilla-La Mancha con cifras de generación. En octubre de 2025 el saldo de intercambios de
Asturias (−289.536 MWh), Navarra y el País Vasco cambia de signo o se dispara y la demanda cae a la mitad. Son datos
provisionales de la fuente, no errores de nuestro proceso: el fichero raw ya los trae así.

**Decisión.** No se corrigen a mano ni se inventan (R-1): quedan en NaN y registrados. Los modelos recortan los huecos
del final y sustituyen los intermedios por el mismo mes del año anterior solo como entrada, marcados con `imputado`.
`cpd.fuentes.ree` vuelve a pedir la demanda de un año hasta 12 meses después de acabar, así que la próxima
actualización (`python -m cpd.fuentes.actualizar`) recogerá las correcciones cuando REData las publique.

## 8. Limitaciones

- n = 52 provincias: cualquier correlación por provincia tiene mucha incertidumbre (una correlación de 0,3 no es
  significativa con este tamaño).
- Las variables de comunidad autónoma se repiten en sus provincias: no aportan variación dentro de la comunidad.
- PeeringDB recoge los centros de datos que se registran para interconexión, no todos los CPD de España.
- El score y el VAN vienen de la simulación del mapa (`frontend/public/data/provincias_simuladas.json`), que usa
  supuestos a calibrar (R-16).

## 9. Decisiones que apoya

1. Modelo de demanda por comunidad con features relativas al nivel reciente (las comunidades tienen escalas muy
   distintas) y con los atípicos de REData excluidos.
2. Modelo `prob_cpd` con el logaritmo de la población y sin `n_ixp` ni `distancia_ixp_km` (fuga).
3. Revisar el simulador: hoy solo distingue provincias por el clima.
"""


def _tabla_metricas_precio(metricas: pd.DataFrame) -> str:
    """Tabla de MAE por modelo: todos los horizontes en validación y test, y por horizonte en test (€/MWh)."""
    filas = []
    for modelo, grupo in metricas.groupby("modelo", sort=False):
        g = grupo.set_index(["particion", "horizonte"])
        fila = {
            "Modelo": NOMBRES_MODELO.get(modelo, modelo),
            "Configuración": grupo["configuracion"].iloc[0],
            "MAE validación": _n(g.loc[("validacion", "todos"), "mae"], 1),
            "MAE test": _n(g.loc[("test", "todos"), "mae"], 1),
            "RMSE test": _n(g.loc[("test", "todos"), "rmse"], 1),
        }
        for h in ("1", "3", "6", "12"):
            fila[f"MAE test h={h}"] = _n(g.loc[("test", h), "mae"], 1)
        filas.append(fila)
    return _tabla(pd.DataFrame(filas))


def _seccion_precio(precio: dict[str, Any]) -> str:
    """Sección de métricas del precio de la luz para `metricas.md`."""
    r = precio["resultado"]
    e = r["elegido"]
    bt = precio["backtest"].assign(abs=lambda d: d["error_eur_mwh"].abs())
    resumen_bt = bt.groupby("modelo")["abs"].agg(["mean", "max"]).sort_values("mean").reset_index()
    tabla_bt = pd.DataFrame(
        {
            "Modelo": resumen_bt["modelo"].map(lambda m: NOMBRES_MODELO.get(m, m)),
            "Error medio de la media anual (€/MWh)": resumen_bt["mean"].map(lambda v: _n(v, 1)),
            "Peor origen (€/MWh)": resumen_bt["max"].map(lambda v: _n(v, 1)),
        }
    )
    return f"""## Regresión: precio medio mensual de la electricidad (spot, €/MWh)

Un solo modelo para los horizontes de 1 a 12 meses. Métrica principal: **MAE en €/MWh** (cada €/MWh de error es
coste de energía mal estimado; el MAPE se dispara en los meses con precios muy bajos). Validación
{precio['periodos']['validacion']}; test {precio['periodos']['test']}, usado una vez.

{_tabla_metricas_precio(r['metricas'])}

Modelo elegido con la validación: **{NOMBRES_MODELO.get(e['modelo'], e['modelo'])}** ({e['configuracion']}).

### Backtesting de la media de los 12 meses siguientes (orígenes trimestrales 2020-2023)

{_tabla(tabla_bt)}

Es lo que usa el simulador: el precio medio del año siguiente. Detalle en la [ficha del modelo](../modelos/precio_luz.md)."""


def informe_metricas(demanda: dict[str, Any], prob: dict[str, Any], fecha: str, precio: dict[str, Any] | None = None) -> str:
    """Tabla de métricas de todos los modelos y baselines (`docs/analisis/metricas.md`)."""
    secciones = []
    for h, resultado in demanda["resultados"].items():
        e = resultado["elegido"]
        secciones.append(
            f"### Demanda por comunidad a {h} {'mes' if h == 1 else 'meses'} vista\n\n"
            f"{_tabla_metricas_demanda(resultado['metricas'])}\n\n"
            f"Modelo elegido con la validación: **{NOMBRES_MODELO.get(e['modelo'], e['modelo'])}** ({e['configuracion']})."
        )
    bt = demanda["backtesting"]
    if not bt.empty:
        resumen_bt = bt.groupby("modelo")["mape_pct"].agg(["mean", "min", "max"]).sort_values("mean").reset_index()
        resumen_bt = pd.DataFrame(
            {
                "Modelo": resumen_bt["modelo"].map(lambda m: NOMBRES_MODELO.get(m, m)),
                "MAPE medio": resumen_bt["mean"].map(lambda v: f"{_n(v, 2)} %"),
                "Mejor corte": resumen_bt["min"].map(lambda v: f"{_n(v, 2)} %"),
                "Peor corte": resumen_bt["max"].map(lambda v: f"{_n(v, 2)} %"),
            }
        )
        cortes = ", ".join(sorted(bt["corte"].unique()))
        secciones.append(f"### Backtesting a 12 meses (cortes: {cortes})\n\n{_tabla(resumen_bt)}")
    m = prob["metricas"].copy()
    tabla_prob = pd.DataFrame(
        {
            "Modelo": m["modelo"].map(lambda x: NOMBRES_MODELO.get(x, x)),
            "Log-loss": m["log_loss"].map(lambda v: _n(v, 3)),
            "ROC-AUC": [("0,500 (constante)" if mo == "mayoritaria" else _n(v, 3)) for mo, v in zip(m["modelo"], m["roc_auc"])],
            "Brier": m["brier"].map(lambda v: _n(v, 3)),
            "Accuracy (umbral 0,5)": m["accuracy"].map(lambda v: f"{_n(100 * v, 1)} %"),
            "Precision": m["precision"].map(lambda v: _n(v, 2)),
            "Recall": m["recall"].map(lambda v: _n(v, 2)),
            "F1": m["f1"].map(lambda v: _n(v, 2)),
        }
    )
    return f"""# Métricas de los modelos

{AVISO.format(fecha=fecha)}

Fase 8 de [la metodología](../metodologia/03_Flujo_de_trabajo.md). **La previsión a 1 año que usa el mapa (con todos los
gráficos) está en [previsiones_1_anio.md](previsiones_1_anio.md).** Fichas de modelo:
[demanda por comunidad](../modelos/demanda_ccaa.md), [probabilidad de CPD](../modelos/prob_cpd.md) y
[precio de la luz](../modelos/precio_luz.md).

## Regresión: demanda eléctrica mensual por comunidad (MWh)

Métricas (recomendación, no vienen de clase: la clase pide medir la distancia al valor real [C3 p.10-11]):

- **MAPE** (métrica principal): error medio en % del valor real. Permite comparar comunidades de tamaños muy
  distintos. Un MAPE del 4 % equivale a equivocarse en unos 140 GWh al mes en Andalucía (que consume unos 3.500 GWh
  al mes) o en 0,7 GWh en Ceuta (unos 17 GWh al mes).
- **MAE**: error medio en GWh; lo dominan las comunidades grandes (Cataluña, Andalucía, Madrid).
- **RMSE**: como el MAE pero castiga más los errores grandes; si es mucho mayor que el MAE, hay meses con fallos
  grandes.

Todas las filas se calculan con los mismos meses y comunidades. Test: usado una vez, con el modelo reentrenado con
entrenamiento + validación.

{(chr(10) * 2).join(secciones)}

## Clasificación: probabilidad de que una provincia tenga CPD

Validación cruzada estratificada repetida (5 × 20); cada provincia se evalúa con modelos que no la han visto.

{_tabla(tabla_prob)}

- **Log-loss** (métrica principal, porque el mapa muestra la probabilidad): castiga las probabilidades seguras y
  equivocadas. Cuanto más baja, mejor. La clase mayoritaria marca el mínimo que hay que superar.
- **ROC-AUC** [C3 p.19]: probabilidad de que una provincia con CPD reciba más probabilidad que una sin CPD.
  0,5 = azar; 1 = perfecto.
- **Paradoja de la exactitud** [C3 p.23]: predecir siempre "no tiene CPD" acierta el
  {_n(100 * (1 - prob['prevalencia']), 1)} % sin servir para nada. Por eso no se elige el modelo por accuracy.

Modelo elegido (menor log-loss): **{NOMBRES_MODELO.get(prob['elegido'], prob['elegido'])}**.

{_seccion_precio(precio) if precio else ""}
"""


def _seccion_control(control: pd.DataFrame, figura: str) -> str:
    """Tabla y gráfico del requisito de acierto (85 % ≤ acierto < 99,9 %)."""
    tabla = pd.DataFrame(
        {
            "Modelo": control["modelo"],
            "Acierto validación / backtesting": control["acierto_validacion"].map(lambda v: f"{_n(v, 1)} %"),
            "Acierto test": control["acierto_test"].map(lambda v: "—" if pd.isna(v) else f"{_n(v, 1)} %"),
            "Cómo se mide": control["definicion"],
            "Estado": control["estado"],
        }
    )
    fallan = control[~control["estado"].str.startswith("cumple")]
    aviso = (
        "Todos los modelos cumplen el requisito."
        if fallan.empty
        else "**No cumplen:** "
        + "; ".join(f"{f.modelo} ({f.estado})" for f in fallan.itertuples())
        + ". Sus previsiones se enseñan solo como escenario, con el aviso, y no se usan como dato en el simulador."
    )
    return f"""## Control de acierto (requisito: 85 % ≤ acierto < 99,9 %)

**Acierto** = 100 × (1 − WAPE), con WAPE = Σ|real − previsto| / Σ|real| (en clasificación, la accuracy). Se usa el
WAPE y no 100 − MAPE porque el MAPE se dispara en los meses con valores muy bajos: un precio de 16 €/MWh con un error
de 30 €/MWh cuenta como un 190 % de error. Un acierto de 99,9 % o más se marca como **sospechoso**: casi seguro
indica una fuga de información. El control se ejecuta en cada `python -m cpd.modelos` y avisa en la consola.

![Control de acierto]({figura})

{_tabla(tabla)}

{aviso}
"""


def _seccion_reservas(reservas: dict[str, Any], figura: str) -> str:
    r = reservas["resultado"]
    t = r["metricas"].pivot(index="modelo", columns="particion", values="acierto_pct").sort_values("validacion", ascending=False)
    m = r["metricas"].pivot(index="modelo", columns="particion", values="mae")
    filas = [
        {
            "Modelo": NOMBRES_MODELO.get(mo, mo) + (" **(elegido)**" if mo == r["elegido"] else (" (en la combinación)" if mo in r["miembros"] else "")),
            "Acierto validación": f"{_n(f['validacion'], 1)} %",
            "Acierto test": f"{_n(f['test'], 1)} %",
            "MAE test (puntos)": _n(m.loc[mo, "test"], 1),
        }
        for mo, f in t.iterrows()
    ]
    o = r["origenes"]
    return f"""## Reservas de agua por ámbito hidrográfico (riesgo hídrico, P4)

Reserva de los embalses (% de la capacidad) de los 16 ámbitos del Boletín Hidrológico (MITECO, desde 1987), mes a
mes, 1 año vista. Candidatos: se mantiene el último mes, mismo mes del año anterior, **climatología** (media del mes en
los 10 años anteriores), **anomalía persistente** (climatología + la anomalía actual, que se va diluyendo con un factor
φ por horizonte ajustado con los años anteriores), la misma con un **φ propio de cada cuenca**, y ETS. Se probó también
la lluvia reciente de la cuenca (NASA POWER): no mejoraba y se descartó.

**Transparencia.** El candidato con φ por cuenca se añadió después de una primera ejecución en la que la combinación
elegida (con «último mes») no llegaba al 85 % en test. La elección sigue siendo con la validación, pero el test de las
reservas ya no es del todo independiente, y su acierto (85,3 %) está justo en el mínimo.

![Reservas por ámbito]({figura})

**Figura 4.** Últimos 3 años y previsión a 1 año de cada ámbito.

{_tabla(pd.DataFrame(filas))}

Validación: orígenes {o['origenes_validacion']}. Test: meses {o['meses_test']}. Error en puntos porcentuales de reserva.
"""


def _seccion_10_anios(diez: dict[str, Any]) -> str:
    r = diez["resultado"]
    ph = r["por_horizonte"].pivot(index="horizonte_anios", columns="modelo", values="mape_pct")
    origenes = r["por_horizonte"].query("modelo == @r['elegido']").set_index("horizonte_anios")["origenes"]
    filas = [
        {"Años vista": h, "Orígenes": int(origenes[h]), **{NOMBRES_MODELO.get(c, c): f"{_n(ph.loc[h, c], 1)} %" for c in [r["elegido"], *[x for x in r["miembros"] if x != r["elegido"]]]}}
        for h in ph.index
    ]
    p = diez["prevision"]
    ultimo = diez["json"]["historia"][-1]
    return f"""## Demanda eléctrica nacional a 10 años (P5)

Demanda anual de España (REData, 2007-{ultimo['anio']}). Backtesting plurianual: desde el final de cada año entre 2011 y
{ultimo['anio'] - 1}, cada modelo prevé los 10 años siguientes (o los que haya). Candidatos: sin cambio, media de 3 años,
deriva, tendencia lineal, Holt amortiguado y la combinación de los 3 mejores.

![Demanda a 10 años]({"../../" + diez["figura"]})

**Figura 11.** Demanda real, lo que el modelo habría previsto desde varios años del pasado y la previsión a 10 años.

MAPE por horizonte (cuantos más años vista, menos orígenes con los que medirlo):

{_tabla(pd.DataFrame(filas))}

**Resultado.** Modelo elegido: **{NOMBRES_MODELO.get(r['elegido'], r['elegido'])}**
({', '.join(NOMBRES_MODELO.get(m, m) for m in r['miembros'])}); acierto en el backtesting **{_n(diez['acierto'], 1)} %**. Previsión:
{_n(p['prevision_twh'].iloc[0], 0)} TWh en {int(p['anio'].iloc[0])} y **{_n(p['prevision_twh'].iloc[-1], 0)} TWh en {int(p['anio'].iloc[-1])}** (intervalo 10-90 %:
{_n(p['inferior_twh'].iloc[-1], 0)}-{_n(p['superior_twh'].iloc[-1], 0)} TWh), frente a {_n(ultimo['valor'], 0)} TWh en {ultimo['anio']}.

**Limitación.** Es una previsión **tendencial**: no incluye la electrificación, el hidrógeno ni los nuevos centros de
datos, que pueden hacer crecer la demanda. Un CPD de 50 MW de TI consume unos 0,46 TWh al año (el 0,2 % de la demanda
nacional). El intervalo a más de 7 años se extrapola (σ·√h) porque hay pocos orígenes para medirlo.
"""


def _seccion_temperatura(temperatura: dict[str, Any], figura: str, figura_mensual: str) -> str:
    """Temperatura media por provincia a 1 año: modelos, acierto (y su límite en °C) y efecto en el PUE."""
    from cpd.simulator import pue_estimado

    r, j = temperatura["resultado"], temperatura["resumen"]
    acierto = r["metricas"].pivot(index="modelo", columns="particion", values="acierto_pct").sort_values("validacion", ascending=False)
    mae = r["metricas"].pivot(index="modelo", columns="particion", values="mae")
    filas = [
        {
            "Modelo": NOMBRES_MODELO.get(mo, mo) + (" **(elegido)**" if mo == r["elegido"] else (" (en la combinación)" if mo in r["miembros"] else "")),
            "Acierto validación": f"{_n(f['validacion'], 1)} %",
            "Acierto test": f"{_n(f['test'], 1)} %",
            "MAE validación (°C)": _n(mae.loc[mo, "validacion"], 2),
            "MAE test (°C)": _n(mae.loc[mo, "test"], 2),
        }
        for mo, f in acierto.iterrows()
    ]
    pred = r["predicciones"].query("modelo == @r['elegido']")
    # Error de la media de 12 meses, que es la que entra en el PUE.
    anual = pred.groupby(["particion", "serie", "origen"]).agg(prevision=("prevision", "mean"), real=("real", "mean"), n=("real", "size"))
    anual = anual[anual["n"] == 12]
    mae_anual = (anual["prevision"] - anual["real"]).abs().groupby(level="particion").mean()
    val = pred.query("particion == 'validacion'")
    acierto_kelvin = 100 * (1 - (val["real"] - val["prevision"]).abs().sum() / (val["real"] + 273.15).sum())
    delta_pue = pue_estimado(15 + mae_anual["validacion"], "aire") - pue_estimado(15, "aire")
    provincias = pd.DataFrame.from_dict(j["provincias"], orient="index").sort_values("media_prevista")
    fria, calida = provincias.iloc[0], provincias.iloc[-1]
    pue_entre = pue_estimado(calida["media_prevista"], "aire") - pue_estimado(fria["media_prevista"], "aire")
    cambio = (provincias["media_prevista"] - provincias["media_12m_actual"]).mean()
    sentido = f"{_n(abs(cambio), 1)} °C {'menos' if cambio < 0 else 'más'} que el último año"
    o = r["origenes"]
    return f"""## Temperatura media por provincia (PUE)

Temperatura media mensual (°C) de las 52 provincias (NASA POWER, desde 2015), 1 año vista. Es la variable con la que
el simulador estima el PUE (`simulator.pue_estimado`) y, con él, el consumo, el OPEX y el VAN: según el EDA, el VAN
simulado depende casi solo de ella. Candidatos: los mismos que las reservas (último mes, mismo mes del año anterior,
climatología, anomalía persistente con un φ común y con un φ propio de cada provincia, y ETS) y la combinación de los 3
mejores. Como los datos empiezan en 2015, la climatología usa todos los años anteriores al origen (hasta 10) y se exige
un mínimo de 5 años de historia.

**Cómo leer el acierto.** Es 100 − WAPE con la temperatura en °C. El °C no tiene un cero natural, así que ese porcentaje
depende de la escala: con el mismo error, en kelvin saldría un {_n(acierto_kelvin, 1)} %, que parece casi perfecto sin decir nada
nuevo. Por eso la cifra que manda es el **error en °C** (MAE). El intervalo de la previsión también va en °C (aditivo),
no en porcentaje.

![Temperatura por provincia]({figura})

**Figura 5.** Temperatura media de las 52 provincias: el último año real (azul) y la previsión de los próximos 12 meses
(naranja) con su intervalo 10-90 % (barra).

{_tabla(pd.DataFrame(filas))}

Validación: orígenes {o['origenes_validacion']}. Test: meses {o['meses_test']}.

**Resultado.** Modelo elegido: **{NOMBRES_MODELO.get(r['elegido'], r['elegido'])}** ({', '.join(NOMBRES_MODELO.get(m, m) for m in r['miembros'])}).
Error de un mes: {_n(mae.loc[r['elegido'], 'validacion'], 2)} °C en validación y {_n(mae.loc[r['elegido'], 'test'], 2)} °C en test. Error de la media de 12 meses, que es
la que usa el PUE: **{_n(mae_anual['validacion'], 2)} °C** en validación y {_n(mae_anual.get('test'), 2)} °C en test. Con la fórmula del simulador,
{_n(mae_anual['validacion'], 2)} °C mueven el PUE {_n(delta_pue, 3)} (un PUE de aire es 1,45), poco frente a los {_n(pue_entre, 3)} que separan la
provincia más fría de la más cálida. Previsión: de {_n(fria['media_prevista'], 1)} °C en {fria['nombre']} a {_n(calida['media_prevista'], 1)} °C en
{calida['nombre']}; de media, {sentido}.

![Temperatura mensual]({figura_mensual})

**Figura 6.** Serie mensual de las 4 provincias más frías y las 4 más cálidas según la previsión: últimos 3 años y
previsión a 1 año con su intervalo.
"""


def _seccion_renovables(renovables: dict[str, Any], figura: str, figura_mensual: str) -> str:
    """% de generación renovable por comunidad a 1 año: modelos, acierto mes a mes y de la media anual, y por qué
    el mes a mes no llega al mínimo si es el caso."""
    from cpd.modelos.metricas import ACIERTO_MINIMO

    r, j = renovables["resultado"], renovables["resumen"]
    acierto = r["metricas"].pivot(index="modelo", columns="particion", values="acierto_pct").sort_values("validacion", ascending=False)
    mae = r["metricas"].pivot(index="modelo", columns="particion", values="mae")
    filas = [
        {
            "Modelo": NOMBRES_MODELO.get(mo, mo) + (" **(elegido)**" if mo == r["elegido"] else (" (en la combinación)" if mo in r["miembros"] else "")),
            "Acierto validación": f"{_n(f['validacion'], 1)} %",
            "Acierto test": f"{_n(f['test'], 1)} %",
            "MAE validación (puntos)": _n(mae.loc[mo, "validacion"], 2),
            "MAE test (puntos)": _n(mae.loc[mo, "test"], 2),
        }
        for mo, f in acierto.iterrows()
    ]
    elegido = r["elegido"]
    por_h = r["por_horizonte"].query("particion == 'validacion' and modelo == @elegido").set_index("horizonte_meses")["acierto_pct"]
    val = r["predicciones"].query("particion == 'validacion' and modelo == @elegido")
    error_ccaa = (val["real"] - val["prevision"]).abs().groupby(val["serie"]).sum().sort_values(ascending=False)
    parte = 100 * error_ccaa / error_ccaa.sum()
    nombre_ccaa = {c: d["nombre"] for c, d in j["ccaa"].items()}
    tres = ", ".join(f"{nombre_ccaa.get(c, c)} ({_n(v, 0)} %)" for c, v in parte.head(3).items())
    ccaa = pd.DataFrame.from_dict(j["ccaa"], orient="index").sort_values("media_prevista")
    cambio = (ccaa["media_prevista"] - ccaa["media_12m_actual"]).mean()
    mensual_val = acierto.loc[elegido, "validacion"]
    no_llega = mensual_val < ACIERTO_MINIMO
    o = r["origenes"]
    explicacion = (
        f"""**¿Por qué el mes a mes no llega al {_n(ACIERTO_MINIMO, 0)} %?** El % renovable de un mes depende del viento, la lluvia y el sol de
ese mes, que no se pueden saber con un año de antelación: el acierto baja de {_n(por_h.iloc[0], 0)} % a 1 mes a {_n(por_h.iloc[-1], 0)} % a 12 meses. Tres
comunidades suman el {_n(parte.head(3).sum(), 0)} % del error de validación: {tres}. En las comunidades con poca generación, una sola
central que para o arranca cambia mucho el porcentaje. Los errores de meses sueltos se compensan en la media de 12 meses, que es la cifra que
interesa para un CPD (un contrato de energía renovable es anual): esa sí cumple. El gráfico mes a mes se enseña como
orientativo, con aviso.
"""
        if no_llega
        else ""
    )
    return f"""## Generación renovable por comunidad autónoma

Porcentaje de la generación eléctrica de cada comunidad que es renovable (REData, mensual desde 2015), 1 año vista. Un
CPD que quiera energía verde la tendrá más fácil (y más barata) donde la red ya es muy renovable. Ceuta queda fuera: no
tiene generación renovable en todo el periodo. Candidatos: los de las reservas y la temperatura (último mes, mismo mes
del año anterior, climatología, anomalía persistente con φ común y por comunidad, ETS), dos ETS con solo los últimos 5
años (con y sin tendencia) y la combinación de los 3 mejores.

**Transparencia.** Las dos ETS de 5 años se añadieron después de una primera prueba en la que la combinación se
quedaba en un 83,8 % en validación: con tanta potencia solar nueva, la historia larga frena la tendencia. La elección
sigue siendo con la validación. La fila de la media de 12 meses del control de acierto se añadió después de ver que el
mes a mes no llegaba al mínimo; las dos filas se enseñan. El 18/11/2026 se añadió un Ridge sobre anomalías con la
reserva de los embalses (más agua, más hidráulica), elegido también con la validación.

![Renovables por comunidad]({figura})

**Figura 7.** % renovable de cada comunidad: el último año real (azul) y la previsión de los próximos 12 meses (naranja)
con su intervalo 10-90 % (barra).

{_tabla(pd.DataFrame(filas))}

Validación: orígenes {o['origenes_validacion']}. Test: meses {o['meses_test']}.

**Resultado.** Modelo elegido: **{NOMBRES_MODELO.get(elegido, elegido)}** ({', '.join(NOMBRES_MODELO.get(m, m) for m in r['miembros'])}).
Mes a mes: {_n(mensual_val, 1)} % de acierto en validación y {_n(acierto.loc[elegido, 'test'], 1)} % en test (error de {_n(mae.loc[elegido, 'validacion'], 1)} y
{_n(mae.loc[elegido, 'test'], 1)} puntos). **% medio de los 12 meses: {_n(j['acierto_anual_validacion'], 1)} % en validación y {_n(j['acierto_anual_test'], 1)} % en test.**
Previsión: de {_n(ccaa['media_prevista'].iloc[0], 0)} % en {ccaa['nombre'].iloc[0]} a {_n(ccaa['media_prevista'].iloc[-1], 0)} % en {ccaa['nombre'].iloc[-1]}; de media,
{_n(abs(cambio), 1)} puntos {'menos' if cambio < 0 else 'más'} que el último año.

{explicacion}
![Renovables mensual]({figura_mensual})

**Figura 8.** % renovable mensual de cada comunidad (de más a menos renovable según la previsión): últimos 3 años y
previsión a 1 año con su intervalo.
"""


def _seccion_cobertura(cobertura: dict[str, Any], figura: str) -> str:
    """Generación renovable (MWh) por comunidad a 1 año y cobertura renovable de la demanda."""
    r, j = cobertura["resultado"], cobertura["resumen"]
    acierto = r["metricas"].pivot(index="modelo", columns="particion", values="acierto_pct").sort_values("validacion", ascending=False)
    filas = [
        {
            "Modelo": NOMBRES_MODELO.get(mo, mo) + (" **(elegido)**" if mo == r["elegido"] else (" (en la combinación)" if mo in r["miembros"] else "")),
            "Acierto validación (mes a mes)": f"{_n(f['validacion'], 1)} %",
            "Acierto test (mes a mes)": f"{_n(f['test'], 1)} %",
        }
        for mo, f in acierto.iterrows()
    ]
    ccaa = pd.DataFrame.from_dict(j["ccaa"], orient="index").dropna(subset=["cobertura_prevista_pct"]).sort_values("cobertura_prevista_pct", ascending=False)
    tabla = pd.DataFrame(
        {
            "Comunidad": ccaa["nombre"],
            "Renovable último año (GWh)": (ccaa["renovable_12m_mwh"] / 1e3).map(lambda v: _n(v, 0)),
            "Demanda último año (GWh)": (ccaa["demanda_12m_mwh"] / 1e3).map(lambda v: _n(v, 0)),
            "Cobertura último año": ccaa["cobertura_actual_pct"].map(lambda v: f"{_n(v, 0)} %"),
            "Cobertura prevista": ccaa["cobertura_prevista_pct"].map(lambda v: f"{_n(v, 0)} %"),
        }
    )
    por_encima = ", ".join(ccaa.loc[ccaa["cobertura_prevista_pct"] > 100, "nombre"])
    o = r["origenes"]
    return f"""## Cobertura renovable por comunidad autónoma

Cuánta energía renovable genera cada comunidad frente a la que consume: **cobertura = generación renovable / demanda**.
Por encima del 100 %, la comunidad genera en renovables más de lo que consume: hay energía verde de sobra para un CPD
nuevo. La generación renovable (MWh, REData) se prevé con los mismos candidatos que el % renovable, una ETS sobre el
logaritmo y, desde el 18/11/2026, la **suma de tecnologías**: solar, eólica, hidráulica y resto se prevén por separado
(cada una con su estacionalidad y su tendencia) y se suman. La demanda, con su propio modelo (arriba). Comunidades por encima del 100 %: {por_encima}.

{_tabla(pd.DataFrame(filas))}

Validación: orígenes {o['origenes_validacion']}. Test: meses {o['meses_test']}. **Total de 12 meses** (la cifra que entra en
la cobertura): **{_n(j['acierto_anual_validacion'], 1)} %** en validación y **{_n(j['acierto_anual_test'], 1)} %** en test. El mes a mes depende del viento, la
lluvia y el sol de cada mes y se enseña solo como orientativo.

![Cobertura renovable]({figura})

**Figura 9.** Cobertura renovable de cada comunidad: último año real (azul) y previsión de los próximos 12 meses
(naranja). La línea discontinua marca el 100 %. La demanda de la península termina en junio de 2026 (ver limitaciones),
así que los dos periodos de 12 meses no coinciden del todo.

{_tabla(tabla)}
"""


def _seccion_operacion(operacion_res: dict[str, Any], figura: str) -> str:
    """Operación del CPD de referencia a 1 año (A3): consumo, emisiones, agua y reserva del ámbito por provincia."""
    j, bt = operacion_res["resumen"], operacion_res["backtesting"]
    tabla = operacion_res["tabla"].copy()
    tabla["nombre"] = tabla["codigo_provincia"].map(lambda c: operacion_res["nombres"].get(c, {}).get("nombre", c))
    menos, mas = tabla.nsmallest(5, "emisiones_t_previsto"), tabla.nlargest(5, "emisiones_t_previsto")
    lista = lambda d: ", ".join(f"{f.nombre} ({_n(f.emisiones_t_previsto / 1e3, 1)} mil t)" for f in d.itertuples())  # noqa: E731
    pue = tabla["pue_previsto"]
    cpd = j["cpd"]
    return f"""## Operación del CPD a 1 año (sostenibilidad operativa, objetivo A3)

Encadena los modelos anteriores con las fórmulas del simulador para un CPD de referencia ({_n(cpd['potencia_ti_mw'], 0)} MW de TI,
carga {_n(100 * cpd['factor_carga'], 0)} %, refrigeración por {cpd['tipo_refrigeracion']}): la **temperatura media prevista** de la provincia da el
PUE y el consumo, y el **% renovable previsto** de su comunidad da las emisiones si el CPD se abastece con el mix de
generación de esa comunidad ({_n(j['factor_emision_t_mwh'], 2)} t CO2 por MWh no renovable). El mercado eléctrico es único, así que
usar el mix de la comunidad es una aproximación (recomendación, no viene de clase). También se da la reserva mínima
prevista de los embalses del ámbito en los próximos 12 meses.

**Validación de punta a punta** ({j['origenes']} orígenes de validación comunes a los dos modelos, {bt['provincias']} provincias): el consumo
del año siguiente calculado con lo previsto acierta un **{_n(j['acierto_consumo'], 1)} %** y las emisiones un **{_n(j['acierto_emisiones'], 1)} %**. El
consumo acierta tanto porque el PUE apenas cambia con la temperatura en la fórmula del simulador (de {_n(pue.min(), 3)} a {_n(pue.max(), 3)}
entre provincias); no hay fuga de información: el dato real de cada año no se usa para prever ese año.

![Emisiones del CPD]({figura})

**Figura 10.** Emisiones anuales del CPD de referencia en cada provincia: último año (azul) y próximos 12 meses
(naranja).

Menos emisiones previstas: {lista(menos)}. Más: {lista(mas)}.
"""


def _seccion_medio_plazo(medio: dict[str, Any], figura: str) -> str:
    """Medio plazo (10 años, A3): temperatura → PUE → consumo del CPD y reserva de agua del ámbito."""
    j = medio["json"]
    t, r = j["temperatura"], j["reservas"]
    base, final = j["anio_base"], j["anio_final"]

    def tabla(res: dict[str, Any], unidad: str) -> str:
        m = res["metricas"].pivot(index="modelo", columns="particion", values=["mae", "acierto"]).sort_values(("mae", "validacion"))
        filas = []
        for modelo, fila in m.iterrows():
            marca = " **(elegido)**" if modelo == res["elegido"] else (" (en la combinación)" if modelo in res["miembros"] else "")
            filas.append({
                "Modelo": NOMBRES_MODELO.get(modelo, modelo) + marca,
                f"MAE validación ({unidad})": _n(fila[("mae", "validacion")], 2), f"MAE test ({unidad})": _n(fila[("mae", "test")], 2),
                "Acierto validación": f"{_n(fila[('acierto', 'validacion')], 1)} %", "Acierto test": f"{_n(fila[('acierto', 'test')], 1)} %",
            })
        return _tabla(pd.DataFrame(filas))

    op = pd.DataFrame.from_dict(j["provincias"], orient="index")
    calidas = op.nlargest(5, "temp_final_c")
    frias = op.nsmallest(5, "temp_final_c")
    lista = lambda d: ", ".join(f"{f.nombre} ({_n(f.temp_final_c, 1)} °C, PUE {_n(f.pue_final, 2)})" for f in d.itertuples())  # noqa: E731
    amb = pd.DataFrame.from_dict(j["ambitos"], orient="index").sort_values("media_decada_prevista_pct")
    bajos = ", ".join(f"{a} ({_n(f.media_decada_prevista_pct, 0)} %)" for a, f in amb.head(4).iterrows())
    nombre_t = NOMBRES_MODELO.get(t["modelo"], t["modelo"])
    nombre_r = NOMBRES_MODELO.get(r["modelo"], r["modelo"])
    return f"""## Medio plazo: clima y agua a 10 años (sostenibilidad operativa, objetivo A3)

El objetivo A3 pide previsiones a corto **y medio plazo** de la sostenibilidad operativa del CPD. A 1 año ya están el
PUE, el consumo y las emisiones; a 10 años ({base + 1}-{final}) lo que cambia la operación es el **clima** (temperatura →
PUE → consumo) y el **agua** de los embalses del ámbito. Código: `src/cpd/modelos/medio_plazo.py`.

**Datos nuevos.** La tabla diaria de clima empieza en 2015 y no basta para validar 10 años. Se añade la temperatura
**mensual de NASA POWER desde {t['historia_desde']}** (la misma fuente y el mismo punto que la diaria: en los meses comunes difieren
0,003 °C de media). Las reservas de MITECO ya venían desde {r['historia_desde']}.

**Protocolo.** Test: lo que se habría previsto desde {t['origen_test']} para {t['origen_test'] + 1}-{t['origen_test'] + 10} (ningún modelo lo ve).
Validación: orígenes {t['origenes_validacion'][0]}-{t['origenes_validacion'][1]} en la temperatura y {r['origenes_validacion'][0]}-{r['origenes_validacion'][1]} en las reservas, cuyos 10 años
previstos terminan antes del test, para que la elección no mire ningún año del test. Candidatos: sin cambio, media de 10
años, media larga (30 años), tendencia lineal de 30 años, media de 10 años más la tendencia, Holt amortiguado y la
combinación de los 3 mejores por MAE de validación.

![Medio plazo]({figura})

**Figura 11b.** (a) Temperatura media anual de España (media de las 52 capitales): real, lo que se habría previsto
desde {t['origen_test']} (test) y previsión a 10 años con su intervalo 10-90 %. (b) Reserva media de los embalses de cada
ámbito: últimos 10 años (azul) y próxima década (naranja).

### Temperatura por provincia a 10 años

{tabla(medio['res_t'], '°C')}

Elegido: **{nombre_t}** ({', '.join(NOMBRES_MODELO.get(m, m) for m in t['miembros'])}). Acierto **{_n(t['acierto_validacion'], 1)} %** en validación y
**{_n(t['acierto_test'], 1)} %** en test (error medio {_n(t['mae_validacion'], 2)} y {_n(t['mae_test'], 2)} °C). El test es peor porque 2016-2025 se calentó más
de lo que decía la historia: los modelos con tendencia habrían acertado algo más en el test, pero en la validación (que
es con lo que se elige) no ganaban. Se dice tal cual, sin cambiar la elección: la validación cae en 1996-2015, años
en que la temperatura subió más despacio.

**Sensibilidad (no es la previsión elegida).** Si sigue la tendencia de los últimos 30 años
({_n(t['escenario_tendencia']['pendiente_c_decada'], 2)} °C por década), la media de España en {final} sería {_n(t['escenario_tendencia']['temp_final_c'], 1)} °C en lugar de {_n(t['media_espana_final_c'], 1)} °C (últimos 10
años: {_n(t['media_espana_10a_c'], 1)} °C). El PUE medio pasaría de {_n(t['pue_medio_final'], 3)} a {_n(t['escenario_tendencia']['pue_final'], 3)} y el consumo del CPD subiría un
{_n(t['escenario_tendencia']['cambio_consumo_pct'], 1)} % respecto a la última década: el calentamiento afecta poco a la operación con la fórmula del simulador.

**Consumo del CPD a 10 años, de punta a punta** (temperatura prevista → PUE → consumo, frente a lo mismo con la
temperatura real): **{_n(t['consumo_acierto_validacion'], 1)} %** en validación y **{_n(t['consumo_acierto_test'], 1)} %** en test. Es tan alto porque el PUE del simulador
cambia poco con la temperatura; no hay fuga (la temperatura real de cada año no se usa para prever ese año).

Más calor previsto en {final}: {lista(calidas)}. Menos: {lista(frias)}.

### Reserva de agua por ámbito a 10 años

{tabla(medio['res_r'], 'puntos')}

Elegido: **{nombre_r}** ({', '.join(NOMBRES_MODELO.get(m, m) for m in r['miembros'])}). **Año a año** acierta {_n(r['acierto_validacion'], 1)} % en validación y
{_n(r['acierto_test'], 1)} % en test: **no llega al 85 %**, porque el año concreto de una sequía no se puede saber con 10 años de
antelación. Para un CPD lo que cuenta en una inversión a 10 años es el **agua media de la década**, y esa sí cumple:
**{_n(r['acierto_decada_validacion'], 1)} %** en validación y **{_n(r['acierto_decada_test'], 1)} %** en test. El año a año se enseña como orientativo.

Ámbitos con menos reserva media prevista: {bajos}.

**Emisiones a 10 años: no se prevén.** El mix por comunidad solo existe desde 2015 (11 años), con lo que no se puede
validar un horizonte de 10 años; además depende sobre todo de decisiones políticas (PNIEC), no de la historia.
"""


def _seccion_sismico(sismico: dict[str, Any]) -> str:
    """Riesgo sísmico (P8): candidatos, métricas y por qué no se usa si no llega al acierto mínimo."""
    from cpd.fuentes.provincias import PROVINCIAS
    from cpd.modelos.metricas import ACIERTO_MINIMO

    nombres = {p.codigo: p.nombre_ine for p in PROVINCIAS}
    m = sismico["metricas"]
    filas = [
        {
            "Modelo": NOMBRES_MODELO.get(f.modelo, f.modelo) + (" **(elegido)**" if f.modelo == sismico["elegido"] else ""),
            "Partición": f.particion,
            "Accuracy": f"{_n(100 * f.accuracy, 1)} %",
            "ROC-AUC": _n(f.roc_auc, 2),
            "Recall": f"{_n(100 * f.recall, 0)} %",
            "Log-loss": _n(f.log_loss, 3),
        }
        for f in m.sort_values(["particion", "log_loss"], ascending=[False, True]).itertuples()
    ]
    elegida = m.set_index(["modelo", "particion"]).loc[(sismico["elegido"], "validacion")]
    cumple = 100 * elegida["accuracy"] >= ACIERTO_MINIMO
    prev = sismico["prevision"].sort_values("prob", ascending=False)
    return f"""## Riesgo sísmico por provincia (P8)

¿Habrá al menos un terremoto de magnitud ≥ 3 en la provincia el año que viene? Datos de EMSC por provincia y año
(desde 2015); cada año se entrena solo con los anteriores. Variables: si lo hubo el año anterior, en qué fracción de
años lo ha habido, actividad media, magnitud máxima y la peligrosidad oficial de la norma NCSE-02 (aceleración
máxima de la provincia y municipios con ab ≥ 0,08 g). Candidatos: clase mayoritaria, persistencia («como el año
anterior») y regresión logística; se elige con la log-loss de validación ({sismico['anios_validacion']}; test {sismico['anio_test']}).

{_tabla(pd.DataFrame(filas))}

{"El modelo cumple el acierto mínimo." if cumple else f"**No llega al {_n(ACIERTO_MINIMO, 0)} %** aunque mejora a los baselines (ROC-AUC {_n(elegida['roc_auc'], 2)}): que haya o no un terremoto de magnitud ≥ 3 en un año es muy aleatorio y diez años de catálogo son poca historia. No se usa en el score. Para el riesgo sísmico del score y del filtro se usa directamente la aceleración sísmica básica oficial de la capital (NCSE-02), que es el dato que manda para proyectar un edificio."}
Probabilidades más altas para {int(prev['anio'].iloc[0])}: {', '.join(f"{nombres.get(c, c)} ({_n(100 * p, 0)} %)" for c, p in zip(prev['codigo_provincia'].head(5), prev['prob'].head(5)))}.
"""


def _seccion_gas_tiempo(gas_tiempo: dict[str, Any], figura: str, precio: dict[str, Any]) -> str:
    """Gas y tiempo: modelos añadidos para intentar mejorar el precio de la luz (inestables) y su efecto."""
    j = gas_tiempo["resumen"]
    nombres = {"gas": "Gas natural (MIBGAS)", "eolica": "Eólica de España", "solar": "Solar de España", "hidraulica": "Hidráulica de España"}
    filas = [
        {
            "Modelo": nombres.get(k, k),
            "Elegido": NOMBRES_MODELO.get(m["modelo"], m["modelo"]),
            "Acierto validación": f"{_n(m['acierto_validacion'], 1)} %",
            "Acierto test": f"{_n(m['acierto_test'], 1)} %",
        }
        for k, m in j["modelos"].items()
    ]
    rp = precio["resultado"]
    est = rp["metricas"].query("modelo == 'estructural_gas_tiempo'").set_index("particion")["acierto_pct"] if "estructural_gas_tiempo" in set(rp["metricas"]["modelo"]) else None
    linea_est = (
        f"Como candidato del precio, el **precio estructural** acierta un {_n(est['validacion'], 1)} % en validación y un {_n(est['test'], 1)} % en test"
        + (" y entra en la combinación." if "estructural_gas_tiempo" in rp["miembros"] else ".")
        if est is not None
        else ""
    )
    return f"""## Gas y tiempo: modelos añadidos para el precio de la luz (inestables)

El precio de la luz era el modelo más difícil: se quedaba en un 59-62 % de acierto. Como el precio lo marca casi
siempre la central de gas de ciclo combinado y baja cuando hay mucho viento, sol o agua, se añadieron (18/11/2026)
los **modelos del gas** (MIBGAS: último valor, ETS y los futuros del gas) y **del tiempo**, a través de la generación
eólica, solar e hidráulica de España (REData; la hidráulica, también con la reserva de los embalses). Con ellos se
construye un **precio estructural**: log(precio) = f(log(gas), cuotas de eólica, solar, hidráulica, nuclear, ciclo
combinado y carbón, ciclo combinado × gas, mes), ajustado con los meses reales y alimentado con las previsiones.

**Son inestables:** el gas y el tiempo de dentro de un año no se pueden saber, y sus aciertos cambian mucho entre
validación y test. Se usan solo como entradas del precio, no como dato del simulador.

![Gas y tiempo]({figura})

**Figura 2b.** Gas y generación eólica, solar e hidráulica de España: últimos 3 años y previsión a 1 año, con su
acierto (validación / test).

{_tabla(pd.DataFrame(filas))}

**Resultado para la luz.** {linea_est} El acierto del precio queda en {_n(precio['resumen']['acierto_validacion'], 1)} % en validación y
{_n(precio['resumen']['acierto_test'], 1)} % en test. **Diagnóstico:** aun con el gas y la generación **reales** de cada mes (sin previsión), el
precio solo se explica en un {_n(j['diagnostico_precio_con_reales'], 1)} %: faltan datos que no son abiertos o no son mensuales, como el precio del CO2 (la
fuente de la bolsa EEX es de pago), la demanda hora a hora y las interconexiones. Por eso el precio sigue como
orientativo.
"""


def _por_que_precio(res: dict[str, Any]) -> str:
    """Si el precio a 1 año no llega al acierto mínimo (D8), explica por qué con cifras de su propia validación."""
    from cpd.modelos.metricas import ACIERTO_MINIMO

    elegido = res["elegido"]
    general = res["metricas"].query("modelo == @elegido and particion == 'validacion'").iloc[0]
    if general["acierto_pct"] >= ACIERTO_MINIMO:
        return ""
    ph = res["por_horizonte"].query("particion == 'validacion'")
    por_h = ph[ph["modelo"] == elegido].set_index("horizonte_meses")["acierto_pct"]
    a_1_mes = ph[ph["horizonte_meses"] == 1].set_index("modelo")["acierto_pct"]
    reales = res["predicciones"].query("particion == 'validacion' and modelo == @elegido").drop_duplicates("mes").set_index("mes")["real"]
    mes = lambda t: pd.Timestamp(t).strftime("%m/%Y")  # noqa: E731
    return f"""**¿Por qué no llega al {_n(ACIERTO_MINIMO, 0)} %?** El acierto cae con la antelación: {_n(por_h.iloc[0], 0)} % a 1 mes y
{_n(por_h.iloc[-1], 0)} % a 12 meses (modelo elegido, validación). Ni el mejor modelo a 1 mes vista
—{NOMBRES_MODELO.get(a_1_mes.idxmax(), a_1_mes.idxmax())}— pasa del {_n(a_1_mes.max(), 0)} %. En los meses de validación el precio real fue de
{_n(reales.min(), 0)} €/MWh ({mes(reales.idxmin())}) a {_n(reales.max(), 0)} €/MWh ({mes(reales.idxmax())}): el error medio del modelo elegido,
{_n(general['mae'], 0)} €/MWh, es pequeño en un mes caro y enorme en uno barato. Llegar al {_n(ACIERTO_MINIMO, 0)} % exigiría escoger un periodo
de evaluación tranquilo o usar información que no se sabía en el origen, que es lo que el requisito (D8) quiere evitar.
Por eso esta previsión se enseña como **escenario orientativo**, con aviso, y el simulador sigue usando la media de
12 meses como supuesto (D7). Los futuros de electricidad (OMIP) podrían mejorar los primeros meses, pero no se han
integrado y no aseguran el {_n(ACIERTO_MINIMO, 0)} % (mejora posible; recomendación, no viene de clase).
"""


def informe_anual(anual: dict[str, Any], fecha: str, diez: dict[str, Any] | None = None, control: pd.DataFrame | None = None) -> str:
    """Informe de la previsión a 1 año (y a 10 años) con todos los gráficos (`docs/analisis/previsiones_1_anio.md`)."""
    fig = {k: "../../" + v for k, v in anual["figuras"].items()}
    p, d = anual["precio"], anual["demanda"]
    rp, rd = p["resultado"], d["resultado"]
    jp, jd = p["resumen"], d["resumen"]

    def tabla_modelos(res: dict[str, Any], col: str, fmt: int, unidad: str) -> str:
        t = res["metricas"].pivot(index="modelo", columns="particion", values=col).sort_values("validacion")
        filas = []
        for modelo, fila in t.iterrows():
            marca = " **(elegido)**" if modelo == res["elegido"] else (" (en la combinación)" if modelo in res["miembros"] else "")
            filas.append({"Modelo": NOMBRES_MODELO.get(modelo, modelo) + marca, f"Validación ({unidad})": _n(fila["validacion"], fmt), f"Test ({unidad})": _n(fila["test"], fmt)})
        return _tabla(pd.DataFrame(filas))

    filas_ccaa = []
    for codigo, c in sorted(jd["ccaa"].items(), key=lambda kv: -kv[1]["prevision_12m"]):
        filas_ccaa.append(
            {
                "Comunidad": c["nombre"],
                "Último año (GWh)": _n(c["ultimos_12m"] / 1e3, 0),
                "Previsión 1 año (GWh)": _n(c["prevision_12m"] / 1e3, 0),
                "Variación": f"{_n((c['prevision_12m'] / c['ultimos_12m'] - 1) * 100, 1)} %",
                "Rango (GWh)": f"{_n(c['prevision_12m_inferior'] / 1e3, 0)}-{_n(c['prevision_12m_superior'] / 1e3, 0)}",
                "Datos hasta": c["hasta"],
            }
        )
    meses_p = ", ".join(f"{x['mes']}: {_n(x['valor'], 0)}" for x in jp["prevision"])
    o_p, o_d = rp["origenes"], rd["origenes"]
    seccion_control = _seccion_control(control, fig["control"]) if control is not None and "control" in fig else ""
    seccion_reservas = _seccion_reservas(anual["reservas"], fig["reservas"]) if "reservas" in anual else ""
    seccion_temperatura = (
        _seccion_temperatura(anual["temperatura"], fig["temperatura"], fig["temperatura_mensual"]) if "temperatura" in anual and "temperatura" in fig else ""
    )
    seccion_renovables = (
        _seccion_renovables(anual["renovables"], fig["renovables"], fig["renovables_mensual"]) if "renovables" in anual and "renovables" in fig else ""
    )
    seccion_cobertura = _seccion_cobertura(anual["cobertura"], fig["cobertura"]) if "cobertura" in anual and "cobertura" in fig else ""
    seccion_operacion = _seccion_operacion(anual["operacion"], fig["operacion"]) if "operacion" in anual and "operacion" in fig else ""
    seccion_sismico = _seccion_sismico(anual["sismico"]) if "sismico" in anual else ""
    seccion_gas_tiempo = (
        _seccion_gas_tiempo(anual["gas_tiempo"], fig["gas_tiempo"], anual["precio"]) if anual.get("gas_tiempo") and "gas_tiempo" in fig else ""
    )
    seccion_10 = _seccion_10_anios(diez) if diez else ""
    if anual.get("medio_plazo"):
        seccion_10 += "\n" + _seccion_medio_plazo(anual["medio_plazo"], "../../" + anual["medio_plazo"]["figura"])
    return f"""# Previsiones · 1 año (demanda, precio de la luz, reservas de agua, temperatura y renovables) y 10 años (demanda nacional)

{AVISO.format(fecha=fecha)}

Previsión mes a mes de los **12 meses siguientes** al último dato con el modelo que menos se equivoca a 1 año (demanda
por comunidad, precio de la luz, reservas de agua por ámbito, temperatura por provincia y % de generación renovable por
comunidad), y de la demanda nacional a 10 años. Código: `src/cpd/modelos/anual.py` y `src/cpd/modelos/largo_plazo.py`. Las fichas de
modelo de [demanda](../modelos/demanda_ccaa.md) y [precio](../modelos/precio_luz.md) describen las primeras
evaluaciones; este informe es el que alimenta el mapa.

{seccion_control}

## Cómo se ha buscado el menor error

1. **Backtesting a 1 año con 24 orígenes** (dos años). En cada origen, cada modelo se entrena solo con lo que se sabía
   entonces y prevé los 12 meses siguientes. Se compara con lo que pasó. Así el error medido es el de una previsión a
   1 año de verdad, y no el de un único periodo.
2. **Candidatos:** baselines (mismo mes del año anterior, último mes, media de 12 meses), un modelo estadístico de
   series temporales (**ETS de Holt-Winters** con tendencia amortiguada, `statsmodels`), modelos de ML (Ridge con
   lags; para el precio, **Ridge con el gas** y gradient boosting) y la **combinación** (media) de los 3 mejores.
3. **Fuente nueva para el precio:** el precio del gas de **MIBGAS** (spot y futuros a 1 trimestre y 1 año), porque el
   gas marca el precio de la luz en muchas horas y sus futuros son lo que el mercado espera para el año siguiente.
4. **Elección:** la combinación, salvo que un modelo solo la mejore en validación en más de un 5 %. Combinar modelos
   reduce el error porque cada uno se equivoca en momentos distintos (recomendación, no viene de clase).
5. **Test:** un año entero que ningún modelo ha visto (origen {o_p['origen_test']} en el precio y {o_d['origen_test']} en la
   demanda).

**Transparencia.** La primera versión usaba 12 orígenes de validación y elegía el mejor modelo sin margen: en el
precio eligió el gradient boosting, que luego fue el peor en test (prevía 285 €/MWh extrapolando la crisis de 2022).
Se amplió la validación a 24 orígenes y se fijó la regla de la combinación **después de ver ese test**, así que los
resultados de test son orientativos y no una prueba totalmente independiente.

## Precio de la luz

![Precio de la luz]({fig['precio']})

**Figura 1.** Arriba, el precio real desde 2021 (azul), lo que el modelo habría previsto hace un año (punteado), la
previsión de los próximos 12 meses (naranja) con su intervalo mensual (10-90 %) y la media de 12 meses que usa el
simulador (gris). Abajo, en su propio eje, el gas de MIBGAS (mercado diario y futuro a 1 año) que usan los modelos con gas.

{tabla_modelos(rp, 'mae', 1, '€/MWh')}

Validación: orígenes {o_p['origenes_validacion']}, meses {o_p['meses_validacion']}. Test: meses {o_p['meses_test']}.

**Resultado.** Modelo elegido: **{NOMBRES_MODELO.get(rp['elegido'], rp['elegido'])}**
({', '.join(NOMBRES_MODELO.get(m, m) for m in rp['miembros'])}). Error medio a 1 año: {_n(jp['error_validacion'], 1)} €/MWh en
validación y {_n(jp['error_test'], 1)} €/MWh en test, frente a {_n(rp['metricas'].query("modelo == 'media_12m' and particion == 'validacion'")['mae'].iloc[0], 1)} y
{_n(rp['metricas'].query("modelo == 'media_12m' and particion == 'test'")['mae'].iloc[0], 1)} €/MWh de la media de 12 meses que usa el simulador.

**Previsión** desde {jp['ultimo_mes']}: media de **{_n(jp['media_prevista'], 0)} €/MWh** para los próximos 12 meses (rango
{_n(jp['media_inferior'], 0)}-{_n(jp['media_superior'], 0)} €/MWh, cuantiles 10-90 % del error de la media anual en validación), frente a
{_n(jp['media_12m_actual'], 0)} €/MWh de media del último año y {_n(jp['ultimo_mes_valor'], 0)} €/MWh en {jp['ultimo_mes']}. El futuro de gas a
1 año cotiza a {_n(jp['futuro_gas_anio'], 1) if jp['futuro_gas_anio'] else '—'} €/MWh. Mes a mes (€/MWh): {meses_p}.

![Backtesting del precio]({fig['backtesting_precio']})

**Figura 2.** Las 24 previsiones a 1 año de validación frente al precio real: se ve cuándo acierta y cuándo no
(la previsión tarda en reaccionar a los cambios bruscos).

{_por_que_precio(rp)}

{seccion_gas_tiempo}
## Demanda eléctrica por comunidad autónoma

![Demanda por comunidad]({fig['demanda']})

**Figura 3.** Últimos 3 años y previsión a 1 año de cada comunidad, con su intervalo (10-90 %).

{tabla_modelos(rd, 'mape_pct', 2, '% MAPE')}

Validación: orígenes {o_d['origenes_validacion']}, meses {o_d['meses_validacion']}. Test: meses {o_d['meses_test']}.

**Resultado.** Modelo elegido: **{NOMBRES_MODELO.get(rd['elegido'], rd['elegido'])}**
({', '.join(NOMBRES_MODELO.get(m, m) for m in rd['miembros'])}). Error medio a 1 año: {_n(jd['error_validacion'], 2)} % en validación y
{_n(jd['error_test'], 2)} % en test, frente a {_n(rd['metricas'].query("modelo == 'estacional' and particion == 'test'")['mape_pct'].iloc[0], 2)} % del mejor
baseline en test («mismo mes del año anterior»).

{_tabla(pd.DataFrame(filas_ccaa))}

Rango: cuantiles 10-90 % del error de la suma anual de cada comunidad en validación.

{seccion_reservas}

{seccion_temperatura}

{seccion_renovables}

{seccion_cobertura}

{seccion_operacion}

{seccion_sismico}

{seccion_10}

## Errores por horizonte y comparación de modelos

![Error por horizonte]({fig['horizonte']})

**Figura 12.** Error medio de cada modelo según los meses de antelación (validación), un gráfico por serie. El elegido
va en naranja y el resto en gris.

![Comparación]({fig['modelos']})

**Figura 13.** Error a 1 año de cada modelo en validación y en test, un gráfico por serie (el elegido, en negrita).

## Limitaciones

- El precio del año siguiente depende sobre todo del gas, el CO2 y la hidráulica, que también se pueden equivocar:
  el intervalo es ancho a propósito. No se han integrado los futuros de electricidad (OMIP), la referencia directa
  del mercado: podrían mejorar los primeros meses, pero no aseguran el acierto mínimo (ver «¿Por qué no llega…?»).
- Un solo año de test por serie: el error de test tiene mucha incertidumbre.
- La demanda peninsular termina en junio de 2026 porque REData aún no ha publicado bien julio y agosto
  (ver [tablas_api.md](../datos/tablas_api.md)): su «año siguiente» empieza en julio de 2026.

## Reproducción

`.\\.venv\\Scripts\\python.exe -m cpd.modelos` (necesita las tablas `gas_diario` y `gas_futuros`, que descarga
`python -m cpd.fuentes.actualizar`). Salidas en `data/curated/modelos/previsiones_1_anio.json` y `anual_*.csv`.
"""


def ficha_precio(precio: dict[str, Any], fecha: str) -> str:
    """Model card del precio de la luz (`docs/modelos/precio_luz.md`)."""
    r = precio["resultado"]
    e = r["elegido"]
    res = precio["resumen"]
    m = r["metricas"]
    val = m.query("particion == 'validacion' and horizonte == 'todos'").set_index("modelo")["mae"]
    tst = m.query("particion == 'test' and horizonte == 'todos'").set_index("modelo")["mae"]
    h1 = m.query("particion == 'test' and horizonte == '1'").set_index("modelo")["mae"]
    bt = precio["backtest"].assign(abs=lambda d: d["error_eur_mwh"].abs()).groupby("modelo")["abs"].mean()
    mejor_bt = str(bt.idxmin())
    ta = precio["test_anual"].set_index("modelo")
    filas = "\n".join(
        f"| {NOMBRES_MODELO.get(n, n)} | {_n(val[n], 1)} | {_n(tst[n], 1)} | {_n(h1[n], 1)} | {_n(bt.get(n), 1)} | {_n(ta['error_eur_mwh'].get(n), 1)} |"
        for n in val.sort_values().index
    )
    mejor_test = str(tst.idxmin())
    nota_test = (
        f"En test, {NOMBRES_MODELO.get(mejor_test, mejor_test)} habría sido algo mejor ({_n(tst[mejor_test], 1)} frente a "
        f"{_n(tst[e['modelo']], 1)} €/MWh), pero el modelo se elige con la validación y el test solo se mira una vez."
        if mejor_test != e["modelo"]
        else "El modelo elegido es también el mejor en test."
    )
    sel = r["seleccion"].assign(mae_validacion_eur_mwh=lambda d: d["mae_validacion_eur_mwh"].map(lambda v: _n(v, 1)))
    sel.columns = ["Familia", "Configuración", "MAE validación (€/MWh)"]
    figura = "../../" + precio["figura"]
    gana_ml = e["familia"] == "ml"
    return f"""# Model card · Precio medio mensual de la electricidad (`precio_luz`)

{AVISO.format(fecha=fecha)}

> Esta ficha es la primera evaluación del precio (un solo periodo de validación y sin el precio del gas). **La
> previsión a 1 año que usa el mapa** (combinación con el gas de MIBGAS, elegida con 24 orígenes de backtesting) está
> en [previsiones_1_anio.md](../analisis/previsiones_1_anio.md).

## Datos

- Fuente y tablas: `data/curated/tablas/precios_diarios` (spot diario REData/OMIE, €/MWh → media mensual),
  `reservas_ambito_mensual` (MITECO, 16 ámbitos → reserva nacional) y `co2` (REData, emisiones del sistema).
- Granularidad: nacional (sistema peninsular) × mes. Solo meses completos (se quita el mes en curso).
- Periodo de entrenamiento: meses objetivo de 2017 a {precio['periodos']['entrenamiento_hasta']} (incluye la crisis de 2021-2022).
- Periodo de validación: {precio['periodos']['validacion']}.
- Periodo de test: {precio['periodos']['test']} (usado una vez).
- Features (`cpd.features.precio`, origen `r = t − h`): último precio, penúltimo, media de 3 meses, mismo mes del año
  anterior, tendencia anual, volatilidad, reserva hídrica nacional y su variación anual, CO2 relativo, mes del
  año (seno y coseno) y horizonte. Todas relativas al nivel de 12 meses y en logaritmo. Diccionario en
  `data/curated/modelos/diccionario_features.csv`.
- Escalado: `StandardScaler` dentro del pipeline de Ridge, ajustado solo con entrenamiento (R-7).

## Objetivo

Precio spot medio de cada uno de los 12 meses siguientes (€/MWh) y su media, que es el dato que entra en el OPEX
del simulador. Un solo modelo para los horizontes de 1 a 12 meses (previsión directa; el horizonte es una feature).

## Baselines

- Último mes (naive): el precio del mes de origen.
- **Media de los últimos 12 meses: es lo que usa hoy el simulador.**
- Mismo mes del año anterior (estacional).
- Tendencia + estacionalidad (`cpd.forecast.prever_mensual`).

## Métrica principal

**MAE (€/MWh)** = media de |real − previsión|. Se elige porque el error del precio pasa directamente al coste de
la energía: con un CPD de 50 MW de TI (unos 455 GWh al año con PUE 1,3), 10 €/MWh de error son unos 4,5 M€ al año de
OPEX. El MAPE no sirve como métrica principal: se dispara en los meses con precios muy bajos. Coste del error:
infraestimar el precio es más peligroso que sobreestimarlo (hace parecer rentable un CPD que no lo es).

## Resultados

| Modelo | MAE validación | MAE test | MAE test a 1 mes | Error de la media anual (backtesting) | Error de la media anual (test) |
|---|---|---|---|---|---|
{filas}

Todos los valores están en €/MWh. Backtesting: {res['origenes_backtesting']} orígenes trimestrales de 2020 a 2023, con
reentrenamiento en cada origen. Test anual: origen {precio['test_anual']['origen'].iloc[0] if not precio['test_anual'].empty else '—'}
(error = previsión − real).

**Modelo elegido con la validación: {NOMBRES_MODELO.get(e['modelo'], e['modelo'])}.**
{"El modelo de ML mejora a todos los baselines en validación." if gana_ml else
"Ningún modelo de ML supera en validación a la media de los últimos 12 meses: es decir, **el supuesto que ya usaba el simulador es la mejor previsión disponible del precio anual**. La explicación más probable: sin el precio del gas (que no está entre las fuentes) no se pueden anticipar los cambios de régimen, y el entrenamiento está dominado por la crisis de 2021-2022. Se documenta en lugar de forzar un modelo peor."}
{nota_test}

Matiz importante: en el backtesting de 2020-2023, el que mejor acierta la media del año siguiente es
**{NOMBRES_MODELO.get(mejor_bt, mejor_bt)}** ({_n(bt[mejor_bt], 1)} €/MWh de error medio), porque en esos años el precio cambió de
nivel varias veces y el último mes recoge antes el cambio. Con el criterio fijado de antemano (MAE mensual en
validación) se mantiene el modelo elegido.

![Previsión del precio]({figura})

**Figura.** Precio real, previsión de los 12 meses siguientes con su intervalo y el escenario «el precio se queda
como el último mes».

Selección de configuraciones de ML (validación):

{_tabla(sel)}

## Previsión actual

- Precio medio previsto para los 12 meses siguientes a {res['ultimo_mes']}: **{_n(res['media_prevista_eur_mwh'], 1)} €/MWh**
  (rango probable {_n(res['inferior_eur_mwh'], 0)}-{_n(res['superior_eur_mwh'], 0)} €/MWh, cuantiles del 10 % y el 90 % del error
  de la media anual en el backtesting).
- Escenario «se mantiene el último mes»: **{_n(res['ultimo_mes_eur_mwh'], 1)} €/MWh** ({res['ultimo_mes']}).
- **Aviso:** el precio sube desde julio de 2026 (en {res['ultimo_mes']}, {_n(res['ultimo_mes_eur_mwh'], 0)} €/MWh frente a
  {_n(res['media_12m_actual_eur_mwh'], 0)} de media en 12 meses). Si es un cambio de régimen como el de 2021, la media de 12 meses
  lo infraestima. El mapa enseña el VAN con los dos extremos del rango.

## Sesgos y comprobaciones

- Paradoja de la exactitud: no aplica (regresión).
- Por horizonte: el error a 1 mes es menor que a 12 (tabla de [metricas.md](../analisis/metricas.md)).
- Fuga: `tests/test_modelos.py` comprueba que cambiar los datos posteriores al origen no cambia las features.
- Particiones: entrenamiento < validación < test por mes objetivo (R-6).

## Limitaciones

- No hay precio del gas (MIBGAS o TTF) ni precios de futuros (OMIP), que son lo que de verdad anticipa el precio
  del año siguiente. Es la mejora más clara (recomendación, no viene de clase).
- Una sola serie nacional con unos 120 meses útiles: pocos datos para un modelo con muchas features.
- El precio que paga un CPD depende de su contrato (PPA, tarifas de acceso), no solo del spot.

## Uso previsto y uso no previsto

- Previsto: dar el precio de referencia y su rango al simulador y enseñar la sensibilidad del VAN en el mapa.
- No previsto: comprar energía o cerrar un contrato con esta previsión.

## Reproducción

`.\\.venv\\Scripts\\python.exe -m cpd.modelos` (semilla {precio['semilla']}; versiones en `requirements.txt`). Salidas en
`data/curated/modelos/` (`prevision_precio_luz.csv`, `resumen_precio_luz.json`, `metricas_precio.csv`,
`media_anual_precio.csv`). Entrenado el {fecha}.
"""


def ficha_demanda(demanda: dict[str, Any], fecha: str) -> str:
    """Model card de la previsión de demanda (`docs/modelos/demanda_ccaa.md`)."""
    periodos = demanda["periodos"]
    r1 = demanda["resultados"][1]
    r12 = demanda["resultados"][12]

    def fila(resultado: dict[str, Any], modelo: str, particion: str) -> pd.Series:
        m = resultado["metricas"]
        return m[(m["modelo"] == modelo) & (m["particion"] == particion)].iloc[0]

    e1, e12 = r1["elegido"], r12["elegido"]
    mejor_base_1 = r1["metricas"][(r1["metricas"]["familia"] == "baseline") & (r1["metricas"]["particion"] == "validacion")].sort_values("mape_pct").iloc[0]["modelo"]
    supera = fila(r1, e1["modelo"], "test")["mape_pct"] < fila(r1, mejor_base_1, "test")["mape_pct"]
    res = demanda["resumen"]
    cuantiles = demanda["cuantiles_log"]
    figura = "../../" + demanda["figura"] if demanda.get("figura") else None
    imputados = int(demanda["serie"]["imputado"].sum())
    return f"""# Model card · Demanda eléctrica mensual por comunidad autónoma

{AVISO.format(fecha=fecha)}

> Esta ficha evalúa la demanda a 1 y a 12 meses vista con un único periodo de test. **La previsión a 1 año que usa el
> mapa** (combinación de modelos elegida con 24 orígenes de backtesting) está en
> [previsiones_1_anio.md](../analisis/previsiones_1_anio.md).

## Datos

- Fuente y tabla: `data/curated/panel_provincia_mes`, columna `demanda_ccaa_mwh` (Red Eléctrica REData).
- Granularidad: comunidad autónoma × mes (19 comunidades, incluidas Baleares, Canarias, Ceuta y Melilla).
- Periodo de entrenamiento: primer mes con features completas (2017) a {periodos['entrenamiento_hasta']}.
- Periodo de validación: {periodos['validacion']}.
- Periodo de test: {periodos['test']} (usado una vez).
- Features: lags de `h`, `h+1`, `h+2`, 12 y 24 meses; medias de 3 y 6 meses; volatilidad y tendencia de 12 meses;
  mes del año (seno, coseno y variables binarias) y confinamiento de 2020. Todas relativas al nivel de los 12 meses
  que terminan en `t − h`, en logaritmo. Diccionario: `data/curated/modelos/diccionario_features.csv`
  (se regenera con el comando).
- Calidad: la demanda imposible de REData (jul-ago de 2026 sin saldo de intercambios; oct-2025 en tres comunidades del
  norte) llega en NaN desde el curado. Los huecos del final se recortan y {imputados} meses intermedios se sustituyen por
  el mismo mes del año anterior, solo como entrada y marcados (ver el
  [informe EDA](../analisis/eda_panel.md#7-datos-atípicos-de-la-demanda-r-10)).
- Escalado (solo Ridge): `StandardScaler` dentro del pipeline, ajustado solo con entrenamiento (R-7).

## Objetivo

Demanda eléctrica del mes `t` de cada comunidad (MWh), con los datos conocidos hasta `t − h`. Dos horizontes:
`h` = 1 mes y `h` = 12 meses. El modelo predice `log(demanda / nivel)` y se convierte a MWh.

## Baselines

- Último valor (naive): demanda de `t − h`.
- Mismo mes del año anterior (estacional): demanda de `t − 12`. Con `h` = 12 coincide con el naive.
- Tendencia + estacionalidad: `cpd.forecast.prever_mensual`, reajustado en cada origen.

## Métrica principal

**MAPE** = media de |real − previsión| / real × 100. Se elige porque las comunidades tienen escalas muy distintas y
porque el error relativo es lo que se traslada al simulador (impacto local). Coste del error: sobreestimar la demanda
de la zona exagera el impacto local del CPD; infraestimarla lo esconde. El coste es simétrico.

## Resultados

Tabla completa (validación y test de todos los modelos): [metricas.md](../analisis/metricas.md).

| Horizonte | Mejor baseline (test) | Modelo elegido | MAPE test del elegido |
|---|---|---|---|
| 1 mes | {NOMBRES_MODELO[mejor_base_1]}: {_n(fila(r1, mejor_base_1, 'test')['mape_pct'], 2)} % | {NOMBRES_MODELO.get(e1['modelo'], e1['modelo'])} ({e1['configuracion']}) | {_n(fila(r1, e1['modelo'], 'test')['mape_pct'], 2)} % |
| 12 meses | {NOMBRES_MODELO['estacional']}: {_n(fila(r12, 'estacional', 'test')['mape_pct'], 2)} % | {NOMBRES_MODELO.get(e12['modelo'], e12['modelo'])} | {_n(fila(r12, e12['modelo'], 'test')['mape_pct'], 2)} % |

- **A 1 mes**, el modelo elegido {"mejora" if supera else "no mejora"} al mejor baseline en test.
- **A 12 meses**, ningún modelo ML supera al "mismo mes del año anterior" en validación, así que se elige el
  baseline. Se documenta en lugar de forzar un modelo peor: la demanda anual de cada comunidad es muy estable y las
  features disponibles no anticipan sus cambios (crisis, eficiencia, autoconsumo).
{f"{chr(10)}![Previsión frente a real en test]({figura}){chr(10)}{chr(10)}**Figura.** Demanda real y previsión a 1 mes en el periodo de test para seis comunidades.{chr(10)}" if figura else ""}
Intervalo de la previsión final: cuantiles del 5 % y el 95 % de los errores relativos del modelo elegido en
validación (de {_n(100 * (np.exp(cuantiles[0]) - 1), 1)} % a +{_n(100 * (np.exp(cuantiles[1]) - 1), 1)} % al mes). La suma de
12 meses suma también los extremos, así que es un intervalo conservador.

## Sesgos y comprobaciones

- Paradoja de la exactitud: no aplica (regresión).
- Por subgrupo (MAPE de test a 1 mes del modelo elegido, por comunidad; detalle en
  `data/curated/modelos/predicciones_demanda.csv`): más error en {demanda['peores_ccaa']}; menos en
  {demanda['mejores_ccaa']}.
- Fuga: un test (`tests/test_modelos.py`) comprueba que cambiar la demanda posterior a `t − h` no cambia las features.
- Particiones: un test comprueba que entrenamiento < validación < test (R-6).

## Previsión de los próximos 12 meses

{_tabla(res.assign(**{"Últimos 12 meses (GWh)": (res['ultimos_12m_mwh'] / 1e3).map(lambda v: _n(v, 0)), "Previsión 12 meses (GWh)": (res['prevision_12m_mwh'] / 1e3).map(lambda v: _n(v, 0)), "Hasta": res['ultimos_12m_hasta']})[["ccaa", "Hasta", "Últimos 12 meses (GWh)", "Previsión 12 meses (GWh)"]].rename(columns={"ccaa": "Comunidad"}))}

Como el modelo a 12 meses es el estacional, la previsión repite el último año. Las comunidades peninsulares
terminan en junio de 2026 porque REData aún no publica el saldo de intercambios de julio y agosto.

## Limitaciones

- No prevé a 10 años: para la pregunta P5 sigue valiendo `cpd.forecast` (tendencia + estacionalidad), con una
  incertidumbre que crece con el horizonte. Un modelo con lags no se puede extender 120 meses sin acumular error.
- No incluye el efecto de un CPD nuevo sobre la demanda ni variables externas (PIB, precios, autoconsumo).
- La demanda es de comunidad: no distingue provincias.

## Uso previsto y uso no previsto

- Previsto: dar contexto en la ficha del mapa (demanda de la comunidad) y comparar el consumo de un CPD con la
  demanda de su zona.
- No previsto: planificar la red eléctrica o tomar decisiones de inversión sin revisión humana.

## Reproducción

`.\\.venv\\Scripts\\python.exe -m cpd.modelos` (semilla {demanda['semilla']}; versiones en `requirements.txt`).
Salidas en `data/curated/modelos/` y modelo guardado en `models/demanda_ccaa_h1.joblib` (fuera de git).
Entrenado el {fecha}.
"""


def ficha_prob_cpd(prob: dict[str, Any], tabla: pd.DataFrame, figura: str | None, fecha: str) -> str:
    """Model card de `prob_cpd` (`docs/modelos/prob_cpd.md`)."""
    m = prob["metricas"].set_index("modelo")
    mu = prob["metricas_umbral"]
    sesgos = prob["sesgos"].copy()
    sesgos = pd.DataFrame(
        {
            "Subgrupo": sesgos["grupo"],
            "Provincias": sesgos["provincias"],
            "Con CPD (real)": sesgos["con_cpd_pct"].map(lambda v: f"{_n(v, 0)} %"),
            "Probabilidad media": sesgos["prob_media_pct"].map(lambda v: f"{_n(v, 0)} %"),
            "Falsos positivos": sesgos["falsos_positivos"],
            "Falsos negativos": sesgos["falsos_negativos"],
        }
    )
    coef = prob["coeficientes"].assign(coeficiente_estandarizado=lambda d: d["coeficiente_estandarizado"].map(lambda v: _n(v, 2)))
    coef.columns = ["Feature", "Coeficiente (estandarizado)"]
    probs = prob["probabilidades"][prob["elegido"]]
    candidatas = tabla.assign(prob=probs)[lambda d: d["tiene_cpd"] == 0].nlargest(5, "prob")
    sorpresas = tabla.assign(prob=probs)[lambda d: d["tiene_cpd"] == 1].nsmallest(3, "prob")
    lista = lambda d: ", ".join(f"{fila.provincia} ({_n(100 * fila.prob, 0)} %)" for fila in d.itertuples())  # noqa: E731
    elegido = prob["elegido"]
    return f"""# Model card · Probabilidad de que una provincia tenga un CPD (`prob_cpd`)

{AVISO.format(fecha=fecha)}

## Datos

- Fuente y tabla: `data/curated/panel_provincia_mes` resumido a una fila por provincia
  (`cpd.features.provincia.features_estaticas_provincia`).
- Etiqueta: `tiene_cpd` = 1 si hay al menos un centro de datos en PeeringDB ({int(tabla['tiene_cpd'].sum())} de 52 provincias).
- Granularidad: provincia (transversal, sin tiempo).
- Validación: no hay fechas de apertura de los CPD, así que **no se puede hacer una partición temporal** (R-6 no
  aplica). Se usa validación cruzada estratificada repetida: 5 pliegues × 20 repeticiones, semilla 42. El
  hiperparámetro `C` de la logística se elige con una validación cruzada interna (anidada).
- Features: log de población, renta por persona, paro, temperatura media, % de free cooling, estrés hídrico,
  subestaciones de 220-400 kV, % de Red Natura 2000, capacidad de acceso de la comunidad, terremotos y si es
  extrapeninsular. **Excluidas por fuga:** `n_ixp` y `distancia_ixp_km` (los IXP están dentro de centros de datos).
- Nulos e imputación: mediana, ajustada dentro de cada pliegue (solo falta la capacidad de acceso de Melilla).
  Escalado: `StandardScaler` dentro del pipeline (R-7).

## Objetivo

Probabilidad (0-1) de que una provincia con esas características tenga un centro de datos. Es una **propensión**:
dice a qué se parece una provincia, no si se va a construir un CPD nuevo.

## Baselines

- Clase mayoritaria: log-loss {_n(m.loc['mayoritaria', 'log_loss'], 3)}; accuracy {_n(100 * m.loc['mayoritaria', 'accuracy'], 1)} %.
- Logística solo con población: log-loss {_n(m.loc['solo_poblacion', 'log_loss'], 3)}; ROC-AUC {_n(m.loc['solo_poblacion', 'roc_auc'], 3)}.

## Métrica principal

**Log-loss** (pérdida logarítmica) [C3 p.14]: −media(y·log p + (1−y)·log(1−p)). Se elige porque el mapa muestra la
probabilidad y esta métrica castiga las probabilidades seguras y equivocadas. Se mira también ROC-AUC [C3 p.19].
Coste de los errores: un falso positivo (provincia "parecida a las que tienen CPD" que no lo es) solo lleva a estudiarla
más; un falso negativo esconde una buena candidata. Por eso el umbral se elige con la curva ROC (índice de Youden) en
lugar de fijarlo en 0,5.

## Resultados

| Modelo | Log-loss | ROC-AUC | Brier | Accuracy (0,5) |
|---|---|---|---|---|
{chr(10).join(f"| {NOMBRES_MODELO[n]} | {_n(m.loc[n, 'log_loss'], 3)} | {'0,500 (constante)' if n == 'mayoritaria' else _n(m.loc[n, 'roc_auc'], 3)} | {_n(m.loc[n, 'brier'], 3)} | {_n(100 * m.loc[n, 'accuracy'], 1)} % |" for n in m.index)}

**Modelo elegido: {NOMBRES_MODELO[elegido]}.** Con 52 provincias, añadir variables no mejora la log-loss: la
población explica casi todo y el resto añade ruido (sobreajuste). Se documenta en lugar de elegir un modelo más
complejo y peor.
{f"{chr(10)}![Curva ROC]({'../../' + figura}){chr(10)}{chr(10)}**Figura 1.** Curvas ROC fuera de pliegue de los cuatro modelos.{chr(10)}" if figura else ""}
{f"{chr(10)}![prob_cpd por provincia]({'../../' + prob['figura_provincias']}){chr(10)}{chr(10)}**Figura 2.** Matriz de confusión con el umbral elegido, métricas con ese umbral y probabilidad fuera de pliegue de cada provincia (azul: tiene CPD; gris: no tiene; línea discontinua: umbral). Las barras grises a la derecha del umbral son las provincias «parecidas» a las que ya tienen CPD.{chr(10)}" if prob.get('figura_provincias') else ""}
**Umbral elegido** (Youden): {_n(prob['umbral'], 2)}. Matriz de confusión con ese umbral:

| | Predice "con CPD" | Predice "sin CPD" |
|---|---|---|
| Tiene CPD | {mu['vp']} (verdaderos positivos) | {mu['fn']} (falsos negativos) |
| No tiene CPD | {mu['fp']} (falsos positivos) | {mu['vn']} (verdaderos negativos) |

Accuracy {_n(100 * mu['accuracy'], 1)} %, precision {_n(mu['precision'], 2)}, recall (TPR) {_n(mu['recall'], 2)}, FPR {_n(mu['fpr'], 2)}, F1 {_n(mu['f1'], 2)}.

**Coeficientes de la logística con todas las features** (ajustada con las 52 provincias, `C` = {_n(prob['C_final'], 2)};
solo para interpretar):

{_tabla(coef)}

## Sesgos y comprobaciones

- **Paradoja de la exactitud:** comprobada. Predecir siempre "sin CPD" acierta el {_n(100 * (1 - prob['prevalencia']), 1)} %
  y no detecta ninguna provincia con CPD; el modelo elegido se compara con ese mínimo en log-loss y ROC-AUC.
- **Por subgrupo** (con el umbral elegido):

{_tabla(sesgos)}

- Provincias sin CPD con más probabilidad (candidatas): {lista(candidatas)}.
- Provincias con CPD y poca probabilidad (el modelo no las explica): {lista(sorpresas)}.

## Limitaciones

- 52 filas y 14 positivos: las métricas tienen mucha incertidumbre (una provincia más o menos cambia el ROC-AUC
  unas centésimas).
- PeeringDB no recoge todos los CPD (solo los registrados para interconexión).
- Elegir entre los cuatro modelos con las mismas predicciones fuera de pliegue con que se informa es algo optimista;
  con tan pocos datos no hay un test aparte.
- No dice por qué una provincia tiene CPD (correlación, no causalidad).

## Uso previsto y uso no previsto

- Previsto: dato de contexto en la ficha del mapa ("probabilidad de que se instale un CPD") y lista de provincias
  parecidas a las que ya tienen CPD.
- No previsto: decidir una inversión, ni comparar provincias como si fuera una probabilidad de éxito.

## Reproducción

`.\\.venv\\Scripts\\python.exe -m cpd.modelos` (semilla 42; versiones en `requirements.txt`). Salida en
`data/curated/modelos/prob_cpd_provincia.csv`; modelo final en `models/prob_cpd.joblib` (fuera de git).
Entrenado el {fecha}.
"""
