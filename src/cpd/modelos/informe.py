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

Fase 8 de [la metodología](../metodologia/03_Flujo_de_trabajo.md). Fichas de modelo:
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
{f"{chr(10)}![Curva ROC]({'../../' + figura}){chr(10)}{chr(10)}**Figura.** Curvas ROC fuera de pliegue de los cuatro modelos.{chr(10)}" if figura else ""}
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
