"""Aplicación Streamlit: simulador y dashboard de viabilidad de un CPD (data center) en municipios españoles.

Ejecutar desde la raíz del proyecto (con el venv activado):
    streamlit run app/streamlit_app.py
o bien con scripts/run_app.ps1.

Pestañas: Ranking, Mapa, Ficha municipio, Económico, Previsión demanda y Escenarios.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite importar el paquete cpd aunque no se haya hecho "pip install -e ."
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from cpd.config import RUTA_DEMANDA_LIMPIA, RUTA_DEMO, cargar_settings  # noqa: E402
from cpd.forecast import prever_mensual  # noqa: E402
from cpd.scoring import (  # noqa: E402
    ESTADO_CONDICIONES,
    ESTADO_NO_VIABLE,
    ESTADO_VIABLE,
    INDICADORES_POR_BLOQUE,
    evaluar,
    pesos_normalizados,
    preparar_escenario,
)
from cpd.simulator import TIPOS_REFRIGERACION, CPDParams  # noqa: E402

ORDEN_ESTADOS: list[str] = [ESTADO_VIABLE, ESTADO_CONDICIONES, ESTADO_NO_VIABLE]
COLORES_ESTADO: dict[str, str] = {
    ESTADO_VIABLE: "#2E7D5B",
    ESTADO_CONDICIONES: "#C98A1B",
    ESTADO_NO_VIABLE: "#B5473A",
}
FONDO_ESTADO: dict[str, str] = {
    ESTADO_VIABLE: "#D7EFE2",
    ESTADO_CONDICIONES: "#FBEBC8",
    ESTADO_NO_VIABLE: "#F4D3CE",
}
ETIQUETAS_BLOQUE: dict[str, str] = {
    "energia": "Energía",
    "agua_refrigeracion": "Agua y refrigeración",
    "conectividad": "Conectividad",
    "riesgos_naturales": "Riesgos naturales",
    "suelo_regulatorio": "Suelo y regulación",
    "costes": "Costes",
    "mercado_talento": "Mercado y talento",
    "impacto": "Impacto",
}


def fmt(valor, decimales: int = 0) -> str:
    """Formatea un número con convención española (miles con punto, decimales con coma)."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(numero):
        return "—"
    texto = f"{numero:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_m(valor) -> str:
    """Formatea euros en millones: 1 234 567 -> '1,2 M€'."""
    try:
        numero = float(valor) / 1e6
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(numero) else f"{fmt(numero, 1)} M€"


def colorear_estado(valor) -> str:
    """Estilo de celda para la columna estado."""
    return f"background-color: {FONDO_ESTADO.get(valor, '#FFFFFF')}; font-weight: 600"


@st.cache_data
def leer_demo(ruta: str) -> pd.DataFrame:
    """Lee la tabla de municipios de demostración (el código INE se mantiene como texto)."""
    return pd.read_csv(ruta, dtype={"codigo_ine": str})


