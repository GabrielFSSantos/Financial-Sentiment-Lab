"""Testes de fetch de mercado (``modules.market.assets``)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from modules.market.assets import fetch_market_assets
from modules.market.config.loader import MarketConfiguration, load_market_configuration
from modules.market.loader import load_market_prices


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


@patch("modules.market.assets.yf")
def test_fetch_market_assets_handles_multiindex_single_ticker(
    mock_yf,
    project_root: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "prices.csv"
    source = load_market_configuration(project_root=project_root).source
    assert source is not None
    configuration = replace(
        load_market_configuration(project_root=project_root),
        local_path=target,
        source=replace(source, tickers=("SBSP3.SA",)),
    )

    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "SBSP3.SA"),
            ("Open", "SBSP3.SA"),
        ]
    )
    frame = pd.DataFrame(
        {
            ("Close", "SBSP3.SA"): [100.0, 101.0],
            ("Open", "SBSP3.SA"): [99.0, 100.0],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )
    frame.columns = columns
    mock_yf.download.return_value = frame

    summary = fetch_market_assets(configuration, force=True)
    assert summary.failed_count == 0

    loaded = pd.read_csv(target)
    assert list(loaded.columns) == ["date", "ticker", "close"]
    assert loaded["close"].notna().all()
    assert (loaded["ticker"] == "SBSP3.SA").all()


@patch("modules.market.assets.yf")
def test_fetch_market_assets_concat_multi_ticker_without_duplicate_columns(
    mock_yf,
    project_root: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "prices.csv"
    source = load_market_configuration(project_root=project_root).source
    assert source is not None
    configuration = replace(
        load_market_configuration(project_root=project_root),
        local_path=target,
        source=replace(source, tickers=("AAA", "BBB", "CCC")),
    )

    def _download_side_effect(ticker, **_kwargs):
        index = pd.to_datetime(["2024-01-02", "2024-01-03"])
        if ticker == "AAA":
            return pd.DataFrame({"Close": [10.0, 11.0]}, index=index)

        open_ticker = "BBB" if ticker == "BBB" else "CCC"
        close_values = [20.0, 21.0] if ticker == "BBB" else [30.0, 31.0]
        frame = pd.DataFrame(
            {
                ("Close", open_ticker): close_values,
                ("Open", open_ticker): [value - 1 for value in close_values],
            },
            index=index,
        )
        frame.columns = pd.MultiIndex.from_tuples(list(frame.columns))
        return frame

    mock_yf.download.side_effect = _download_side_effect

    summary = fetch_market_assets(configuration, force=True)
    assert summary.failed_count == 0

    frame = pd.read_csv(target)
    assert list(frame.columns) == ["date", "ticker", "close"]
    assert set(frame["ticker"]) == {"AAA", "BBB", "CCC"}
    assert frame["close"].notna().all()


@patch("modules.market.assets.yf")
def test_fetch_then_load_market_prices(
    mock_yf,
    project_root: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "prices.csv"
    configuration: MarketConfiguration = replace(
        load_market_configuration(project_root=project_root),
        local_path=target,
        source=None,
    )

    target.write_text(
        "date,ticker,close\n"
        "2024-01-01,AAA,10\n"
        "2024-01-02,AAA,11\n",
        encoding="utf-8",
    )

    loaded = load_market_prices(configuration)
    assert "log_return" in loaded.columns
    assert loaded["close"].notna().all()


def test_load_market_prices_drops_invalid_rows(
    project_root: Path,
    tmp_path: Path,
) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "date,ticker,close\n"
        "NaN,NaN,SBSP3.SA\n"
        "2024-01-01,AAA,10\n"
        "2024-01-02,AAA,not-a-number\n"
        "2024-01-03,AAA,12\n",
        encoding="utf-8",
    )
    configuration = replace(
        load_market_configuration(project_root=project_root),
        local_path=bad_csv,
        source=None,
    )

    loaded = load_market_prices(configuration)
    assert len(loaded) == 2
    assert loaded["close"].notna().all()
