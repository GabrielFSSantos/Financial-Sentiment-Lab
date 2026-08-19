"""Alinhamento de índices do experimento com preços de mercado."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
from modules.research.config.loader import ResearchConfiguration
from modules.research.io.experiment import (
    IndexCombination,
    load_baselines_daily,
    load_iti_daily,
)
from modules.research.validation.baselines import add_b3_column


class AlignmentError(RuntimeError):
    """Erro durante o alinhamento ITI × mercado."""


@dataclass
class AlignmentResult:
    """Painel alinhado e metadados de cobertura."""

    panel: pd.DataFrame
    dropped_companies: tuple[str, ...] = field(default_factory=tuple)
    overlap_days: int = 0


def _map_company_to_ticker(
    frame: pd.DataFrame,
    mapping: dict[str, str],
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    working = frame.copy()
    working["ticker"] = working["company"].map(mapping)
    dropped = tuple(
        sorted(
            company
            for company in working.loc[working["ticker"].isna(), "company"]
            .dropna()
            .unique()
        )
    )
    return working.dropna(subset=["ticker"]), dropped


def _add_future_returns(
    frame: pd.DataFrame,
    *,
    return_column: str,
    horizons: tuple[int, ...],
) -> pd.DataFrame:
    working = frame.sort_values(["ticker", "date"]).reset_index(drop=True)

    for horizon in horizons:
        working[f"future_{return_column}_{horizon}"] = working.groupby(
            "ticker"
        )[return_column].shift(-horizon)

    return working


def align_combination(
    combination: IndexCombination,
    configuration: ResearchConfiguration,
    *,
    market_prices: pd.DataFrame | None = None,
) -> AlignmentResult:
    """Alinha ITI, baselines, B3 e retornos futuros para uma combinação."""

    iti = load_iti_daily(combination.iti_daily)
    baselines = load_baselines_daily(combination.baselines_daily)

    if iti.empty or baselines.empty:
        raise AlignmentError(
            f"Índices vazios em {combination.root}"
        )

    panel = iti.merge(
        baselines,
        on=["date", "company", "sector"],
        how="outer",
        suffixes=("", "_baseline"),
    )
    panel = add_b3_column(panel)
    panel, dropped_companies = _map_company_to_ticker(
        panel,
        configuration.company_to_ticker,
    )

    if market_prices is None:
        market_config = load_market_configuration(
            config_path=configuration.market_config_path,
        )
        market_prices = load_market_prices(market_config)

    merged = panel.merge(
        market_prices,
        on=["date", "ticker"],
        how="inner",
    )

    if merged.empty:
        raise AlignmentError(
            f"Nenhum overlap date+ticker para {combination.model_key}/"
            f"{combination.dataset_key}"
        )

    overlap_days = int(merged["date"].nunique())
    if overlap_days < configuration.min_overlap_days:
        raise AlignmentError(
            f"Overlap insuficiente ({overlap_days} < "
            f"{configuration.min_overlap_days}) em {combination.root}"
        )

    merged = _add_future_returns(
        merged,
        return_column=configuration.return_column,
        horizons=configuration.horizons,
    )
    merged["model_key"] = combination.model_key
    merged["dataset_key"] = combination.dataset_key

    return AlignmentResult(
        panel=merged,
        dropped_companies=dropped_companies,
        overlap_days=overlap_days,
    )


__all__ = [
    "AlignmentError",
    "AlignmentResult",
    "align_combination",
]
