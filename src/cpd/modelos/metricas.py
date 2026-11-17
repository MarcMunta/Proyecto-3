"""Métricas de evaluación (fase 8): regresión (distancia al valor real, C3 p.10-11) y clasificación (C3 p.13-19).

Las fórmulas se escriben a mano para que se puedan leer y comprobar en los tests; ROC-AUC y log-loss usan
scikit-learn.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import log_loss, roc_auc_score, roc_curve


def _arrays(real, prevision) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(real, dtype=float)
    p = np.asarray(prevision, dtype=float)
    if y.shape != p.shape:
        raise ValueError(f"Tamaños distintos: {y.shape} y {p.shape}")
    if not len(y):
        raise ValueError("No hay valores que evaluar")
    return y, p


def mae(real, prevision) -> float:
    """Error absoluto medio: media de |real − previsión| (mismas unidades que el dato, p. ej. MWh)."""
    y, p = _arrays(real, prevision)
    return float(np.mean(np.abs(y - p)))


def rmse(real, prevision) -> float:
    """Raíz del error cuadrático medio (mismas unidades que el dato). Penaliza más los errores grandes que el MAE."""
    y, p = _arrays(real, prevision)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mape(real, prevision) -> float:
    """Error porcentual absoluto medio (%): media de |real − previsión| / |real| × 100. Solo sin ceros en `real`."""
    y, p = _arrays(real, prevision)
    if np.any(y == 0):
        raise ValueError("El MAPE no se puede calcular con valores reales iguales a cero")
    return float(np.mean(np.abs((y - p) / y)) * 100)


def acierto_pct(real, prevision) -> float:
    """Acierto de una previsión (%) = 100 × (1 − WAPE), con WAPE = Σ|real − previsión| / Σ|real|.

    Es la definición habitual de «forecast accuracy» (recomendación, no viene de clase). A diferencia de 100 − MAPE,
    no se dispara cuando hay meses con valores muy bajos (p. ej. un precio de la luz de 16 €/MWh), porque pesa cada
    error por el tamaño total de la serie. Puede ser negativo si el error total supera al valor total.
    """
    y, p = _arrays(real, prevision)
    return float(100 * (1 - np.sum(np.abs(y - p)) / np.sum(np.abs(y))))


def metricas_regresion(real, prevision) -> dict[str, float]:
    """MAE, RMSE, MAPE y acierto juntos (claves `mae`, `rmse`, `mape_pct`, `acierto_pct`).

    Si algún valor real es 0 (p. ej. un mes sin generación renovable en Melilla), el MAPE no existe y queda en NaN;
    el acierto (WAPE) sí se puede calcular.
    """
    sin_ceros = bool(np.all(np.asarray(real, dtype=float) != 0))
    return {
        "mae": mae(real, prevision),
        "rmse": rmse(real, prevision),
        "mape_pct": mape(real, prevision) if sin_ceros else float("nan"),
        "acierto_pct": acierto_pct(real, prevision),
    }


# Requisito del proyecto (17/11/2026): todo modelo debe acertar al menos un 85 % (objetivo: 90 %) y ninguno puede
# llegar al 99,9 %: un acierto así indica casi seguro una fuga de información (el modelo «ve» el resultado).
ACIERTO_MINIMO: float = 85.0
ACIERTO_OBJETIVO: float = 90.0
ACIERTO_SOSPECHOSO: float = 99.9


def control_acierto(acierto: float) -> str:
    """Estado de un acierto (%) frente al requisito: `cumple`, `cumple (objetivo 90 %)`, `no cumple (< 85 %)` o
    `sospechoso (≥ 99,9 %)`."""
    if acierto >= ACIERTO_SOSPECHOSO:
        return "sospechoso (≥ 99,9 %)"
    if acierto < ACIERTO_MINIMO:
        return "no cumple (< 85 %)"
    if acierto >= ACIERTO_OBJETIVO:
        return "cumple (objetivo 90 %)"
    return "cumple"


def matriz_confusion(real, prediccion) -> dict[str, int]:
    """Matriz de confusión binaria (1 = tiene CPD): verdaderos/falsos positivos y negativos (C3 p.15-17)."""
    y = np.asarray(real).astype(int)
    p = np.asarray(prediccion).astype(int)
    return {
        "vp": int(np.sum((y == 1) & (p == 1))),
        "fp": int(np.sum((y == 0) & (p == 1))),
        "fn": int(np.sum((y == 1) & (p == 0))),
        "vn": int(np.sum((y == 0) & (p == 0))),
    }


def metricas_clasificacion(real, probabilidad, umbral: float = 0.5) -> dict[str, float]:
    """Métricas de un clasificador con probabilidades (C3 p.13-14, 19).

    Args:
        real: etiquetas 0/1.
        probabilidad: probabilidad estimada de la clase 1, entre 0 y 1.
        umbral: a partir de qué probabilidad se predice la clase 1.

    Returns:
        accuracy, precision, recall (TPR), fpr, f1, roc_auc, log_loss, brier y la matriz de confusión al umbral.
    """
    y = np.asarray(real).astype(int)
    prob = np.clip(np.asarray(probabilidad, dtype=float), 1e-6, 1 - 1e-6)
    pred = (prob >= umbral).astype(int)
    mc = matriz_confusion(y, pred)
    vp, fp, fn, vn = mc["vp"], mc["fp"], mc["fn"], mc["vn"]
    precision = vp / (vp + fp) if vp + fp else 0.0
    recall = vp / (vp + fn) if vp + fn else 0.0
    return {
        "umbral": umbral,
        "accuracy": (vp + vn) / len(y),
        "precision": precision,
        "recall": recall,
        "fpr": fp / (fp + vn) if fp + vn else 0.0,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "roc_auc": float(roc_auc_score(y, prob)) if len(set(y)) == 2 else float("nan"),
        "log_loss": float(log_loss(y, prob, labels=[0, 1])),
        "brier": float(np.mean((prob - y) ** 2)),
        **mc,
    }


def umbral_youden(real, probabilidad) -> float:
    """Umbral que maximiza TPR − FPR (índice de Youden) sobre la curva ROC (C3 p.19)."""
    fpr, tpr, umbrales = roc_curve(np.asarray(real).astype(int), np.asarray(probabilidad, dtype=float))
    validos = np.isfinite(umbrales)
    indice = int(np.argmax((tpr - fpr)[validos]))
    return float(umbrales[validos][indice])
