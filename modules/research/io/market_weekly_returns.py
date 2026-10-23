"""Retornos semanais futuros no calendário completo (antes da junção com notícias)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def weekly_log_returns_from_prices(
    market_prices: pd.DataFrame,
    *,
    date_col: str = "date",
    ticker_col: str = "ticker",
    price_col: str = "adj_close",
) -> pd.DataFrame:
    """Agrega preços diários em semanas W-FRI (último pregão da semana)."""

    frame = market_prices.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col, ticker_col, price_col])
    frame = frame.sort_values([ticker_col, date_col])

    rows: list[dict[str, object]] = []
    for ticker, group in frame.groupby(ticker_col):
        indexed = group.set_index(date_col)
        for period_start, period_df in indexed.resample("W-FRI"):
            if period_df.empty:
                continue
            last_row = period_df.iloc[-1]
            rows.append(
                {
                    "week_id": period_df.index.max().normalize(),
                    "market_close_at": period_df.index.max(),
                    "ticker": ticker,
                    "log_return_week": float(
                        np.log(last_row[price_col] / period_df.iloc[0][price_col])
                    )
                    if len(period_df) > 1
                    else 0.0,
                    "period_end": period_df.index.max().date().isoformat(),
                }
            )
    return pd.DataFrame(rows)


def attach_future_weekly_log_returns(
    weekly_returns: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    return_col: str = "log_return_week",
) -> pd.DataFrame:
    """Acumula retornos futuros em semanas de calendário (não linhas sobreviventes)."""

    working = weekly_returns.sort_values(["ticker", "week_id"]).reset_index(drop=True)
    for horizon in horizons:
        col = f"future_{return_col}_{horizon}"

        def _forward(series: pd.Series) -> pd.Series:
            values = series.to_numpy(dtype=float)
            output = np.full(len(values), np.nan)
            for index in range(len(values)):
                end = index + horizon
                if end >= len(values):
                    continue
                window = values[index + 1 : end + 1]
                if np.any(np.isnan(window)):
                    continue
                output[index] = float(np.sum(window))
            return pd.Series(output, index=series.index)

        working[col] = working.groupby("ticker", group_keys=False)[return_col].apply(
            _forward
        )
    return working
