"""Métricas estatísticas para validação incremental."""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score


MetricFunction = Callable[[pd.Series, pd.Series], float | None]


def _clean_pair(
    predictor: pd.Series,
    target: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    aligned = pd.concat(
        [predictor.astype(float), target.astype(float)],
        axis=1,
        keys=["predictor", "target"],
    ).dropna()
    if aligned.empty:
        return aligned["predictor"], aligned["target"]
    return aligned["predictor"], aligned["target"]


def pearson_metric(predictor: pd.Series, target: pd.Series) -> float | None:
    x, y = _clean_pair(predictor, target)
    if len(x) < 2:
        return None
    if x.std(ddof=0) == 0 or y.std(ddof=0) == 0:
        return None
    return float(x.corr(y, method="pearson"))


def spearman_metric(predictor: pd.Series, target: pd.Series) -> float | None:
    x, y = _clean_pair(predictor, target)
    if len(x) < 2:
        return None
    if x.nunique() <= 1 or y.nunique() <= 1:
        return None
    return float(x.corr(y, method="spearman"))


def r2_metric(predictor: pd.Series, target: pd.Series) -> float | None:
    x, y = _clean_pair(predictor, target)
    if len(x) < 2:
        return None
    if x.std(ddof=0) == 0:
        return None
    return float(r2_score(y, x))


def mse_metric(predictor: pd.Series, target: pd.Series) -> float | None:
    x, y = _clean_pair(predictor, target)
    if len(x) < 1:
        return None
    return float(mean_squared_error(y, x))


METRIC_FUNCTIONS: dict[str, MetricFunction] = {
    "pearson": pearson_metric,
    "spearman": spearman_metric,
    "r2": r2_metric,
    "mse": mse_metric,
}


def compute_metric(
    metric_name: str,
    predictor: pd.Series,
    target: pd.Series,
) -> float | None:
    function = METRIC_FUNCTIONS.get(metric_name.lower())
    if function is None:
        raise KeyError(f"Métrica desconhecida: {metric_name}")
    value = function(predictor, target)
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


__all__ = [
    "METRIC_FUNCTIONS",
    "compute_metric",
    "mse_metric",
    "pearson_metric",
    "r2_metric",
    "spearman_metric",
]
