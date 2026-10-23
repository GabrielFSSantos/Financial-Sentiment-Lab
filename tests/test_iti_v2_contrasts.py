"""Contrastes ITI-v2 (Δ pareado + Holm secundário)."""

import numpy as np
import pandas as pd

from modules.experiment.campaign.iti_v2_contrasts import (
    ContrastSpec,
    apply_holm_secondary,
    run_delta_contrast,
)
from modules.research.config.analysis_plan import AnalysisPlan


def _tiny_plan() -> AnalysisPlan:
    return AnalysisPlan(
        schema_version="iti_v2_analysis_1",
        primary_metric="spearman",
        primary_horizon_weeks=1,
        horizons_weeks=(1,),
        bootstrap_replicates=200,
        block_length_weeks=2,
        block_sensitivity_weeks=(2,),
        seed=42,
        alpha=0.05,
        secondary_correction="holm",
        week_anchor="W-FRI",
        returns_before_join=True,
        constant_series_policy="undefined_with_reason",
        nan_as_zero_financial="forbidden",
    )


def test_delta_contrast_runs_on_synthetic_panel() -> None:
    rng = np.random.default_rng(0)
    n = 40
    soft = rng.normal(size=n)
    iti = soft + rng.normal(scale=0.1, size=n)
    ret = rng.normal(size=n)
    panel = pd.DataFrame(
        {
            "soft_input": soft,
            "iti_v2_h7": iti,
            "future_log_return_1": ret,
        }
    )
    spec = ContrastSpec(
        id="TEST",
        candidate_column="iti_v2_h7",
        baseline_column="soft_input",
        metric="spearman",
        horizon_weeks=1,
    )
    row = run_delta_contrast(panel, spec, plan=_tiny_plan(), n_bootstrap=100)
    assert row["status"] == "ok"
    assert row["n"] == n
    assert row["delta"] is not None


def test_holm_secondary_marks_significance() -> None:
    rows = [
        {"p_value": 0.001},
        {"p_value": 0.5},
    ]
    adjusted = apply_holm_secondary(rows, alpha=0.05)
    assert adjusted[0]["significant_holm"] is True
    assert adjusted[1]["significant_holm"] is False