def sidebar_parametros(settings: dict) -> tuple[CPDParams, dict[str, float]]:
    """Dibuja los controles del CPD y de los pesos en la barra lateral."""
    d = settings["cpd_por_defecto"]
    tipos = list(TIPOS_REFRIGERACION)

    st.sidebar.header("Parámetros del CPD")
    potencia = st.sidebar.number_input("Potencia TI (MW)", 1.0, 500.0, float(d["potencia_ti_mw"]), 1.0)
    factor = st.sidebar.slider("Factor de carga", 0.3, 1.0, float(d["factor_carga"]), 0.05)
    tipo = st.sidebar.selectbox(
        "Tipo de refrigeración", tipos, index=tipos.index(d["tipo_refrigeracion"]),
    )
    renovable = st.sidebar.slider("Energía renovable (%)", 0, 100, int(round(d["pct_renovable"] * 100)), 5)
    latencia = st.sidebar.number_input("Latencia máxima (ms)", 1.0, 100.0, float(d["latencia_max_ms"]), 1.0)
    inversion = st.sidebar.number_input("Inversión CAPEX (M€)", 10.0, 5000.0, float(d["inversion_eur"]) / 1e6, 10.0)
    vida = st.sidebar.slider("Vida útil (años)", 5, 30, int(d["vida_util_anos"]))

    with st.sidebar.expander("Avanzado"):
        usar_pue = st.checkbox("Estimar el PUE por municipio", value=True)
        pue = st.number_input("PUE fijo (si no se estima)", 1.02, 3.0, float(d["pue"]), 0.01)
        autoproduccion = st.number_input("Autoproducción (MWh/año)", 0.0, 10_000_000.0, float(d["autoproduccion_mwh"]), 1000.0)
        personal = st.number_input("Personal fijo", 0, 1000, int(d["personal"]))
        wue = st.number_input("WUE (litros de agua por kWh)", 0.0, 5.0, float(d["wue_l_kwh"]), 0.05)

    with st.sidebar.expander("Pesos del score global"):
        pesos_raw = {
            bloque: st.slider(
                ETIQUETAS_BLOQUE[bloque], 0, 100, int(round(settings["pesos"][bloque] * 100)), 5,
                key=f"peso_{bloque}",
            )
            for bloque in INDICADORES_POR_BLOQUE
        }
        st.caption(f"Se renormalizan para sumar 100 %. Suma actual: {sum(pesos_raw.values())}.")

    params = CPDParams(
        potencia_ti_mw=float(potencia),
        factor_carga=float(factor),
        pue=float(pue),
        wue_l_kwh=float(wue),
        tipo_refrigeracion=tipo,
        pct_renovable=renovable / 100,
        autoproduccion_mwh=float(autoproduccion),
        inversion_eur=float(inversion) * 1e6,
        vida_util_anos=int(vida),
        personal=int(personal),
        latencia_max_ms=float(latencia),
        tier=d["tier"],
        usar_pue_estimado=usar_pue,
    )
    return params, pesos_raw


def render_ranking(res: pd.DataFrame) -> None:
    """Pestaña Ranking: contadores por estado y tabla ordenada con colores."""
    conteo = res["estado"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric(ESTADO_VIABLE, int(conteo.get(ESTADO_VIABLE, 0)))
    c2.metric(ESTADO_CONDICIONES, int(conteo.get(ESTADO_CONDICIONES, 0)))
    c3.metric(ESTADO_NO_VIABLE, int(conteo.get(ESTADO_NO_VIABLE, 0)))

    columnas = ["ranking", "municipio", "provincia", "estado", "score_global", "opex_eur", "van_eur", "impacto_local_pct"]
    tabla = res[[c for c in columnas if c in res.columns]].copy()
    tabla["motivos"] = res["motivos"].apply(lambda m: "; ".join(m) if isinstance(m, list) else "")
    formatos = {
        "score_global": lambda v: fmt(v, 1),
        "opex_eur": fmt_m,
        "van_eur": fmt_m,
        "impacto_local_pct": lambda v: fmt(v, 1) + " %" if fmt(v, 1) != "—" else "—",
    }
    estilo = (
        tabla.style.map(colorear_estado, subset=["estado"])
        .format({k: v for k, v in formatos.items() if k in tabla.columns})
    )
    st.dataframe(estilo, hide_index=True)
    st.caption(
        "Orden: primero Viable, después Viable con condiciones y al final No viable. "
        "Dentro de cada estado, de mayor a menor score global (0-100)."
    )


def render_mapa(res: pd.DataFrame) -> None:
    """Pestaña Mapa: municipios sobre OpenStreetMap, color por estado y tamaño por score."""
    datos = res.copy()
    datos["tamano"] = pd.to_numeric(datos["score_global"], errors="coerce").fillna(5).clip(lower=5)
    fig = px.scatter_map(
        datos,
        lat="lat",
        lon="lon",
        color="estado",
        size="tamano",
        size_max=26,
        hover_name="municipio",
        hover_data={"provincia": True, "score_global": ":.1f", "lat": False, "lon": False, "tamano": False, "estado": False},
        color_discrete_map=COLORES_ESTADO,
        category_orders={"estado": ORDEN_ESTADOS},
        zoom=4.6,
        center={"lat": 40.2, "lon": -3.7},
        map_style="open-street-map",
        height=620,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), legend_title_text="Estado")
    st.plotly_chart(fig)
    st.caption("El tamaño del punto es proporcional al score global. Los datos son de demostración sintética.")


