"""Testes de check de pré-requisitos do research."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from modules.research.config.loader import load_research_configuration
from modules.research.pipeline.runner import check_research_inputs


def test_check_research_inputs_reports_invalid_market_csv(
    project_root: Path,
    tmp_path: Path,
) -> None:
    market_yaml = tmp_path / "market.yaml"
    bad_csv = tmp_path / "bad_prices.csv"
    bad_csv.write_text(
        "date,ticker,close,close.1\n"
        "2024-01-01,AAA,not-a-number,\n",
        encoding="utf-8",
    )
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
  local_path: {bad_csv}
""",
        encoding="utf-8",
    )

    configuration = replace(
        load_research_configuration(project_root=project_root),
        run_id="test_run",
        experiment_output_root=project_root / "tests/fixtures/research/outputs",
        market_config_path=market_yaml,
    )

    errors, warnings = check_research_inputs(configuration)
    assert errors
    assert any("inválido" in item.lower() for item in errors)


def test_check_research_inputs_reports_market_coverage(
    project_root: Path,
    tmp_path: Path,
) -> None:
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
        load_research_configuration(project_root=project_root),
        run_id="test_run",
        experiment_output_root=project_root / "tests/fixtures/research/outputs",
        market_config_path=market_yaml,
    )

    errors, warnings = check_research_inputs(configuration)
    assert not errors
    assert any("Mercado:" in warning for warning in warnings)
