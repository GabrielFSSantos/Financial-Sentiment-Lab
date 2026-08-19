"""Testes de métricas de research."""

from __future__ import annotations

import pandas as pd

from modules.research.config.loader import InferenceConfiguration
from modules.research.validation.metrics import (
    compute_metric,
    compute_metric_with_inference,
    pearson_metric,
)


def test_pearson_metric_known_value() -> None:
    predictor = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    target = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    value = pearson_metric(predictor, target)
    assert value is not None
    assert abs(value - 1.0) < 1e-9


def test_compute_metric_returns_none_for_constant_series() -> None:
    predictor = pd.Series([1.0, 1.0, 1.0])
    target = pd.Series([1.0, 2.0, 3.0])
    assert compute_metric("pearson", predictor, target) is None


def test_compute_metric_with_inference_perfect_correlation() -> None:
    predictor = pd.Series([float(index) for index in range(20)])
    target = pd.Series([float(index * 2) for index in range(20)])
    inference = InferenceConfiguration(
        enabled=True,
        n_bootstrap=50,
        block_size=3,
        ci_level=0.95,
        random_seed=7,
    )

    result = compute_metric_with_inference(
        "pearson",
        predictor,
        target,
        inference=inference,
    )

    assert result.value is not None
    assert abs(result.value - 1.0) < 1e-9
    assert result.p_value is not None
    assert result.p_value < 0.05
    assert result.ci_low is not None
    assert result.ci_high is not None
    assert result.ci_low > 0


def test_compute_metric_with_inference_small_sample_returns_none() -> None:
    predictor = pd.Series([1.0])
    target = pd.Series([2.0])
    inference = InferenceConfiguration(
        enabled=True,
        n_bootstrap=10,
        block_size=1,
        ci_level=0.95,
        random_seed=1,
    )

    result = compute_metric_with_inference(
        "pearson",
        predictor,
        target,
        inference=inference,
    )
    assert result.value is None
