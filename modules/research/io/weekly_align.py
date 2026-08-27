"""Alinhamento semanal ITI × baselines × mercado."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.experiment.indexing.baselines import resample_baselines_weekly
from modules.research.config.loader import ResearchConfiguration
from modules.research.io.experiment import IndexCombination
from modules.research.validation.baselines import add_b3_column


def _week_end_key(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.to_period("W-FRI").dt.end_time.dt.normalize()


def _collapse_weekly_panel(frame: pd.DataFrame, *, date_source: str) -> pd.DataFrame:
    """Normaliza datas para sexta-feira (W-FRI) e colapsa duplicatas semanais."""

    if frame.empty:
        return frame

    working = frame.copy()
    working["week_end"] = _week_end_key(working[date_source])
    working = working.sort_values(date_source)
    collapsed = (
        working.groupby(["company", "sector", "week_end"], as_index=False)
        .last()
        .copy()
    )
    collapsed["date"] = collapsed["week_end"].dt.date.astype(str)
    return collapsed.drop(columns=["week_end"])


def _weekly_market_returns(
    market_prices: pd.DataFrame,
    *,
    return_column: str,
) -> pd.DataFrame:
    frame = market_prices.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    rows: list[dict[str, object]] = []

    for ticker, group in frame.groupby("ticker"):
        indexed = group.set_index("date").sort_index()
        for period_start, period_df in indexed.resample("W-FRI"):
            if period_df.empty:
                continue
            values = pd.to_numeric(period_df[return_column], errors="coerce")
            if return_column == "log_return":
                weekly_return = float(values.sum())
            else:
                weekly_return = float((1.0 + values).prod() - 1.0)
            rows.append(
                {
                    "period_start": period_start.date().isoformat(),
                    "period_end": period_df.index.max().date().isoformat(),
                    "ticker": ticker,
                    return_column: weekly_return,
                }
            )

    return pd.DataFrame(rows)


def _add_future_weekly_returns(
    frame: pd.DataFrame,
    *,
    return_column: str,
    horizons: tuple[int, ...],
) -> pd.DataFrame:
    working = frame.sort_values(["ticker", "period_end"]).reset_index(drop=True)

    for horizon in horizons:
        column_name = f"future_{return_column}_{horizon}"

        def _forward(series: pd.Series) -> pd.Series:
            values = series.to_numpy(dtype=float)
            output = np.full(len(values), np.nan)
            for index in range(len(values)):
                end = index + horizon
                if end >= len(values):
                    continue
                window = values[index + 1 : end + 1]
                if return_column == "log_return":
                    output[index] = float(np.nansum(window))
                else:
                    output[index] = float(np.prod(1.0 + window) - 1.0)
            return pd.Series(output, index=series.index)

        working[column_name] = working.groupby("ticker", group_keys=False)[
            return_column
        ].apply(_forward)

    return working


def load_weekly_iti_panel(
    combination: IndexCombination,
    configuration: ResearchConfiguration,
) -> pd.DataFrame:
    weekly_path = combination.root / "iti_weekly.csv"
    if not weekly_path.is_file():
        raise FileNotFoundError(f"iti_weekly.csv ausente: {weekly_path}")

    iti = pd.read_csv(weekly_path)
    column = configuration.iti_weekly_column
    if column not in iti.columns:
        raise KeyError(
            f"Coluna {column!r} ausente em {weekly_path}; "
            f"disponíveis: {list(iti.columns)}"
        )

    iti = iti.rename(columns={column: "iti_liquido"})
    if "iti_risco_mean" in iti.columns:
        iti["iti_risco"] = iti["iti_risco_mean"]
    elif "iti_risco_last" in iti.columns:
        iti["iti_risco"] = iti["iti_risco_last"]
    else:
        iti["iti_risco"] = 0.0

    iti["date"] = iti["period_end"]
    iti["impacto_dia"] = iti.get("impacto_dia_sum", iti.get("impacto_dia_mean", 0.0))
    iti = _collapse_weekly_panel(iti, date_source="period_end")

    baselines = resample_baselines_weekly(
        pd.read_csv(combination.baselines_daily)
    )
    baselines = _collapse_weekly_panel(baselines, date_source="period_end")

    panel = iti.merge(
        baselines,
        on=["date", "company", "sector"],
        how="inner",
        suffixes=("", "_baseline"),
    )
    panel = add_b3_column(panel)
    return panel


def align_weekly_combination(
    combination: IndexCombination,
    configuration: ResearchConfiguration,
    *,
    market_prices: pd.DataFrame,
    company_to_ticker: dict[str, str],
) -> tuple[pd.DataFrame, tuple[str, ...], int]:
    panel = load_weekly_iti_panel(combination, configuration)

    if configuration.companies_filter:
        panel = panel.loc[
            panel["company"].isin(configuration.companies_filter)
        ].copy()

    panel["ticker"] = panel["company"].map(company_to_ticker)
    dropped = tuple(
        sorted(
            company
            for company in panel.loc[panel["ticker"].isna(), "company"]
            .dropna()
            .unique()
        )
    )
    panel = panel.dropna(subset=["ticker"])

    weekly_market = _weekly_market_returns(
        market_prices,
        return_column=configuration.return_column,
    )
    merged = panel.merge(
        weekly_market,
        left_on=["date", "ticker"],
        right_on=["period_end", "ticker"],
        how="inner",
    )

    if merged.empty:
        raise ValueError("Nenhum overlap semanal date+ticker")

    if "period_end" not in merged.columns:
        if "period_end_y" in merged.columns:
            merged["period_end"] = merged["period_end_y"]
        else:
            merged["period_end"] = merged["date"]

    merged = _add_future_weekly_returns(
        merged,
        return_column=configuration.return_column,
        horizons=configuration.horizons,
    )
    merged["model_key"] = combination.model_key
    merged["dataset_key"] = combination.dataset_key

    overlap = int(merged["date"].nunique())
    return merged, dropped, overlap
