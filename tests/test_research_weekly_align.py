"""Testes de alinhamento semanal do research."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
from modules.research.config.loader import load_research_configuration
from modules.research.io.experiment import list_index_combinations
from modules.research.io.weekly_align import (
    _collapse_weekly_panel,
    _week_end_key,
    align_weekly_combination,
)


@pytest.mark.contract
def test_week_end_key_uses_w_fri() -> None:
    series = pd.Series(["2024-01-03", "2024-01-05"])
    ends = _week_end_key(series)
    assert ends.dt.dayofweek.iloc[0] == 4  # Friday


@pytest.mark.contract
def test_collapse_weekly_panel_keeps_last_observation_per_week() -> None:
    frame = pd.DataFrame(
        {
            "company": ["Sabesp", "Sabesp"],
            "sector": ["Water", "Water"],
            "period_end": ["2024-01-03", "2024-01-05"],
            "iti_liquido": [0.1, 0.9],
        }
    )
    collapsed = _collapse_weekly_panel(frame, date_source="period_end")
    assert len(collapsed) == 1
    assert collapsed["iti_liquido"].iloc[0] == pytest.approx(0.9)


def test_weekly_align_sabesp_r0(project_root: Path) -> None:
    run_dir = project_root / "outputs" / "sabesp_r0_baseline"
    if not run_dir.is_dir():
        return

    configuration = load_research_configuration(
        project_root=project_root,
        config_path=project_root / "configs/campaigns/sabesp_2026/research_weekly.yaml",
        run_id="sabesp_r0_baseline",
    )
    combinations = list_index_combinations(configuration)
    market = load_market_prices(
        load_market_configuration(project_root=project_root)
    )

    panel, dropped, overlap = align_weekly_combination(
        combinations[0],
        configuration,
        market_prices=market,
        company_to_ticker=configuration.company_to_ticker,
    )

    assert overlap >= 8
    assert panel["iti_liquido"].notna().any()
    assert "future_log_return_2" in panel.columns
    assert dropped == ()
