"""Testes de comparação entre runs."""

from __future__ import annotations

import pyarrow as pa

from modules.dashboard.services.catalog import get_resolved_config
from modules.dashboard.services.compare import compare_runs, delta_win_rate
from modules.dashboard.services.runs import diff_configs, param_diffs_to_dataframe


def test_diff_configs_alpha() -> None:
    config_a = get_resolved_config("sabesp_r0_baseline") or {}
    config_b = get_resolved_config("sabesp_r1_alpha070") or {}
    if not config_a or not config_b:
        return
    diffs = diff_configs(config_a, config_b)
    keys = {row["parametro"] for row in diffs}
    assert "alpha" in keys


def test_param_diffs_arrow_compatible() -> None:
    rows = [
        {"parametro": "alpha", "run_a": 0.85, "run_b": 0.7},
        {"parametro": "horizon_mode", "run_a": "ewma_alpha", "run_b": "fixed"},
        {"parametro": "disabled_dimensions", "run_a": [], "run_b": ["u"]},
    ]
    df = param_diffs_to_dataframe(rows)
    pa.Table.from_pandas(df)
    assert df["run_a"].dtype == object
    assert all(isinstance(value, str) for value in df["run_a"])


def test_compare_runs_metrics() -> None:
    result = compare_runs(["sabesp_r0_baseline", "sabesp_r1_alpha070"])
    assert "metrics" in result
    assert len(result["metrics"]) == 2


def test_delta_win_rate() -> None:
    delta = delta_win_rate("sabesp_r0_baseline", "sabesp_r1_alpha070")
    if delta is not None:
        assert delta > 0
