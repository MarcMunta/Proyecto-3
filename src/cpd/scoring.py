"""Filtros eliminatorios, sub-scores 0-100, score global, ranking y evaluación por municipio.

Flujo del embudo (3 fases, según el diseño del proyecto):
1. Filtros eliminatorios (M1, M3, M4, M5, M6): aplicar_filtros() devuelve el estado y los motivos.
   - Cualquier KO -> "No viable".
   - Cualquier condición -> "Viable con condiciones".
   - Si no hay ninguna -> "Viable".
2. Sub-scores 0-100 por bloque (energía, agua, conectividad, riesgos, suelo, costes,
   mercado/talento, impacto) mediante normalización min-max entre municipios.
3. Score global = media ponderada de los sub-scores con los pesos de settings.yaml.
   Los municipios "No viable" conservan su score pero se ordenan después de los viables.

evaluar() combina todo y devuelve un DataFrame con una fila por municipio.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

import numpy as np
import pandas as pd

from cpd import simulator as sim
from cpd.simulator import CPDParams

ESTADO_VIABLE: str = "Viable"
ESTADO_CONDICIONES: str = "Viable con condiciones"
ESTADO_NO_VIABLE: str = "No viable"
ORDEN_ESTADO: dict[str, int] = {ESTADO_VIABLE: 0, ESTADO_CONDICIONES: 1, ESTADO_NO_VIABLE: 2}

# Para cada bloque: lista de (columna, dirección). Dirección +1 = mejor cuanto MAYOR;
# -1 = mejor cuanto MENOR. Cada bloque es la media de sus indicadores normalizados.
INDICADORES_POR_BLOQUE: dict[str, list[tuple[str, int]]] = {
    "energia": [
        ("capacidad_acceso_mw", +1),       # más capacidad de acceso a la red
        ("dist_subestacion_km", -1),       # subestación más cercana
        ("tension_subestacion_kv", +1),    # mayor tensión de la subestación
    ],
    "agua_refrigeracion": [
        ("estres_hidrico_idx", -1),        # menor estrés hídrico
        ("pue_aplicado", -1),              # menor PUE => menos energía de refrigeración
        ("humedad_media_pct", -1),         # menos humedad: mejor para evaporativa
    ],
    "conectividad": [
        ("latencia_rtt_ms", -1),           # menor latencia hasta el punto de red
        ("cobertura_fibra_pct", +1),       # mayor cobertura de fibra
    ],
    "riesgos_naturales": [
        ("peligrosidad_sismica_g", -1),    # menor aceleración sísmica
        ("temp_max_hist_c", -1),           # menor temperatura extrema histórica
        ("dias_calor_extremo", -1),        # menos días de calor extremo
    ],
    "suelo_regulatorio": [
        ("precio_suelo_eur_m2", -1),       # suelo más barato
        ("suelo_industrial_ha", +1),       # más suelo industrial disponible
        ("dist_autopista_km", -1),         # mejor accesibilidad por carretera
    ],
    "costes": [
        ("opex_eur", -1),                  # OPEX anual más bajo
        ("capex_total_eur", -1),           # inversión total más baja
    ],
    "mercado_talento": [
        ("poblacion", +1),                 # mercado laboral y de clientes
        ("tasa_paro", -1),                 # más paro => más talento disponible
        ("pct_estudios_superiores", +1),   # más formación superior
        ("dist_aeropuerto_km", -1),        # logística y desplazamientos
    ],
    "impacto": [
        ("impacto_local_pct", -1),         # menor peso sobre el consumo municipal
        ("co2_t", -1),                     # menores emisiones anuales
    ],
}

# Columnas de entrada que se rellenan con NaN si no existen (la app no se rompe).
COLUMNAS_ENTRADA: tuple[str, ...] = (
    "codigo_ine", "municipio", "provincia", "ccaa", "lat", "lon", "poblacion", "tasa_paro",
    "pct_estudios_superiores", "dist_subestacion_km", "tension_subestacion_kv", "capacidad_acceso_mw",
    "consumo_electrico_municipal_mwh", "temp_media_c", "temp_max_hist_c", "humedad_media_pct",
    "dias_calor_extremo", "estres_hidrico_idx", "consumo_hidrico_municipal_m3", "cobertura_fibra_pct",
    "dist_ixp_km", "dist_autopista_km", "dist_aeropuerto_km", "precio_suelo_eur_m2",
    "suelo_industrial_ha", "zona_inundable", "red_natura", "peligrosidad_sismica_g",
)


def _valor(fila: Mapping[str, Any], columna: str) -> float:
    """Devuelve el valor de una columna como float, o NaN si falta o no es numérico."""
    try:
        return float(fila.get(columna))
    except (TypeError, ValueError):
        return float("nan")


def _finito(valor: float) -> bool:
    """True si el valor es un número finito (no NaN ni infinito)."""
    return bool(np.isfinite(valor))


def pesos_normalizados(pesos: Mapping[str, float] | None, settings: dict[str, Any]) -> dict[str, float]:
    """Devuelve los pesos de los bloques renormalizados para que sumen 1.

    Args:
        pesos: pesos elegidos por el usuario (None = usar los de settings).
        settings: configuración cargada con cargar_settings().

    Returns:
        Diccionario bloque -> peso (suma 1).

    Raises:
        ValueError: si algún peso es negativo o la suma es cero.
    """
    origen = dict(settings["pesos"]) if pesos is None else dict(pesos)
    bloques = list(INDICADORES_POR_BLOQUE)
    valores = {bloque: float(origen.get(bloque, 0.0)) for bloque in bloques}
    if any(v < 0 for v in valores.values()):
        raise ValueError("Los pesos no pueden ser negativos")
    total = sum(valores.values())
    if total <= 0:
        raise ValueError("La suma de pesos debe ser mayor que cero")
    return {bloque: v / total for bloque, v in valores.items()}


def aplicar_filtros(
    fila: Mapping[str, Any],
    params: CPDParams,
    settings: dict[str, Any],
) -> tuple[str, list[str]]:
    """Aplica los filtros eliminatorios y condicionales a un municipio.

    Reglas KO (-> "No viable"):
        - zona inundable (M5) = 1.
        - Red Natura 2000 (M4) = 1.
        - CPD > umbral_potencia_subestacion_mw y distancia a subestación > dist_subestacion_max_km (M1).
        - capacidad de acceso < potencia total (M1).
        - latencia RTT > latencia máxima del CPD (M3).
        - estrés hídrico >= umbral y refrigeración evaporativa/adiabática (M6).
    Reglas condicionales (-> "Viable con condiciones"):
        - peligrosidad sísmica >= 0.16 g (M5).
        - estrés hídrico >= umbral con refrigeración aire/inmersión (M6).
        - temperatura máxima histórica >= 44 °C (M6).
        - suelo industrial disponible < mínimo (M4).

    Los datos ausentes no provocan KO: se avisan en los motivos.

    Args:
        fila: datos de un municipio (dict o fila de pandas), con pue_aplicado si ya está calculado.
        params: parámetros del CPD.
        settings: configuración con umbrales y latencia.

    Returns:
        Tupla (estado, motivos).
    """
    um = settings["umbrales"]
    lat = settings["latencia"]
    ko: list[str] = []
    condiciones: list[str] = []

    zona_inundable = _valor(fila, "zona_inundable")
    red_natura = _valor(fila, "red_natura")
    dist_sub = _valor(fila, "dist_subestacion_km")
    capacidad = _valor(fila, "capacidad_acceso_mw")
    dist_ixp = _valor(fila, "dist_ixp_km")
    estres = _valor(fila, "estres_hidrico_idx")
    sismica = _valor(fila, "peligrosidad_sismica_g")
    temp_max = _valor(fila, "temp_max_hist_c")
    suelo_ha = _valor(fila, "suelo_industrial_ha")

    pue = _valor(fila, "pue_aplicado")
    if not _finito(pue):
        pue = params.pue
    potencia_total = sim.potencia_total_mw(params.potencia_ti_mw, pue)
    latencia = sim.latencia_rtt_ms(dist_ixp, lat["factor_ruta"], lat["ms_rtt_por_km"]) if _finito(dist_ixp) else float("nan")

    # --- M5 riesgos naturales / M4 regulatorio: exclusiones ---
    if um.get("zona_inundable_ko", True) and zona_inundable == 1:
        ko.append("Zona inundable (M5): exclusión por riesgo de inundación")
    if um.get("red_natura_ko", True) and red_natura == 1:
        ko.append("Espacio Red Natura 2000 (M4): exclusión regulatoria")

    # --- M1 capacidad eléctrica ---
    if params.potencia_ti_mw > um["umbral_potencia_subestacion_mw"] and _finito(dist_sub):
        if dist_sub > um["dist_subestacion_max_km"]:
            ko.append(
                f"Subestación a {dist_sub:.1f} km; el límite para CPD > "
                f"{um['umbral_potencia_subestacion_mw']} MW es {um['dist_subestacion_max_km']} km (M1)"
            )
    if _finito(capacidad) and capacidad < potencia_total:
        ko.append(f"Capacidad de acceso {capacidad:.0f} MW < potencia total {potencia_total:.1f} MW (M1)")

    # --- M3 conectividad ---
    if _finito(latencia) and latencia > params.latencia_max_ms:
        ko.append(f"Latencia RTT {latencia:.2f} ms > máximo {params.latencia_max_ms} ms (M3)")

    # --- M6 agua y refrigeración ---
    evaporativa = params.tipo_refrigeracion in ("evaporativa", "adiabatica")
    estres_alto = _finito(estres) and estres >= um["estres_hidrico_alto"]
    if estres_alto and evaporativa:
        ko.append(
            f"Estrés hídrico {estres:.2f} con refrigeración {params.tipo_refrigeracion} (M6): "
            "consumo de agua no sostenible"
        )
    elif estres_alto:
        condiciones.append(
            f"Estrés hídrico alto ({estres:.2f}): requiere fuente de agua alternativa o refrigeración "
            "sin agua (M6)"
        )

    # --- Condicionales ---
    if _finito(sismica) and sismica >= um["peligrosidad_sismica_condicionado_g"]:
        condiciones.append(
            f"Peligrosidad sísmica {sismica:.2f} g >= {um['peligrosidad_sismica_condicionado_g']} g: "
            "diseño sísmico reforzado (M5)"
        )
    if _finito(temp_max) and temp_max >= um["temperatura_max_hist_condicionado_c"]:
        condiciones.append(
            f"Temperatura máxima histórica {temp_max:.1f} °C: refrigeración de reserva (M6)"
        )
    if _finito(suelo_ha) and suelo_ha < um["suelo_industrial_min_ha"]:
        condiciones.append(
            f"Suelo industrial disponible {suelo_ha:.1f} ha < {um['suelo_industrial_min_ha']} ha (M4)"
        )

    # --- Datos ausentes: se avisan, no cambian el estado ---
    ausentes = [
        nombre for nombre, valor in [
            ("zona_inundable", zona_inundable), ("red_natura", red_natura),
            ("dist_subestacion_km", dist_sub), ("capacidad_acceso_mw", capacidad),
            ("dist_ixp_km", dist_ixp), ("estres_hidrico_idx", estres),
            ("peligrosidad_sismica_g", sismica),
        ] if not _finito(valor)
    ]
    avisos = [f"Aviso: datos ausentes ({', '.join(ausentes)}); esos filtros no se han podido evaluar"] if ausentes else []

    if ko:
        return ESTADO_NO_VIABLE, ko + condiciones + avisos
    if condiciones:
        return ESTADO_CONDICIONES, condiciones + avisos
    return ESTADO_VIABLE, ["Cumple todos los filtros eliminatorios (M1, M3, M4, M5, M6)"] + avisos


def normalizar_min_max(serie: pd.Series, direccion: int) -> pd.Series:
    """Normaliza una serie a 0-100 mediante min-max, con el sentido indicado.

    Fórmula: norm = (x − min) / (max − min) × 100; si la dirección es −1 se invierte (100 − norm),
    de forma que 100 siempre significa "mejor". Si todos los valores son iguales se asigna 100
    (ningún municipio queda penalizado por ese indicador). Los NaN se mantienen como NaN.

    Args:
        serie: valores de un indicador entre municipios.
        direccion: +1 si mayor es mejor, −1 si menor es mejor.

    Returns:
        Serie con valores entre 0 y 100 (o NaN).
    """
    numeros = pd.to_numeric(serie, errors="coerce").astype(float)
    minimo, maximo = numeros.min(), numeros.max()
    if not _finito(minimo) or not _finito(maximo):
        return pd.Series(np.nan, index=serie.index, dtype=float)
    if maximo == minimo:
        norm = pd.Series(np.where(numeros.notna(), 100.0, np.nan), index=serie.index, dtype=float)
    else:
        norm = (numeros - minimo) / (maximo - minimo) * 100
        if direccion < 0:
            norm = 100 - norm
    return norm.clip(0, 100)


def calcular_sub_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula los sub-scores 0-100 de cada bloque (columnas sub_<bloque>).

    Cada bloque es la media de sus indicadores normalizados con normalizar_min_max.

    Args:
        df: tabla de municipios con las columnas de INDICADORES_POR_BLOQUE.

    Returns:
        DataFrame con una columna por bloque, mismo índice que df.
    """
    sub = {}
    for bloque, indicadores in INDICADORES_POR_BLOQUE.items():
        normalizados = []
        for columna, direccion in indicadores:
            if columna in df.columns:
                normalizados.append(normalizar_min_max(df[columna], direccion))
        if normalizados:
            sub[f"sub_{bloque}"] = pd.concat(normalizados, axis=1).mean(axis=1, skipna=True)
        else:
            sub[f"sub_{bloque}"] = pd.Series(np.nan, index=df.index, dtype=float)
    return pd.DataFrame(sub, index=df.index)


