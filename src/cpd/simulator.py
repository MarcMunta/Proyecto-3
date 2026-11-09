"""Simulador de un CPD (data center): energía, agua, costes, CO2, latencia y finanzas.

Todas las funciones son puras (sin efectos secundarios) y documentan la fórmula
que implementan. Las unidades se indican en el nombre de cada variable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

HORAS_AL_ANO: int = 8760
HORAS_AL_DIA: int = 24
DIAS_AL_ANO: int = 365
MESES_AL_ANO: int = 12

# PUE base por tipo de refrigeración (heurística, ver pue_estimado).
PUE_BASE_POR_REFRIGERACION: dict[str, float] = {
    "aire": 1.45,
    "evaporativa": 1.25,
    "adiabatica": 1.20,
    "inmersion": 1.08,
}
TIPOS_REFRIGERACION: tuple[str, ...] = tuple(PUE_BASE_POR_REFRIGERACION)


@dataclass
class CPDParams:
    """Parámetros de entrada de un CPD. Los valores por defecto son razonables para un CPD de 50 MW.

    Attributes:
        potencia_ti_mw: potencia de los equipos de TI (MW).
        factor_carga: fracción media de la potencia TI utilizada (0-1).
        pue: PUE del CPD. Se usa si usar_pue_estimado es False.
        wue_l_kwh: consumo de agua por kWh de TI (litros/kWh).
        tipo_refrigeracion: aire | evaporativa | adiabatica | inmersion.
        pct_renovable: fracción de energía de origen renovable (0-1).
        autoproduccion_mwh: energía autoproducida anual (MWh) que no se compra.
        inversion_eur: CAPEX total (€).
        vida_util_anos: horizonte de análisis financiero (años).
        personal: número de empleados fijos.
        latencia_max_ms: latencia RTT máxima aceptable (ms).
        tier: nivel de disponibilidad (Uptime Institute), informativo.
        usar_pue_estimado: si True, el PUE se estima por municipio con pue_estimado().
    """

    potencia_ti_mw: float = 50.0
    factor_carga: float = 0.8
    pue: float = 1.3
    wue_l_kwh: float = 0.5
    tipo_refrigeracion: str = "aire"
    pct_renovable: float = 0.8
    autoproduccion_mwh: float = 0.0
    inversion_eur: float = 400e6
    vida_util_anos: int = 20
    personal: int = 60
    latencia_max_ms: float = 10.0
    tier: str = "III"
    usar_pue_estimado: bool = True


def potencia_total_mw(potencia_ti_mw: float, pue: float) -> float:
    """Potencia total con refrigeración y pérdidas incluidas.

    Fórmula: potencia_total_mw = potencia_ti_mw × pue

    Args:
        potencia_ti_mw: potencia TI (MW).
        pue: PUE aplicado.

    Returns:
        Potencia total (MW).
    """
    return potencia_ti_mw * pue


def consumo_anual_mwh(potencia_ti_mw: float, factor_carga: float, pue: float) -> float:
    """Consumo eléctrico anual del CPD.

    Fórmula: consumo_anual_mwh = potencia_ti_mw × factor_carga × pue × 8760

    Ejemplo: 50 MW × 0.8 × 1.3 × 8760 = 455 520 MWh.

    Args:
        potencia_ti_mw: potencia TI (MW).
        factor_carga: factor de carga medio (0-1).
        pue: PUE aplicado.

    Returns:
        Energía consumida en un año (MWh).
    """
    return potencia_ti_mw * factor_carga * pue * HORAS_AL_ANO


def agua_l_dia(potencia_ti_mw: float, factor_carga: float, wue_l_kwh: float) -> float:
    """Consumo de agua diario de refrigeración.

    Fórmula: agua_l_dia = potencia_ti_mw × 1000 × factor_carga × 24 × wue_l_kwh
    (potencia_ti_mw × 1000 = kW de TI; × 24 = kWh/día; × WUE = litros/día).

    Args:
        potencia_ti_mw: potencia TI (MW).
        factor_carga: factor de carga medio (0-1).
        wue_l_kwh: litros de agua por kWh de TI.

    Returns:
        Agua consumida en un día (litros).
    """
    return potencia_ti_mw * 1000 * factor_carga * HORAS_AL_DIA * wue_l_kwh


def agua_m3_anual(potencia_ti_mw: float, factor_carga: float, wue_l_kwh: float) -> float:
    """Consumo de agua anual en m³ a partir del consumo diario.

    Fórmula: agua_m3_anual = agua_l_dia × 365 / 1000

    Args:
        potencia_ti_mw: potencia TI (MW).
        factor_carga: factor de carga medio (0-1).
        wue_l_kwh: litros de agua por kWh de TI.

    Returns:
        Agua anual (m³).
    """
    return agua_l_dia(potencia_ti_mw, factor_carga, wue_l_kwh) * DIAS_AL_ANO / 1000


def coste_energia_eur(consumo_mwh: float, autoproduccion_mwh: float, precio_eur_mwh: float) -> float:
    """Coste anual de la energía comprada a la red.

    Fórmula: coste_energia_eur = max(consumo − autoproducción, 0) × precio_eur_mwh

    Args:
        consumo_mwh: consumo anual (MWh).
        autoproduccion_mwh: energía autoproducida (MWh).
        precio_eur_mwh: precio de compra (€/MWh).

    Returns:
        Coste anual de energía (€).
    """
    return max(consumo_mwh - autoproduccion_mwh, 0.0) * precio_eur_mwh


def coste_agua_eur(agua_m3: float, precio_agua_eur_m3: float) -> float:
    """Coste anual del agua.

    Fórmula: coste_agua_eur = agua_m3 × precio_agua_eur_m3

    Args:
        agua_m3: agua anual (m³).
        precio_agua_eur_m3: precio del agua (€/m³).

    Returns:
        Coste anual de agua (€).
    """
    return agua_m3 * precio_agua_eur_m3


def desglose_opex(
    coste_energia: float,
    coste_agua: float,
    personal: int,
    salario_medio_eur: float,
    inversion_eur: float,
    mantenimiento_pct: float,
    impuestos_pct: float,
) -> dict[str, float]:
    """Desglose del OPEX anual en sus componentes.

    Fórmulas:
        energía = coste_energia (ver coste_energia_eur)
        agua = coste_agua (ver coste_agua_eur)
        personal = personal × salario_medio
        mantenimiento = inversión × mantenimiento_pct
        impuestos_locales = inversión × impuestos_pct

    Args:
        coste_energia: coste anual de energía (€).
        coste_agua: coste anual de agua (€).
        personal: número de empleados.
        salario_medio_eur: salario medio anual (€).
        inversion_eur: CAPEX (€), base de mantenimiento e impuestos.
        mantenimiento_pct: % anual de la inversión para mantenimiento (fracción).
        impuestos_pct: % anual de la inversión para impuestos locales (fracción).

    Returns:
        Diccionario con cada componente y la clave "total".
    """
    desglose = {
        "energia": coste_energia,
        "agua": coste_agua,
        "personal": personal * salario_medio_eur,
        "mantenimiento": inversion_eur * mantenimiento_pct,
        "impuestos_locales": inversion_eur * impuestos_pct,
    }
    desglose["total"] = sum(desglose.values())
    return desglose


def opex_eur(
    coste_energia: float,
    coste_agua: float,
    personal: int,
    salario_medio_eur: float,
    inversion_eur: float,
    mantenimiento_pct: float,
    impuestos_pct: float,
) -> float:
    """OPEX anual total (€): suma de los componentes de desglose_opex.

    Fórmula: opex = energía + agua + personal × salario + inversión × mantenimiento% + inversión × impuestos%

    Returns:
        OPEX anual total (€).
    """
    return desglose_opex(
        coste_energia, coste_agua, personal, salario_medio_eur,
        inversion_eur, mantenimiento_pct, impuestos_pct,
    )["total"]


def co2_t(consumo_mwh: float, pct_renovable: float, factor_emision_t_mwh: float) -> float:
    """Emisiones anuales de CO2 asociadas al consumo no renovable.

    Fórmula: co2_t = consumo_mwh × (1 − pct_renovable) × factor_emision_t_mwh

    Args:
        consumo_mwh: consumo anual (MWh).
        pct_renovable: fracción renovable (0-1).
        factor_emision_t_mwh: t CO2 por MWh no renovable.

    Returns:
        Emisiones anuales (t CO2).
    """
    return consumo_mwh * (1 - pct_renovable) * factor_emision_t_mwh


def impacto_local_pct(consumo_cpd_mwh: float, consumo_municipal_mwh: float | None) -> float | None:
    """Peso del CPD sobre el consumo eléctrico municipal.

    Fórmula: impacto_local_pct = consumo_cpd / consumo_municipal × 100.
    Si el consumo municipal es nulo, ausente o no positivo devuelve None (evita la división por cero).

    Returns:
        Porcentaje (>= 0) o None.
    """
    if consumo_municipal_mwh is None or not np.isfinite(consumo_municipal_mwh) or consumo_municipal_mwh <= 0:
        return None
    return consumo_cpd_mwh / consumo_municipal_mwh * 100


def latencia_rtt_ms(distancia_km: float, factor_ruta: float = 1.5, ms_rtt_por_km: float = 0.01) -> float:
    """Latencia de ida y vuelta (RTT) estimada hasta un punto de red.

    Fórmula: latencia_rtt_ms = distancia_km × 0.01 × factor_ruta
    (en fibra la señal tarda ~5 µs/km por sentido, es decir ~0.01 ms de RTT por km).

    Args:
        distancia_km: distancia en línea recta (km).
        factor_ruta: factor por trazado real de la fibra (por defecto 1.5).
        ms_rtt_por_km: ms de RTT por km de fibra.

    Returns:
        Latencia RTT estimada (ms).
    """
    return distancia_km * ms_rtt_por_km * factor_ruta


def horas_free_cooling(temperaturas_horarias_c: Iterable[float], umbral_c: float = 18.0) -> int:
    """Número de horas en las que la temperatura exterior permite enfriamiento gratuito.

    Cuenta las horas con temperatura estrictamente inferior al umbral. Los valores
    NaN se ignoran (no cuentan como horas válidas).

    Args:
        temperaturas_horarias_c: serie de temperaturas horarias (°C).
        umbral_c: temperatura máxima para free cooling (°C).

    Returns:
        Número de horas.
    """
    temps = np.asarray(list(temperaturas_horarias_c), dtype=float)
    temps = temps[np.isfinite(temps)]
    return int(np.count_nonzero(temps < umbral_c))


def pue_estimado(temp_media_c: float, tipo_refrigeracion: str) -> float:
    """Estimación heurística del PUE a partir de la temperatura media y el tipo de refrigeración.

    HEURÍSTICA (no es un modelo físico calibrado):
        pue = PUE_base[tipo] + 0.01 × (temp_media_c − 15), con el ajuste acotado a [−0.10, +0.15]
        y un mínimo de 1.02.
    - PUE_base: aire 1.45, evaporativa 1.25, adiabática 1.20, inmersión 1.08.
    - Municipios más fríos tienen menor PUE; la inmersión es el tipo con menor PUE.

    Args:
        temp_media_c: temperatura media anual (°C).
        tipo_refrigeracion: aire | evaporativa | adiabatica | inmersion.

    Returns:
        PUE estimado (>= 1.02).

    Raises:
        ValueError: si el tipo de refrigeración no es válido.
    """
    if tipo_refrigeracion not in PUE_BASE_POR_REFRIGERACION:
        raise ValueError(f"Tipo de refrigeración no válido: {tipo_refrigeracion}")
    if temp_media_c is None or not np.isfinite(temp_media_c):
        return PUE_BASE_POR_REFRIGERACION[tipo_refrigeracion]
    ajuste = float(np.clip(0.01 * (temp_media_c - 15.0), -0.10, 0.15))
    return max(PUE_BASE_POR_REFRIGERACION[tipo_refrigeracion] + ajuste, 1.02)


def ingresos_anuales_eur(potencia_ti_mw: float, precio_venta_eur_kw_mes: float, ocupacion: float) -> float:
    """Ingresos anuales por alquiler de capacidad (colocation).

    Fórmula: ingresos = potencia_ti_mw × 1000 × precio_eur_kw_mes × 12 × ocupacion

    Returns:
        Ingresos anuales (€).
    """
    return potencia_ti_mw * 1000 * precio_venta_eur_kw_mes * MESES_AL_ANO * ocupacion


def van(flujos: Sequence[float], tasa: float, inversion: float) -> float:
    """Valor Actual Neto de una serie de flujos anuales.

    Fórmula: VAN = −inversión + Σ_{t=1..n} flujo_t / (1 + tasa)^t

    Args:
        flujos: flujos de caja netos de los años 1..n (€).
        tasa: tasa de descuento (fracción).
        inversion: inversión inicial (€), en t=0.

    Returns:
        VAN (€).
    """
    return -inversion + sum(f / (1 + tasa) ** t for t, f in enumerate(flujos, start=1))


def roi(flujos: Sequence[float], inversion: float) -> float | None:
    """Retorno sobre la inversión (sin descontar).

    Fórmula: ROI = (Σ flujos − inversión) / inversión

    Returns:
        ROI como fracción (0.5 = 50 %) o None si la inversión no es positiva.
    """
    if inversion <= 0:
        return None
    return (sum(flujos) - inversion) / inversion


def payback_anos(flujos: Sequence[float], inversion: float) -> float | None:
    """Plazo de recuperación de la inversión (sin descontar), con interpolación lineal.

    Returns:
        Años hasta recuperar la inversión, o None si no se recupera en el horizonte.
    """
    acumulado = -inversion
    for anio, flujo in enumerate(flujos, start=1):
        anterior = acumulado
        acumulado += flujo
        if acumulado >= 0:
            if flujo <= 0:
                return float(anio)
            return float(anio - 1 + (-anterior) / flujo)
    return None