def render_ficha(res: pd.DataFrame, sel: str) -> None:
    """Pestaña Ficha: estado, motivos, sub-scores y salidas del simulador de un municipio."""
    fila = res.loc[res["municipio"] == sel].iloc[0]
    estado = fila["estado"]
    mensaje = f"{fila['municipio']}: {estado} (score global {fmt(fila['score_global'], 1)} / 100, posición {int(fila['ranking'])})"
    if estado == ESTADO_VIABLE:
        st.success(mensaje)
    elif estado == ESTADO_CONDICIONES:
        st.warning(mensaje)
    else:
        st.error(mensaje)

    st.markdown("**Motivos**")
    for motivo in fila["motivos"] if isinstance(fila["motivos"], list) else []:
        st.markdown(f"- {motivo}")

    izquierda, derecha = st.columns(2)
    with izquierda:
        valores = [fila.get(f"sub_{b}") for b in INDICADORES_POR_BLOQUE]
        fig = go.Figure(go.Bar(
            x=[ETIQUETAS_BLOQUE[b] for b in INDICADORES_POR_BLOQUE],
            y=[None if pd.isna(v) else float(v) for v in valores],
            marker_color="#3B6E8F",
        ))
        fig.update_yaxes(range=[0, 100], title="Sub-score (0-100)")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), title="Sub-scores por bloque")
        st.plotly_chart(fig)
    with derecha:
        st.markdown("**Salidas del simulador**")
        m1, m2 = st.columns(2)
        m1.metric("Consumo anual", f"{fmt(fila['consumo_mwh'])} MWh")
        m2.metric("PUE aplicado", fmt(fila["pue_aplicado"], 2))
        m1.metric("Agua anual", f"{fmt(fila['agua_m3_anual'])} m³")
        m2.metric("CO2 anual", f"{fmt(fila['co2_t'])} t")
        m1.metric("Latencia RTT", f"{fmt(fila['latencia_rtt_ms'], 2)} ms")
        m2.metric("Impacto local", f"{fmt(fila['impacto_local_pct'], 1)} %")

    with st.expander("Todos los datos del municipio"):
        st.table(pd.DataFrame({"campo": fila.index.astype(str), "valor": [str(v) for v in fila.values]}))


def render_economico(res: pd.DataFrame, sel: str, params: CPDParams, settings: dict) -> None:
    """Pestaña Económico: desglose del OPEX, VAN, ROI, payback y flujo acumulado."""
    fila = res.loc[res["municipio"] == sel].iloc[0]
    st.markdown(f"**{sel}**: análisis económico con los parámetros actuales.")
    st.info(
        "Modelo simplificado: ingresos = alquiler de capacidad + parte de la energía repercutida al "
        "cliente (repercusion_energia_pct en settings.yaml), flujos constantes y sin inflación. "
        "Precios y porcentajes son valores iniciales a calibrar."
    )

    izquierda, derecha = st.columns(2)
    with izquierda:
        componentes = {
            "Energía": fila["opex_energia_eur"],
            "Agua": fila["opex_agua_eur"],
            "Personal": fila["opex_personal_eur"],
            "Mantenimiento": fila["opex_mantenimiento_eur"],
            "Impuestos locales": fila["opex_impuestos_eur"],
        }
        fig = go.Figure(go.Bar(
            x=list(componentes.values()), y=list(componentes.keys()), orientation="h", marker_color="#5B7F95",
        ))
        fig.update_layout(height=330, title="Desglose del OPEX anual (€)", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig)
    with derecha:
        a, b = st.columns(2)
        a.metric(
            "Ingresos anuales", fmt_m(fila["ingresos_anuales_eur"]),
            help=f"Alquiler {fmt_m(fila['ingresos_alquiler_eur'])} + energía repercutida {fmt_m(fila['ingresos_energia_eur'])}",
        )
        b.metric("OPEX anual", fmt_m(fila["opex_eur"]))
        a.metric("Flujo de caja anual", fmt_m(fila["flujo_caja_anual_eur"]))
        b.metric("CAPEX total", fmt_m(fila["capex_total_eur"]))
        a.metric("VAN", fmt_m(fila["van_eur"]))
        b.metric("ROI", "—" if pd.isna(fila["roi"]) else f"{fmt(fila['roi'] * 100, 1)} %")
        a.metric("Payback", "No se recupera" if pd.isna(fila["payback_anos"]) else f"{fmt(fila['payback_anos'], 1)} años")

    anios = int(params.vida_util_anos)
    flujo = float(fila["flujo_caja_anual_eur"])
    acumulado = [-float(fila["capex_total_eur"]) + flujo * t for t in range(anios + 1)]
    fig_flujo = go.Figure(go.Scatter(x=list(range(anios + 1)), y=acumulado, mode="lines+markers", line=dict(color="#2E7D5B")))
    fig_flujo.add_hline(y=0, line_dash="dash", line_color="#888")
    fig_flujo.update_layout(
        height=320, title="Flujo de caja acumulado sin descontar (€)",
        xaxis_title="Año", yaxis_title="€", margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig_flujo)


