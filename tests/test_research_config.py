"""Testes isolados de ``configs/research.yaml``."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from modules.research.config.loader import (
    ConfigurationError,
    load_research_configuration,
)


def test_load_research_configuration(project_root: Path) -> None:
    configuration = load_research_configuration(project_root=project_root)
    assert configuration.schema_version == "2.0"
    assert configuration.horizons == (1, 5, 21)
    assert configuration.return_mode == "cumulative"
    assert configuration.iti_predictors == ("iti_liquido", "iti_risco")
    assert configuration.abs_return_predictors == ("iti_risco",)
    assert configuration.inference.enabled is True
    assert configuration.company_to_ticker["Sabesp"] == "SBSP3.SA"


def test_load_research_configuration_rejects_invalid_horizon(
    project_root: Path,
    tmp_path: Path,
) -> None:
    invalid_yaml = tmp_path / "research.yaml"
    invalid_yaml.write_text(
        """
schema_version: "2.0"
defaults:
  horizons: [0]
  iti_column: iti_liquido
  return_column: log_return
experiment_run:
  run_id: null
  output_root: outputs
market:
  config_path: configs/market.yaml
mapping:
  company_to_ticker: {}
validation:
  baselines: [b0]
  metrics: [pearson]
  min_overlap_days: 1
paths:
  output_root: outputs
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="horizons"):
        load_research_configuration(
            project_root=project_root,
            config_path=invalid_yaml,
        )


def test_load_research_configuration_rejects_invalid_iti_predictor(
    project_root: Path,
    tmp_path: Path,
) -> None:
    invalid_yaml = tmp_path / "research.yaml"
    invalid_yaml.write_text(
        """
schema_version: "2.0"
defaults:
  horizons: [1]
  iti_predictors: [invalid_column]
  return_column: log_return
experiment_run:
  run_id: null
  output_root: outputs
market:
  config_path: configs/market.yaml
mapping:
  company_to_ticker: {}
validation:
  baselines: [b0]
  metrics: [pearson]
  min_overlap_days: 1
paths:
  output_root: outputs
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="iti_predictors"):
        load_research_configuration(
            project_root=project_root,
            config_path=invalid_yaml,
        )
