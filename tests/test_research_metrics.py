"""Testes de métricas de research."""

from __future__ import annotations

import pandas as pd

from modules.research.validation.metrics import (
    compute_metric,
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
