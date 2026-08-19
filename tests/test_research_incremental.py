"""Testes de validação incremental."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from modules.research.config.loader import load_research_configuration
from modules.research.validation.incremental import run_incremental_validation


def test_incremental_prefers_iti_on_constructed_panel(project_root) -> None:
    configuration = replace(
        load_research_configuration(project_root=project_root),
        horizons=(1,),
        metrics=("pearson",),
        baselines=("b0",),
    )

    panel = pd.DataFrame(
        {
            "model_key": ["m"] * 5,
            "dataset_key": ["d"] * 5,
            "iti_liquido": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b0_news_count": [5.0, 1.0, 4.0, 2.0, 3.0],
            "future_log_return_1": [2.0, 4.0, 6.0, 8.0, 10.0],
        }
    )

    result = run_incremental_validation(panel, configuration)
    assert not result.empty
    iti_value = result.loc[
        result["predictor"] == "iti", "value"
    ].iloc[0]
    baseline_value = result.loc[
        result["predictor"] == "b0", "value"
    ].iloc[0]
    assert iti_value > baseline_value
