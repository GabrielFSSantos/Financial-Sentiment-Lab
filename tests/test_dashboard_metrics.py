"""Testes do catálogo de métricas."""

from __future__ import annotations

from modules.dashboard.metrics.catalog import get_metric, interpret_value


def test_win_rate_bands() -> None:
    assert "fraco" in interpret_value("win_rate", 0.15)
    assert "gate" in interpret_value("win_rate", 0.35).lower()
    assert "promissor" in interpret_value("win_rate", 0.55)


def test_kappa_bands() -> None:
    assert "gate" in interpret_value("kappa", 0.16).lower()
    assert "atendido" in interpret_value("kappa", 0.45).lower()


def test_new_metrics_exist() -> None:
    for key in (
        "kappa",
        "accuracy",
        "delta_win_rate",
        "overlap_weeks",
        "alpha_ewma",
        "significant_wins",
        "exploratory_caveat",
        "runs_count",
    ):
        assert get_metric(key) is not None
