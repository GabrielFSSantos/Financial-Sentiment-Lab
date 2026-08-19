"""Inferência estatística: bootstrap em bloco e intervalos de confiança."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from modules.research.config.loader import InferenceConfiguration


MetricFunction = Callable[[np.ndarray, np.ndarray], float | None]


@dataclass(frozen=True)
class MetricInferenceResult:
    value: float | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    n: int
    n_bootstrap: int

    def to_dict(self) -> dict[str, float | int | None]:
        return {
            "value": self.value,
            "p_value": self.p_value,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "n": self.n,
            "n_bootstrap": self.n_bootstrap,
        }


def _clean_arrays(
    predictor: np.ndarray,
    target: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    mask = np.isfinite(predictor) & np.isfinite(target)
    x = predictor[mask]
    y = target[mask]
    if len(x) < 2:
        return None
    return x, y


def _clean_arrays_joint(
    iti_predictor: np.ndarray,
    baseline_predictor: np.ndarray,
    target: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    mask = (
        np.isfinite(iti_predictor)
        & np.isfinite(baseline_predictor)
        & np.isfinite(target)
    )
    x_iti = iti_predictor[mask]
    x_base = baseline_predictor[mask]
    y = target[mask]
    if len(y) < 2:
        return None
    return x_iti, x_base, y


def _block_bootstrap_indices(
    length: int,
    *,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if length <= 0:
        return np.array([], dtype=int)

    indices: list[int] = []
    while len(indices) < length:
        start = int(rng.integers(0, max(length - block_size + 1, 1)))
        block = list(range(start, min(start + block_size, length)))
        indices.extend(block)

    return np.array(indices[:length], dtype=int)


def _percentile_ci(
    samples: np.ndarray,
    *,
    ci_level: float,
) -> tuple[float, float]:
    alpha = 1.0 - ci_level
    low = float(np.percentile(samples, 100.0 * alpha / 2.0))
    high = float(np.percentile(samples, 100.0 * (1.0 - alpha / 2.0)))
    return low, high


def _bootstrap_p_value_two_sided(
    samples: np.ndarray,
    *,
    observed: float,
) -> float:
    if samples.size == 0:
        return 1.0
    opposite = np.sum(samples <= 0.0) if observed >= 0 else np.sum(samples >= 0.0)
    return float(min(1.0, 2.0 * opposite / samples.size))


def compute_metric_inference(
    metric_name: str,
    predictor: np.ndarray,
    target: np.ndarray,
    *,
    metric_fn: MetricFunction,
    inference: InferenceConfiguration,
    parametric_p_value: float | None = None,
) -> MetricInferenceResult:
    """Calcula valor pontual, IC bootstrap em bloco e p-value."""

    cleaned = _clean_arrays(predictor, target)
    if cleaned is None:
        return MetricInferenceResult(
            value=None,
            p_value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            n_bootstrap=0,
        )

    x, y = cleaned
    value = metric_fn(x, y)
    if value is None or not inference.enabled:
        return MetricInferenceResult(
            value=value,
            p_value=parametric_p_value,
            ci_low=None,
            ci_high=None,
            n=int(len(x)),
            n_bootstrap=0,
        )

    rng = np.random.default_rng(inference.random_seed)
    bootstrap_values: list[float] = []

    for _ in range(inference.n_bootstrap):
        indices = _block_bootstrap_indices(
            len(x),
            block_size=inference.block_size,
            rng=rng,
        )
        sample_value = metric_fn(x[indices], y[indices])
        if sample_value is not None and np.isfinite(sample_value):
            bootstrap_values.append(float(sample_value))

    if not bootstrap_values:
        return MetricInferenceResult(
            value=value,
            p_value=parametric_p_value,
            ci_low=None,
            ci_high=None,
            n=int(len(x)),
            n_bootstrap=0,
        )

    samples = np.array(bootstrap_values, dtype=float)
    ci_low, ci_high = _percentile_ci(samples, ci_level=inference.ci_level)
    bootstrap_p = _bootstrap_p_value_two_sided(samples, observed=float(value))
    p_value = bootstrap_p if parametric_p_value is None else parametric_p_value

    return MetricInferenceResult(
        value=float(value),
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
        n=int(len(x)),
        n_bootstrap=len(bootstrap_values),
    )


def compute_delta_inference(
    metric_name: str,
    iti_predictor: np.ndarray,
    baseline_predictor: np.ndarray,
    target: np.ndarray,
    *,
    metric_fn: MetricFunction,
    inference: InferenceConfiguration,
) -> MetricInferenceResult:
    """Bootstrap do delta ITI − baseline (MSE: baseline − ITI)."""

    cleaned = _clean_arrays_joint(iti_predictor, baseline_predictor, target)
    if cleaned is None:
        return MetricInferenceResult(
            value=None,
            p_value=None,
            ci_low=None,
            ci_high=None,
            n=0,
            n_bootstrap=0,
        )

    x_iti, x_base, y = cleaned
    n = len(y)

    iti_value = metric_fn(x_iti, y)
    baseline_value = metric_fn(x_base, y)
    if iti_value is None or baseline_value is None:
        return MetricInferenceResult(
            value=None,
            p_value=None,
            ci_low=None,
            ci_high=None,
            n=n,
            n_bootstrap=0,
        )

    if metric_name == "mse":
        observed = float(baseline_value) - float(iti_value)
    else:
        observed = float(iti_value) - float(baseline_value)

    if not inference.enabled:
        return MetricInferenceResult(
            value=observed,
            p_value=None,
            ci_low=None,
            ci_high=None,
            n=n,
            n_bootstrap=0,
        )

    rng = np.random.default_rng(inference.random_seed + 17)
    bootstrap_deltas: list[float] = []

    for _ in range(inference.n_bootstrap):
        indices = _block_bootstrap_indices(
            n,
            block_size=inference.block_size,
            rng=rng,
        )
        sample_iti = metric_fn(x_iti[indices], y[indices])
        sample_base = metric_fn(x_base[indices], y[indices])
        if sample_iti is None or sample_base is None:
            continue
        if metric_name == "mse":
            bootstrap_deltas.append(float(sample_base) - float(sample_iti))
        else:
            bootstrap_deltas.append(float(sample_iti) - float(sample_base))

    if not bootstrap_deltas:
        return MetricInferenceResult(
            value=observed,
            p_value=None,
            ci_low=None,
            ci_high=None,
            n=n,
            n_bootstrap=0,
        )

    samples = np.array(bootstrap_deltas, dtype=float)
    ci_low, ci_high = _percentile_ci(samples, ci_level=inference.ci_level)
    if metric_name == "mse":
        p_value = float(np.mean(samples <= 0.0))
    else:
        p_value = float(np.mean(samples <= 0.0))

    return MetricInferenceResult(
        value=observed,
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
        n=n,
        n_bootstrap=len(bootstrap_deltas),
    )


def is_significant_favorable_delta(
    *,
    metric_name: str,
    delta: float,
    ci_low: float | None,
    ci_high: float | None,
    p_value: float | None,
    alpha: float = 0.05,
) -> bool:
    """Delta favorável ao ITI com IC que não cruza zero ou p < alpha."""

    if metric_name == "mse":
        favorable = delta > 0
        crosses_zero = (
            ci_low is not None
            and ci_high is not None
            and ci_low <= 0 <= ci_high
        )
    else:
        favorable = delta > 0
        crosses_zero = (
            ci_low is not None
            and ci_high is not None
            and ci_low <= 0 <= ci_high
        )

    if not favorable:
        return False
    if p_value is not None and p_value < alpha:
        return True
    if ci_low is not None and ci_high is not None and not crosses_zero:
        return True
    return False


__all__ = [
    "MetricInferenceResult",
    "compute_delta_inference",
    "compute_metric_inference",
    "is_significant_favorable_delta",
]
