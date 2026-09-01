"""Testes de alinhamento semanal do research."""

from __future__ import annotations

from pathlib import Path

from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
from modules.research.config.loader import load_research_configuration
from modules.research.io.experiment import list_index_combinations
from modules.research.io.weekly_align import align_weekly_combination


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
