"""Testes de alinhamento ITI × mercado."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
from modules.research.config.loader import load_research_configuration
from modules.research.io.align import AlignmentError, align_combination
from modules.research.io.experiment import list_index_combinations


def _research_configuration(
    project_root: Path,
    *,
    outputs_root: Path,
    market_config_path: Path,
) -> object:
    configuration = load_research_configuration(project_root=project_root)
    return replace(
        configuration,
        run_id="test_run",
        experiment_output_root=outputs_root,
        research_output_root=outputs_root,
        market_config_path=market_config_path,
        min_overlap_days=5,
    )


def test_align_combination_adds_b3_and_future_returns(
    project_root: Path,
    tmp_path: Path,
) -> None:
    outputs_root = project_root / "tests" / "fixtures" / "research" / "outputs"
    market_yaml = tmp_path / "market.yaml"
    market_yaml.write_text(
        f"""
schema_version: "2.0"
defaults:
  format: csv
  reader:
    encoding: utf-8
    delimiter: ","
  columns:
    date: date
    ticker: ticker
    close: close
  returns:
    compute: [simple_return, log_return]
market:
  enabled: true
  local_path: {project_root / "tests/fixtures/market/prices.csv"}
""",
        encoding="utf-8",
    )

    configuration = _research_configuration(
        project_root,
        outputs_root=outputs_root,
        market_config_path=market_yaml,
    )
    combination = list_index_combinations(configuration)[0]
    market_config = load_market_configuration(config_path=market_yaml)
    market_prices = load_market_prices(market_config)

    result = align_combination(
        combination,
        configuration,
        market_prices=market_prices,
    )

    assert "b3_daily_impact_no_memory" in result.panel.columns
    assert "future_log_return_1" in result.panel.columns
    assert result.overlap_days >= 5
    assert result.panel["ticker"].eq("SBSP3.SA").all()


def test_align_combination_fails_on_insufficient_overlap(
    project_root: Path,
    tmp_path: Path,
) -> None:
    outputs_root = project_root / "tests" / "fixtures" / "research" / "outputs"
    market_yaml = tmp_path / "market.yaml"
    market_yaml.write_text(
        f"""
schema_version: "2.0"
defaults:
  format: csv
  reader:
    encoding: utf-8
    delimiter: ","
  columns:
    date: date
    ticker: ticker
    close: close
  returns:
    compute: [simple_return, log_return]
market:
  enabled: true
  local_path: {project_root / "tests/fixtures/market/prices.csv"}
""",
        encoding="utf-8",
    )

    configuration = replace(
        _research_configuration(
            project_root,
            outputs_root=outputs_root,
            market_config_path=market_yaml,
        ),
        min_overlap_days=999,
    )
    combination = list_index_combinations(configuration)[0]
    market_config = load_market_configuration(config_path=market_yaml)
    market_prices = load_market_prices(market_config)

    with pytest.raises(AlignmentError, match="Overlap insuficiente"):
        align_combination(
            combination,
            configuration,
            market_prices=market_prices,
        )
