"""Métricas estatísticas para validação incremental."""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_squared_error, r2_score

from modules.research.config.loader import InferenceConfiguration, ResearchConfiguration
from modules.research.validation.inference import (
    MetricInferenceResult,
    compute_metric_inference,
)


MetricFunction = Callable[[pd.Series, pd.Series], float | None]
NumpyMetricFunction = Callable[[np.ndarray, np.ndarray], float | None]


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


def pearson_numpy(predictor: np.ndarray, target: np.ndarray) -> float | None:
    mask = np.isfinite(predictor) & np.isfinite(target)
    x = predictor[mask]
    y = target[mask]
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def spearman_numpy(predictor: np.ndarray, target: np.ndarray) -> float | None:
    mask = np.isfinite(predictor) & np.isfinite(target)
    x = predictor[mask]
    y = target[mask]
    if len(x) < 2:
        return None
    x_rank = pd.Series(x).rank(method="average").to_numpy()
    y_rank = pd.Series(y).rank(method="average").to_numpy()
    if np.std(x_rank) == 0 or np.std(y_rank) == 0:
        return None
    return float(np.corrcoef(x_rank, y_rank)[0, 1])


def r2_numpy(predictor: np.ndarray, target: np.ndarray) -> float | None:
    mask = np.isfinite(predictor) & np.isfinite(target)
    x = predictor[mask]
    y = target[mask]
    if len(x) < 2 or np.std(x) == 0:
        return None
    return float(r2_score(y, x))


def mse_numpy(predictor: np.ndarray, target: np.ndarray) -> float | None:
    mask = np.isfinite(predictor) & np.isfinite(target)
    x = predictor[mask]
    y = target[mask]
    if len(x) < 1:
        return None
    return float(mean_squared_error(y, x))


METRIC_FUNCTIONS: dict[str, MetricFunction] = {
    "pearson": pearson_metric,
    "spearman": spearman_metric,
    "r2": r2_metric,
    "mse": mse_metric,
}

NUMPY_METRIC_FUNCTIONS: dict[str, NumpyMetricFunction] = {
    "pearson": pearson_numpy,
    "spearman": spearman_numpy,
    "r2": r2_numpy,
    "mse": mse_numpy,
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


def _parametric_p_value(
    metric_name: str,
    predictor: np.ndarray,
    target: np.ndarray,
) -> float | None:
    mask = np.isfinite(predictor) & np.isfinite(target)
    x = predictor[mask]
    y = target[mask]
    if len(x) < 3:
        return None
    if metric_name == "pearson":
        if np.std(x) == 0 or np.std(y) == 0:
            return None
        _, p_value = pearsonr(x, y)
        return float(p_value)
    if metric_name == "spearman":
        if len(np.unique(x)) <= 1 or len(np.unique(y)) <= 1:
            return None
        _, p_value = spearmanr(x, y)
        return float(p_value)
    return None


def compute_metric_with_inference(
    metric_name: str,
    predictor: pd.Series,
    target: pd.Series,
    *,
    inference: InferenceConfiguration,
) -> MetricInferenceResult:
    """Calcula métrica pontual com inferência bootstrap em bloco."""

    metric_key = metric_name.lower()
    numpy_fn = NUMPY_METRIC_FUNCTIONS.get(metric_key)
    if numpy_fn is None:
        raise KeyError(f"Métrica desconhecida: {metric_name}")

    x = predictor.astype(float).to_numpy()
    y = target.astype(float).to_numpy()
    parametric_p = _parametric_p_value(metric_key, x, y)

    return compute_metric_inference(
        metric_key,
        x,
        y,
        metric_fn=numpy_fn,
        inference=inference,
        parametric_p_value=parametric_p,
    )


def resolve_target_series(
    panel: pd.DataFrame,
    *,
    target_column: str,
    predictor_key: str,
    configuration: ResearchConfiguration,
) -> pd.Series:
    target = panel[target_column].astype(float)
    if configuration.uses_abs_target(predictor_key):
        return target.abs()
    return target


__all__ = [
    "METRIC_FUNCTIONS",
    "NUMPY_METRIC_FUNCTIONS",
    "MetricInferenceResult",
    "compute_metric",
    "compute_metric_with_inference",
    "mse_metric",
    "pearson_metric",
    "r2_metric",
    "resolve_target_series",
    "spearman_metric",
]
