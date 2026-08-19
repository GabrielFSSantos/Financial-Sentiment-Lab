"""Testes de fetch de mercado (``modules.market.assets``)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from modules.market.assets import fetch_market_assets
from modules.market.config.loader import load_market_configuration


def test_fetch_market_assets_skips_existing_file(
    project_root: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "prices.csv"
    target.write_text("date,ticker,close\n2024-01-01,AAA,1\n", encoding="utf-8")
    configuration = replace(
        load_market_configuration(project_root=project_root),
        local_path=target,
    )

    summary = fetch_market_assets(configuration)
    assert summary.failed_count == 0
    assert summary.reports[0].status == "skipped"


@patch("modules.market.assets.yf")
def test_fetch_market_assets_downloads_yfinance(
    mock_yf,
    project_root: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "prices.csv"
    configuration = replace(
        load_market_configuration(project_root=project_root),
        local_path=target,
    )

    mock_yf.download.return_value = pd.DataFrame(
        {
            "Close": [100.0, 101.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )

    summary = fetch_market_assets(configuration, force=True)
    assert summary.failed_count == 0
    assert summary.reports[0].status == "downloaded"
    assert target.is_file()
