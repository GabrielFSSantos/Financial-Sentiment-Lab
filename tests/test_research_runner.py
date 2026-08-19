"""Testes do runner de research."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from modules.research.config.loader import load_research_configuration
from modules.research.pipeline.runner import run_research


def test_run_research_generates_summary(
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
        load_research_configuration(project_root=project_root),
        run_id="test_run",
        experiment_output_root=outputs_root,
        research_output_root=tmp_path / "outputs",
        market_config_path=market_yaml,
        min_overlap_days=5,
    )

    summary = run_research(configuration)
    summary_path = (
        tmp_path
        / "outputs"
        / "test_run"
        / "research"
        / "research_summary.json"
    )

    assert summary.run_id == "test_run"
    assert len(summary.combinations) == 1
    assert summary.combinations[0].predictor_stats
    assert summary_path.is_file()