def render_prevision(settings: dict) -> None:
    """Pestaña Previsión: histórico de REData y previsión a 10 años con banda aproximada."""
    if not RUTA_DEMANDA_LIMPIA.exists():
        st.info(
            "Todavía no hay datos de demanda de REData. Para generarlos, desde la raíz del proyecto "
            "y con el venv activado, ejecuta:"
        )
        st.code("python -m cpd.etl.ree --inicio 2015 --fin 2025", language="bash")
        return
    try:
        datos = pd.read_csv(RUTA_DEMANDA_LIMPIA, parse_dates=["fecha"])
        serie = pd.Series(pd.to_numeric(datos["demanda_mwh"], errors="coerce").values, index=pd.DatetimeIndex(datos["fecha"]))
        prevision = prever_mensual(serie, horizonte_meses=120)
    except (KeyError, ValueError) as error:
        st.error(f"No se pudo generar la previsión: {error}")
        return

    historico_gwh = serie / 1000
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=historico_gwh.index, y=historico_gwh.values, name="Histórico (REData)", line=dict(color="#3B6E8F")))
    fig.add_trace(go.Scatter(x=prevision["fecha"], y=prevision["superior"] / 1000, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=prevision["fecha"], y=prevision["inferior"] / 1000, fill="tonexty", fillcolor="rgba(59,110,143,0.18)",
        line=dict(width=0), name="Intervalo aproximado",
    ))
    fig.add_trace(go.Scatter(x=prevision["fecha"], y=prevision["prevision"] / 1000, name="Previsión 10 años", line=dict(color="#C98A1B", dash="dash")))
    fig.update_layout(height=460, yaxis_title="GWh al mes", margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
    st.plotly_chart(fig)

    anual = prevision.assign(anio=prevision["fecha"].dt.year).groupby("anio")["prevision"].sum() / 1e6
    st.markdown("**Previsión de demanda anual (TWh)**")
    st.table(pd.DataFrame({"año": anual.index.astype(str), "TWh previstos": [fmt(v, 1) for v in anual.values]}))
    st.caption(
        "Modelo BASELINE: tendencia lineal anual × estacionalidad mensual media. El intervalo es "
        "aproximado (1,96 × desviación de residuos × raíz del año de horizonte). Pendiente de comparar "
        "con SARIMA o Prophet."
    )


def render_escenarios(df: pd.DataFrame, params: CPDParams, settings: dict, pesos: dict, res_base: pd.DataFrame) -> None:
    """Pestaña Escenarios: compara el ranking base con un escenario alternativo."""
    c1, c2, c3 = st.columns(3)
    pct = c1.slider("Variación del precio de la electricidad (%)", -30, 100, 20, 5)
    incremento = c2.slider("Aumento del estrés hídrico (sequía)", 0.0, 0.5, 0.15, 0.05)
    opciones = [f"Mantener ({params.tipo_refrigeracion})"] + list(TIPOS_REFRIGERACION)
    seleccion = c3.selectbox("Refrigeración del escenario", opciones)
    tipo_esc = None if seleccion.startswith("Mantener") else seleccion

    df_esc, params_esc, settings_esc = preparar_escenario(
        df, params, settings, pct_precio_electricidad=pct / 100,
        incremento_estres=incremento, tipo_refrigeracion=tipo_esc,
    )
    res_esc = evaluar(df_esc, params_esc, settings_esc, pesos)

    cols = ["municipio", "estado", "ranking", "score_global"]
    union = res_base[cols].merge(res_esc[cols], on="municipio", suffixes=("_base", "_esc"))
    union["cambio_posicion"] = union["ranking_base"] - union["ranking_esc"]
    union["delta_score"] = union["score_global_esc"] - union["score_global_base"]
    union = union.sort_values("ranking_esc")

    tabla = union[["municipio", "estado_base", "estado_esc", "ranking_base", "ranking_esc", "cambio_posicion", "score_global_base", "score_global_esc", "delta_score"]]
    estilo = (
        tabla.style.map(colorear_estado, subset=["estado_base", "estado_esc"])
        .format({"score_global_base": lambda v: fmt(v, 1), "score_global_esc": lambda v: fmt(v, 1), "delta_score": lambda v: fmt(v, 1)})
    )
    st.dataframe(estilo, hide_index=True)
    st.caption("Cambio de posición positivo = el municipio sube en el ranking del escenario.")

    fig = px.bar(union, x="municipio", y="delta_score", color="delta_score", color_continuous_scale="RdYlGn", labels={"delta_score": "Variación del score", "municipio": ""})
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig)


