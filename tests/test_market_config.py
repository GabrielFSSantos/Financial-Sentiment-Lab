"""Testes isolados de ``configs/market.yaml``."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.market.config.loader import (
    ConfigurationError,
    load_market_configuration,
)


def test_load_market_configuration(project_root: Path) -> None:
    configuration = load_market_configuration(project_root=project_root)
    assert configuration.schema_version == "2.0"
    assert configuration.enabled is True
    assert configuration.local_path.name == "prices.csv"
    assert configuration.source is not None
    assert "SBSP3.SA" in configuration.source.tickers
    assert "CSMG3.SA" in configuration.source.tickers


def test_load_market_configuration_rejects_invalid_provider(
    project_root: Path,
    tmp_path: Path,
) -> None:
    invalid_yaml = tmp_path / "market.yaml"
    invalid_yaml.write_text(
        """
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
  local_path: data/market/prices.csv
  source:
    provider: unknown
    tickers: [AAA]
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="provider"):
        load_market_configuration(
            project_root=project_root,
            config_path=invalid_yaml,
        )