def calcular_score_global(sub: pd.DataFrame, pesos: Mapping[str, float]) -> pd.Series:
    """Score global 0-100 como media ponderada de los sub-scores.

    Fórmula: score = Σ_b peso_b × sub_b / Σ_b peso_b (solo bloques con dato en esa fila).
    Como los pesos suman 1 y los sub-scores están en [0, 100], el resultado está en [0, 100].

    Args:
        sub: DataFrame de sub-scores (columnas sub_<bloque>).
        pesos: pesos por bloque (sin el prefijo sub_).

    Returns:
        Serie con el score global (NaN si no hay ningún sub-score disponible).
    """
    bloques = [c.replace("sub_", "", 1) for c in sub.columns]
    w = pd.Series({c: float(pesos.get(b, 0.0)) for c, b in zip(sub.columns, bloques)})
    ponderado = sub.mul(w, axis=1).sum(axis=1, skipna=True)
    peso_valido = sub.notna().mul(w, axis=1).sum(axis=1)
    return (ponderado / peso_valido.replace(0, np.nan)).round(1)


def simular_municipio(fila: Mapping[str, Any], params: CPDParams, settings: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta el simulador para un municipio concreto con sus datos locales.

    Usa temp_media_c para estimar el PUE (si params.usar_pue_estimado), dist_ixp_km para la
    latencia, precio_suelo_eur_m2 para el coste del terreno y consumo_electrico_municipal_mwh
    para el impacto local.

    Returns:
        Diccionario con las salidas del simulador (ver evaluar()).
    """
    pr = settings["precios"]
    lat = settings["latencia"]
    terreno = settings.get("terreno", {})

    temp = _valor(fila, "temp_media_c")
    if params.usar_pue_estimado:
        pue = sim.pue_estimado(temp, params.tipo_refrigeracion)
    else:
        pue = params.pue
    pue_est = sim.pue_estimado(temp, params.tipo_refrigeracion) if _finito(temp) else float("nan")

    consumo = sim.consumo_anual_mwh(params.potencia_ti_mw, params.factor_carga, pue)
    agua_m3 = sim.agua_m3_anual(params.potencia_ti_mw, params.factor_carga, params.wue_l_kwh)
    c_energia = sim.coste_energia_eur(consumo, params.autoproduccion_mwh, pr["precio_electricidad_eur_mwh"])
    c_agua = sim.coste_agua_eur(agua_m3, pr["precio_agua_eur_m3"])
    desglose = sim.desglose_opex(
        c_energia, c_agua, params.personal, pr["salario_medio_eur"], params.inversion_eur,
        pr["mantenimiento_pct_inversion"], pr["impuestos_locales_pct_inversion"],
    )

    precio_suelo = _valor(fila, "precio_suelo_eur_m2")
    superficie_m2 = params.potencia_ti_mw * terreno.get("superficie_ha_por_mw", 0.1) * 10_000
    coste_suelo = precio_suelo * superficie_m2 if _finito(precio_suelo) else 0.0
    capex_total = params.inversion_eur + coste_suelo

    # Ingresos = alquiler de capacidad + parte de la energía repercutida al cliente.
    # En colocation la energía suele facturarse aparte; sin esta repercusión el VAN sale negativo
    # en todos los municipios. Con repercusión parcial (< 1) el precio de la luz sigue afectando al ROI.
    ingresos_alquiler = sim.ingresos_anuales_eur(params.potencia_ti_mw, pr["precio_venta_eur_kw_mes"], pr["ocupacion"])
    ingresos_energia = c_energia * pr.get("repercusion_energia_pct", 0.0)
    ingresos = ingresos_alquiler + ingresos_energia
    flujo_anual = ingresos - desglose["total"]
    flujos = [flujo_anual] * int(params.vida_util_anos)

    consumo_municipal = _valor(fila, "consumo_electrico_municipal_mwh")
    dist_ixp = _valor(fila, "dist_ixp_km")

    return {
        "pue_estimado": pue_est,
        "pue_aplicado": pue,
        "potencia_total_mw": sim.potencia_total_mw(params.potencia_ti_mw, pue),
        "consumo_mwh": consumo,
        "agua_m3_anual": agua_m3,
        "coste_energia_eur": c_energia,
        "opex_energia_eur": desglose["energia"],
        "opex_agua_eur": desglose["agua"],
        "opex_personal_eur": desglose["personal"],
        "opex_mantenimiento_eur": desglose["mantenimiento"],
        "opex_impuestos_eur": desglose["impuestos_locales"],
        "opex_eur": desglose["total"],
        "co2_t": sim.co2_t(consumo, params.pct_renovable, pr["factor_emision_t_mwh"]),
        "impacto_local_pct": sim.impacto_local_pct(consumo, consumo_municipal),
        "latencia_rtt_ms": sim.latencia_rtt_ms(dist_ixp, lat["factor_ruta"], lat["ms_rtt_por_km"]) if _finito(dist_ixp) else float("nan"),
        "coste_suelo_eur": coste_suelo,
        "capex_total_eur": capex_total,
        "ingresos_alquiler_eur": ingresos_alquiler,
        "ingresos_energia_eur": ingresos_energia,
        "ingresos_anuales_eur": ingresos,
        "flujo_caja_anual_eur": flujo_anual,
        "van_eur": sim.van(flujos, pr["tasa_descuento"], capex_total),
        "roi": sim.roi(flujos, capex_total),
        "payback_anos": sim.payback_anos(flujos, capex_total),
    }


def evaluar(
    df: pd.DataFrame,
    params: CPDParams,
    settings: dict[str, Any],
    pesos: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Evalúa todos los municipios: simulador, filtros, sub-scores, score global y ranking.

    Orden del resultado: primero "Viable", luego "Viable con condiciones" y luego "No viable";
    dentro de cada estado, de mayor a menor score_global.

    Args:
        df: tabla de municipios (ver data/demo/municipios_demo.csv).
        params: parámetros del CPD.
        settings: configuración de settings.yaml.
        pesos: pesos opcionales por bloque (se renormalizan); None = los de settings.

    Returns:
        DataFrame con los datos originales, las salidas del simulador, estado, motivos,
        sub_<bloque>, score_global y ranking.

    Raises:
        ValueError: si df está vacío o los pesos no son válidos.
    """
    if df is None or df.empty:
        raise ValueError("La tabla de municipios está vacía")

    base = df.copy()
    for columna in COLUMNAS_ENTRADA:
        if columna not in base.columns:
            base[columna] = np.nan

    simulados = pd.DataFrame(
        [simular_municipio(fila, params, settings) for _, fila in base.iterrows()],
        index=base.index,
    )
    out = pd.concat([base, simulados], axis=1)

    resultados = [aplicar_filtros(fila, params, settings) for _, fila in out.iterrows()]
    out["estado"] = [estado for estado, _ in resultados]
    out["motivos"] = [motivos for _, motivos in resultados]

    sub = calcular_sub_scores(out)
    out = pd.concat([out, sub], axis=1)
    out["score_global"] = calcular_score_global(sub, pesos_normalizados(pesos, settings))

    out["_orden"] = out["estado"].map(ORDEN_ESTADO)
    out = out.sort_values(["_orden", "score_global"], ascending=[True, False], na_position="last")
    out = out.drop(columns="_orden")
    out.insert(0, "ranking", range(1, len(out) + 1))
    return out


def preparar_escenario(
    df: pd.DataFrame,
    params: CPDParams,
    settings: dict[str, Any],
    pct_precio_electricidad: float = 0.0,
    incremento_estres: float = 0.0,
    tipo_refrigeracion: str | None = None,
) -> tuple[pd.DataFrame, CPDParams, dict[str, Any]]:
    """Construye un escenario alternativo a partir del caso base (sin modificar los originales).

    Args:
        df: tabla de municipios base.
        params: parámetros base del CPD.
        settings: configuración base.
        pct_precio_electricidad: variación del precio de la electricidad (0.2 = +20 %).
        incremento_estres: suma al índice de estrés hídrico de cada municipio (sequía), limitado a [0, 1].
        tipo_refrigeracion: cambio de tipo de refrigeración (None = mantener).

    Returns:
        Tupla (df_escenario, params_escenario, settings_escenario).
    """
    df_esc = df.copy()
    if "estres_hidrico_idx" in df_esc.columns and incremento_estres:
        df_esc["estres_hidrico_idx"] = (
            pd.to_numeric(df_esc["estres_hidrico_idx"], errors="coerce") + incremento_estres
        ).clip(0, 1)

    params_esc = copy.deepcopy(params)
    if tipo_refrigeracion is not None:
        params_esc.tipo_refrigeracion = tipo_refrigeracion

    settings_esc = copy.deepcopy(settings)
    settings_esc["precios"]["precio_electricidad_eur_mwh"] = (
        settings["precios"]["precio_electricidad_eur_mwh"] * (1 + pct_precio_electricidad)
    )
    return df_esc, params_esc, settings_esc