def main() -> None:
    """Punto de entrada de la aplicación Streamlit."""
    st.set_page_config(page_title="Viabilidad de CPD", layout="wide")
    st.title("Viabilidad de instalación de un CPD")
    st.caption("Filtros eliminatorios, score 0-100 por municipio, simulación de energía, agua y costes.")
    st.info(
        "Datos de demostración sintéticos. Los indicadores de data/demo/municipios_demo.csv son inventados "
        "pero plausibles: sirven para probar el sistema, no para tomar decisiones."
    )

    try:
        settings = cargar_settings()
    except (FileNotFoundError, ValueError, KeyError) as error:
        st.error(f"Error en la configuración (config/settings.yaml): {error}")
        st.stop()

    try:
        df = leer_demo(str(RUTA_DEMO))
    except FileNotFoundError:
        st.error(f"No se encuentra el fichero de datos: {RUTA_DEMO}")
        st.stop()

    params, pesos_raw = sidebar_parametros(settings)
    try:
        pesos = pesos_normalizados(pesos_raw, settings)
    except ValueError:
        st.sidebar.warning("La suma de pesos es cero: se usan los pesos por defecto.")
        pesos = pesos_normalizados(None, settings)

    try:
        resultado = evaluar(df, params, settings, pesos)
    except ValueError as error:
        st.error(f"No se pudo evaluar: {error}")
        st.stop()

    seleccion = st.sidebar.selectbox("Municipio para el detalle", resultado["municipio"].tolist(), key="municipio_detalle")

    pestanas = st.tabs(["Ranking", "Mapa", "Ficha municipio", "Económico", "Previsión demanda", "Escenarios"])
    with pestanas[0]:
        render_ranking(resultado)
    with pestanas[1]:
        render_mapa(resultado)
    with pestanas[2]:
        render_ficha(resultado, seleccion)
    with pestanas[3]:
        render_economico(resultado, seleccion, params, settings)
    with pestanas[4]:
        render_prevision(settings)
    with pestanas[5]:
        render_escenarios(df, params, settings, pesos, resultado)


# Streamlit ejecuta el script con __name__ == "__main__", así que esto arranca la app
# tanto con "streamlit run" como al ejecutarlo directamente.
if __name__ == "__main__":
    main()
