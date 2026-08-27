"""Testes de comparação entre runs."""

from __future__ import annotations

from modules.dashboard.services.catalog import get_resolved_config
from modules.dashboard.services.compare import compare_runs, delta_win_rate
from modules.dashboard.services.runs import diff_configs


def test_diff_configs_alpha() -> None:
    config_a = get_resolved_config("sabesp_r0_baseline") or {}
    config_b = get_resolved_config("sabesp_r1_alpha070") or {}
    if not config_a or not config_b:
        return
    diffs = diff_configs(config_a, config_b)
    keys = {row["parametro"] for row in diffs}
    assert "alpha" in keys


def test_compare_runs_metrics() -> None:
    result = compare_runs(["sabesp_r0_baseline", "sabesp_r1_alpha070"])
    assert "metrics" in result
    assert len(result["metrics"]) == 2


def test_delta_win_rate() -> None:
    delta = delta_win_rate("sabesp_r0_baseline", "sabesp_r1_alpha070")
    if delta is not None:
        assert delta > 0
