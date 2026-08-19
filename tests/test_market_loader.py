"""Testes de leitura de preços (``modules.market.loader``)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from modules.market.config.loader import load_market_configuration
from modules.market.loader import MarketLoaderError, load_market_prices


def _fixture_configuration(
    project_root: Path,
    prices_path: Path,
) -> object:
    configuration = load_market_configuration(project_root=project_root)
    return replace(
        configuration,
        local_path=prices_path,
        source=None,
    )


def test_load_market_prices_computes_returns(
    project_root: Path,
) -> None:
    prices_path = (
        project_root / "tests" / "fixtures" / "market" / "prices.csv"
    )
    configuration = _fixture_configuration(project_root, prices_path)
    frame = load_market_prices(configuration)

    assert {"date", "ticker", "close", "simple_return", "log_return"}.issubset(
        frame.columns
    )
    assert len(frame) == 13
    assert frame["simple_return"].notna().sum() == 12


def test_load_market_prices_rejects_missing_file(
    project_root: Path,
    tmp_path: Path,
) -> None:
    configuration = _fixture_configuration(
        project_root,
        tmp_path / "missing.csv",
    )

    with pytest.raises(MarketLoaderError, match="não encontrado"):
        load_market_prices(configuration)


def test_load_market_prices_rejects_missing_column(
    project_root: Path,
    tmp_path: Path,
) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("date,ticker\n2024-01-01,AAA\n", encoding="utf-8")
    configuration = _fixture_configuration(project_root, bad_csv)

    with pytest.raises(MarketLoaderError, match="Colunas ausentes"):
        load_market_prices(configuration)
