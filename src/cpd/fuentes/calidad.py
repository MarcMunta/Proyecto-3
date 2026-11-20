"""Controles de calidad de los datos descargados (fase 2 de la metodología; reglas R-1, R-9 y R-10).

Demanda eléctrica por comunidad (REData, `demanda/evolucion`). Problemas comprobados el 17/11/2026 con el endpoint
`balance/balance-electrico`:

- **Julio y agosto de 2026:** REData aún no publica el "Saldo de intercambios" de las comunidades peninsulares y
  su "Demanda en b.c." es solo la generación propia (Madrid: 72.822 + 50.297 = 123.120 MWh, frente a unos
  2.500.000 MWh reales). Son datos provisionales incompletos: se recuperarán cuando REData publique el saldo.
- **Octubre de 2025:** el saldo de intercambios de Asturias (−289.536 MWh), Navarra y el País Vasco cambia de signo
  o se dispara y la demanda cae a la mitad sin causa conocida.

Regla: un valor de demanda imposible no se corrige ni se inventa (R-1); se deja en NaN en el panel y se registra
el valor original y el motivo en `data/curated/calidad_demanda_ccaa.csv` (R-10).
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

# Comunidades con sistema eléctrico no peninsular: Baleares, Canarias, Ceuta y Melilla (código INE de CCAA).
CCAA_EXTRAPENINSULARES: frozenset[str] = frozenset({"04", "05", "18", "19"})

COLUMNAS_REGISTRO: list[str] = ["codigo_ccaa", "ccaa", "mes", "demanda_mwh_original", "cociente_interanual", "motivo"]


def marcar_atipicos_demanda(serie: pd.DataFrame, minimo: float = 0.6, maximo: float = 1.6) -> pd.DataFrame:
    """Marca como atípicos los meses imposibles o fuera de rango de cada comunidad (R-10: decidir y registrar).

    Reglas:
    1. Demanda ≤ 0.
    2. Cociente con el mismo mes del año anterior de la misma comunidad fuera de [`minimo`, `maximo`] (se compara con
       el mismo mes para no marcar la estacionalidad real, p. ej. el verano turístico de Baleares). Si el mes del año
       anterior también es atípico, se compara con el de hace dos años.
    3. Fallo de la fuente: si en un mes son atípicas la mitad o más de las comunidades peninsulares (y al menos 3),
       ese mes se marca en todas las peninsulares.

    El confinamiento de 2020 (cocientes de 0,7-0,9) no se marca con estos umbrales.

    Args:
        serie: una fila por comunidad y mes con `codigo_ccaa`, `mes` (inicio de mes) y `demanda_mwh` (MWh).
        minimo: cociente mínimo admitido frente al mismo mes del año anterior.
        maximo: cociente máximo admitido.

    Returns:
        Copia de la serie (mismo índice) con `cociente_interanual`, `atipico` (bool) y `motivo_atipico`.
        No cambia ningún valor.
    """
    salida = serie.sort_values(["codigo_ccaa", "mes"]).reset_index().copy()
    valor = salida.set_index(["codigo_ccaa", "mes"])["demanda_mwh"]
    negativa = salida["demanda_mwh"] <= 0

    def referencia(atipicos: set[tuple[str, pd.Timestamp]]) -> pd.Series:
        """Demanda del mismo mes del año anterior; si ese mes es atípico, la de hace dos años."""
        refs = []
        for codigo, mes in zip(salida["codigo_ccaa"], salida["mes"]):
            ref = np.nan
            for anios in (1, 2):
                clave = (codigo, mes - pd.DateOffset(years=anios))
                if clave in valor.index and clave not in atipicos:
                    ref = valor[clave]
                    break
            refs.append(ref)
        return pd.Series(refs, index=salida.index, dtype=float)

    # Dos pasadas: la segunda no compara contra meses que la primera ya marcó (evita el efecto eco un año después).
    marcados: set[tuple[str, pd.Timestamp]] = set(zip(salida.loc[negativa, "codigo_ccaa"], salida.loc[negativa, "mes"]))
    for _ in range(2):
        salida["cociente_interanual"] = salida["demanda_mwh"] / referencia(marcados)
        fuera = ((salida["cociente_interanual"] < minimo) | (salida["cociente_interanual"] > maximo)).fillna(False) & ~negativa
        marcados |= set(zip(salida.loc[fuera, "codigo_ccaa"], salida.loc[fuera, "mes"]))
    peninsular = ~salida["codigo_ccaa"].isin(CCAA_EXTRAPENINSULARES)
    individual = negativa | fuera
    proporcion = individual[peninsular].groupby(salida.loc[peninsular, "mes"]).agg(["mean", "sum"])
    meses_fallo = set(proporcion[(proporcion["mean"] >= 0.5) & (proporcion["sum"] >= 3)].index)
    sistemico = peninsular & salida["mes"].isin(meses_fallo)
    salida["atipico"] = individual | sistemico
    salida["motivo_atipico"] = np.select(
        [negativa, fuera, sistemico],
        ["demanda ≤ 0", f"cociente interanual fuera de [{minimo}, {maximo}]", "fallo de la fuente en el mes"],
        default="",
    )
    return salida.set_index("index").rename_axis(serie.index.name)


def depurar_demanda_ccaa(tabla: pd.DataFrame, hoy: dt.date | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deja en NaN la demanda imposible o incompleta de la tabla `ccaa_demanda` y devuelve el registro de lo quitado.

    Además de `marcar_atipicos_demanda`, quita el mes en curso: REData lo publica con los días que lleva y no es
    comparable con un mes completo.

    Args:
        tabla: tabla `ccaa_demanda` de REData (`codigo_ccaa`, `ccaa`, `fecha`, `demanda_mwh` en MWh).
        hoy: fecha de referencia para saber qué mes está en curso (por defecto, hoy).

    Returns:
        (copia de la tabla con `demanda_mwh` = NaN en los meses quitados; registro con `codigo_ccaa`, `ccaa`, `mes`
        (AAAA-MM), `demanda_mwh_original`, `cociente_interanual` y `motivo`).
    """
    if tabla is None or tabla.empty:
        return tabla, pd.DataFrame(columns=COLUMNAS_REGISTRO)
    serie = tabla.assign(
        codigo_ccaa=tabla["codigo_ccaa"].astype(str).str.zfill(2),
        mes=pd.to_datetime(tabla["fecha"]).dt.to_period("M").dt.to_timestamp(),
    ).dropna(subset=["demanda_mwh"])
    mes_en_curso = pd.Timestamp(hoy or dt.date.today()).to_period("M").to_timestamp()
    en_curso = serie[serie["mes"] >= mes_en_curso].assign(atipico=True, motivo_atipico="mes en curso (incompleto)", cociente_interanual=np.nan)
    marcada = pd.concat([marcar_atipicos_demanda(serie[serie["mes"] < mes_en_curso]), en_curso])
    atipicos = marcada[marcada["atipico"]]
    limpia = tabla.copy()
    limpia.loc[atipicos.index, "demanda_mwh"] = np.nan
    registro = pd.DataFrame(
        {
            "codigo_ccaa": atipicos["codigo_ccaa"],
            "ccaa": atipicos["ccaa"] if "ccaa" in atipicos.columns else "",
            "mes": atipicos["mes"].dt.strftime("%Y-%m"),
            "demanda_mwh_original": atipicos["demanda_mwh"],
            "cociente_interanual": atipicos["cociente_interanual"].round(3),
            "motivo": atipicos["motivo_atipico"],
        },
        columns=COLUMNAS_REGISTRO,
    )
    return limpia, registro.sort_values(["mes", "codigo_ccaa"]).reset_index(drop=True)
