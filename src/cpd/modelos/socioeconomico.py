"""Impacto socioeconómico del CPD (variables E39 empleo generado, E40 inversión inducida y E41 PIB), añadido el
18/11/2026. Modelo input-output de Leontief tipo I con las Tablas Input-Output 2022 del INE (recomendación, no viene
de clase: es el método estándar de la contabilidad nacional para efectos indirectos).

Idea: un euro que el CPD gasta en un proveedor español obliga a ese proveedor a producir, y a sus proveedores, y así
sucesivamente. La **matriz inversa interior de Leontief** (L, Tabla 7 del INE) da la producción interior total que
genera cada euro de demanda; con el empleo y el VAB por euro producido de cada rama (Tabla 1) se pasa a empleos y VAB.

- **Construcción (una vez):** el CAPEX del CPD repartido por productos (`settings.yaml → impacto_socioeconomico`,
  **supuesto a calibrar**: obra civil, equipo eléctrico, maquinaria de refrigeración, ingeniería e instalación). Solo
  cuenta la parte producida en España: a cada producto se le quita su cuota de importación real (Tabla 1).
  Resultado en **empleos-año** (puestos equivalentes a tiempo completo durante un año).
- **Operación (cada año):**
  - **directo:** la plantilla del simulador y el VAB del CPD = ingresos − compras (energía, agua y mantenimiento),
    con las mismas fórmulas que el VAN (`cpd.scoring`);
  - **indirecto:** las compras del CPD (electricidad → producto 24, agua → 25, mantenimiento → 23) pasadas por L.
- **PIB (E41):** VAB directo del CPD sobre el PIB de su provincia (INE, Contabilidad Regional). No hay PIB municipal.

Límites: tipo I (no incluye el efecto del gasto de los salarios, tipo II); coeficientes medios nacionales de 2022
(no provinciales); el efecto indirecto se reparte por toda España, no solo en la provincia.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from cpd import simulator as sim

PRODUCTO_ENERGIA: str = "24"
PRODUCTO_AGUA: str = "25"
PRODUCTO_MANTENIMIENTO: str = "23"
PRODUCTO_CPD: str = "40"


def coeficientes(ramas: pd.DataFrame) -> pd.DataFrame:
    """Coeficientes por producto (índice = código): empleo por millón de € producido (ETC/M€), VAB por € producido y
    cuota interior (1 − importaciones / oferta). Los productos sin producción quedan en 0."""
    r = ramas.set_index("codigo")
    produccion = r["produccion_meur"].where(r["produccion_meur"] > 0)
    oferta = r["oferta_meur"].where(r["oferta_meur"] > 0)
    return pd.DataFrame(
        {
            "empleo_por_meur": (1000 * r["empleo_etc_miles"] / produccion).fillna(0.0),
            "vab_por_eur": (r["vab_meur"] / produccion).fillna(0.0),
            "cuota_interior": (1 - r["importaciones_meur"] / oferta).clip(0, 1).fillna(1.0),
        }
    )


def efecto(demanda_meur: dict[str, float], ramas: pd.DataFrame, leontief: pd.DataFrame) -> dict[str, Any]:
    """Efecto total (directo + indirecto) en España de una demanda final (M€ por código de producto).

    Solo la parte producida en España (demanda × cuota interior) entra en la economía española; la producción
    inducida es x = L · f_interior.

    Returns:
        `demanda_interior_meur`, `produccion_meur`, `vab_meur`, `empleo_etc` y `por_producto` (producción, VAB y empleo
        inducidos por producto, ordenado por empleo).
    """
    c = coeficientes(ramas).reindex(leontief.index).fillna({"empleo_por_meur": 0.0, "vab_por_eur": 0.0, "cuota_interior": 1.0})
    f = pd.Series(0.0, index=leontief.index)
    for codigo, valor in demanda_meur.items():
        if codigo not in f.index:
            raise KeyError(f"Producto {codigo} no está en la tabla input-output")
        f[codigo] += valor
    f_interior = f * c["cuota_interior"]
    x = pd.Series(leontief.to_numpy() @ f_interior.to_numpy(), index=leontief.index)
    por_producto = pd.DataFrame({"produccion_meur": x, "vab_meur": x * c["vab_por_eur"], "empleo_etc": x * c["empleo_por_meur"]})
    return {
        "demanda_interior_meur": float(f_interior.sum()), "produccion_meur": float(x.sum()),
        "vab_meur": float(por_producto["vab_meur"].sum()), "empleo_etc": float(por_producto["empleo_etc"].sum()),
        "por_producto": por_producto.sort_values("empleo_etc", ascending=False),
    }


def operacion_anual_eur(params: sim.CPDParams, precios: dict[str, float], consumo_mwh: float) -> dict[str, float]:
    """Ingresos, compras intermedias y VAB anual del CPD (€), con las fórmulas del simulador (`cpd.scoring`)."""
    agua_m3 = sim.agua_m3_anual(params.potencia_ti_mw, params.factor_carga, params.wue_l_kwh)
    energia = sim.coste_energia_eur(consumo_mwh, params.autoproduccion_mwh, precios["precio_electricidad_eur_mwh"])
    agua = sim.coste_agua_eur(agua_m3, precios["precio_agua_eur_m3"])
    mantenimiento = params.inversion_eur * precios["mantenimiento_pct_inversion"]
    ingresos = sim.ingresos_anuales_eur(params.potencia_ti_mw, precios["precio_venta_eur_kw_mes"], precios["ocupacion"])
    ingresos += energia * precios.get("repercusion_energia_pct", 0.0)
    compras = energia + agua + mantenimiento
    return {"ingresos": ingresos, "energia": energia, "agua": agua, "mantenimiento": mantenimiento, "compras": compras, "vab": ingresos - compras}


def impacto(
    params: sim.CPDParams,
    precios: dict[str, float],
    reparto_capex: dict[str, float],
    consumo_mwh: float,
    ramas: pd.DataFrame,
    leontief: pd.DataFrame,
) -> dict[str, Any]:
    """Empleo, producción y VAB generados por el CPD de referencia en la construcción y en un año de operación.

    Args:
        reparto_capex: fracción del CAPEX por código de producto (debe sumar 1).
        consumo_mwh: consumo eléctrico anual del CPD (MWh).

    Returns:
        `construccion` (efecto de la inversión), `operacion` (directo + indirecto), `operacion_eur` (cuentas del CPD) y
        `multiplicador_empleo_operacion` (empleo total / directo).
    """
    if abs(sum(reparto_capex.values()) - 1) > 1e-6:
        raise ValueError("El reparto del CAPEX por productos debe sumar 1")
    construccion = efecto({k: v * params.inversion_eur / 1e6 for k, v in reparto_capex.items()}, ramas, leontief)
    cuentas = operacion_anual_eur(params, precios, consumo_mwh)
    compras = {PRODUCTO_ENERGIA: cuentas["energia"] / 1e6, PRODUCTO_AGUA: cuentas["agua"] / 1e6, PRODUCTO_MANTENIMIENTO: cuentas["mantenimiento"] / 1e6}
    indirecto = efecto(compras, ramas, leontief)
    directo = {"empleo_etc": float(params.personal), "vab_meur": cuentas["vab"] / 1e6, "produccion_meur": cuentas["ingresos"] / 1e6}
    operacion = {
        "directo": directo, "indirecto": indirecto,
        "empleo_total": directo["empleo_etc"] + indirecto["empleo_etc"], "vab_total_meur": directo["vab_meur"] + indirecto["vab_meur"],
    }
    return {
        "construccion": construccion, "operacion": operacion, "operacion_eur": cuentas,
        "multiplicador_empleo_operacion": operacion["empleo_total"] / directo["empleo_etc"] if directo["empleo_etc"] else np.nan,
    }


def por_provincia(vab_directo_meur: float, empleo_directo: float, pib: pd.DataFrame, paro: pd.Series) -> pd.DataFrame:
    """Peso del CPD en cada provincia: VAB directo sobre el PIB provincial (último año con las 52) y empleo directo sobre
    el paro registrado (último mes). El empleo indirecto y el de la construcción no se comparan con la provincia: se
    reparten por toda España (proveedores) y saldría un peso local exagerado.

    Args:
        pib: `pib_provincia.csv` (codigo_provincia, anio, pib_miles_eur).
        paro: paro registrado por provincia (personas).

    Returns:
        codigo_provincia, anio_pib, pib_meur, pct_pib, paro_registrado, pct_paro_directo.
    """
    completos = pib.groupby("anio")["codigo_provincia"].nunique()
    anio = int(completos[completos >= 52].index.max())
    ultimo = pib[pib["anio"] == anio].set_index("codigo_provincia")["pib_miles_eur"] / 1e3
    tabla = pd.DataFrame({"pib_meur": ultimo, "paro_registrado": paro}).dropna(subset=["pib_meur"])
    tabla["anio_pib"] = anio
    tabla["pct_pib"] = 100 * vab_directo_meur / tabla["pib_meur"]
    tabla["pct_paro_directo"] = 100 * empleo_directo / tabla["paro_registrado"]
    return tabla.rename_axis("codigo_provincia").reset_index()
