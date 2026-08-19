"""Testes de validação incremental."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from modules.research.config.loader import load_research_configuration
from modules.research.validation.incremental import run_incremental_validation


def _fast_configuration(project_root):
    configuration = load_research_configuration(project_root=project_root)
    return replace(
        configuration,
        horizons=(1,),
        metrics=("pearson",),
        baselines=("b0",),
        inference=replace(
            configuration.inference,
            n_bootstrap=30,
            block_size=2,
        ),
    )


def test_incremental_prefers_iti_liquido_on_constructed_panel(project_root) -> None:
    configuration = _fast_configuration(project_root)

    panel = pd.DataFrame(
        {
            "model_key": ["m"] * 5,
            "dataset_key": ["d"] * 5,
            "iti_liquido": [1.0, 2.0, 3.0, 4.0, 5.0],
            "iti_risco": [0.1, 0.2, 0.3, 0.4, 0.5],
            "b0_news_count": [5.0, 1.0, 4.0, 2.0, 3.0],
            "future_log_return_1": [2.0, 4.0, 6.0, 8.0, 10.0],
        }
    )

    result = run_incremental_validation(panel, configuration)
    assert not result.empty
    assert "p_value" in result.columns
    assert "ci_low" in result.columns

    iti_value = result.loc[
        result["predictor"] == "iti_liquido", "value"
    ].iloc[0]
    baseline_value = result.loc[
        result["predictor"] == "b0", "value"
    ].iloc[0]
    assert iti_value > baseline_value

    predictors = set(result["predictor"])
    assert "iti_liquido" in predictors
    assert "iti_risco" in predictors


def test_incremental_includes_both_iti_predictors(project_root) -> None:
    configuration = replace(
        _fast_configuration(project_root),
        inference=replace(
            load_research_configuration(project_root=project_root).inference,
            enabled=False,
        ),
    )

    panel = pd.DataFrame(
        {
            "model_key": ["m"] * 6,
            "dataset_key": ["d"] * 6,
            "iti_liquido": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "iti_risco": [0.5, 0.4, 0.3, 0.2, 0.1, 0.0],
            "b0_news_count": [1, 2, 3, 4, 5, 6],
            "future_log_return_1": [0.01, -0.01, 0.02, -0.02, 0.03, -0.03],
        }
    )

    result = run_incremental_validation(panel, configuration)
    assert set(result["predictor"]) >= {"iti_liquido", "iti_risco", "b0"}

    risk_row = result.loc[result["predictor"] == "iti_risco"].iloc[0]
    assert risk_row["target_mode"] == "abs"
