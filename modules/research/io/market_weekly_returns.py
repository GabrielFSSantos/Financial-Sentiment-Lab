"""Retornos semanais futuros no calendário completo (antes da junção com notícias)."""

from __future__ import annotations

import numpy as np
import pandas as pd

WEEK_FREQ = "W-FRI"


def _week_period(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.to_period(WEEK_FREQ)


def weekly_closes_from_prices(
    market_prices: pd.DataFrame,
    *,
    date_col: str = "date",
    ticker_col: str = "ticker",
    price_col: str = "adj_close",
) -> pd.DataFrame:
    """Último pregão de cada semana civil W-FRI e preço ajustado no fechamento."""

    frame = market_prices.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
    frame = frame.dropna(subset=[date_col, ticker_col, price_col])
    frame = frame.sort_values([ticker_col, date_col])

    rows: list[dict[str, object]] = []
    for ticker, group in frame.groupby(ticker_col):
        indexed = group.set_index(date_col)
        for _period_start, period_df in indexed.resample(WEEK_FREQ):
            if period_df.empty:
                continue
            close_at = period_df.index.max()
            price = float(period_df.iloc[-1][price_col])
            week_period = close_at.to_period(WEEK_FREQ)
            rows.append(
                {
                    "week_id": week_period.end_time.normalize(),
                    "week_period": str(week_period),
                    "market_close_at": close_at,
                    "ticker": ticker,
                    "week_close_price": price,
                    "period_end": close_at.date().isoformat(),
                }
            )
    return pd.DataFrame(rows)


def weekly_log_returns_from_prices(
    market_prices: pd.DataFrame,
    *,
    date_col: str = "date",
    ticker_col: str = "ticker",
    price_col: str = "adj_close",
) -> pd.DataFrame:
    """R_w = ln(P_w / P_{w-1}) com P_w = fechamento do último pregão da semana civil."""

    closes = weekly_closes_from_prices(
        market_prices,
        date_col=date_col,
        ticker_col=ticker_col,
        price_col=price_col,
    )
    if closes.empty:
        return closes.assign(log_return_week=pd.Series(dtype=float))

    parts: list[pd.DataFrame] = []
    for ticker, group in closes.groupby("ticker", sort=False):
        g = group.sort_values("week_id").copy()
        min_period = g["week_id"].min().to_period(WEEK_FREQ)
        max_period = g["week_id"].max().to_period(WEEK_FREQ)
        full_periods = pd.period_range(min_period, max_period, freq=WEEK_FREQ)

        price_by_period = {
            pd.Period(row["week_period"], freq=WEEK_FREQ): row["week_close_price"]
            for _, row in g.iterrows()
        }
        close_at_by_period = {
            pd.Period(row["week_period"], freq=WEEK_FREQ): row["market_close_at"]
            for _, row in g.iterrows()
        }

        log_returns: list[float] = []
        prices: list[float] = []
        week_ids: list[pd.Timestamp] = []
        market_closes: list[pd.Timestamp] = []
        period_ends: list[str] = []

        prev_price: float | None = None
        for period in full_periods:
            price = price_by_period.get(period)
            week_ids.append(period.end_time.normalize())
            market_closes.append(
                close_at_by_period.get(period, period.end_time.normalize())
            )
            period_ends.append(
                close_at_by_period.get(period, period.end_time.normalize())
                .date()
                .isoformat()
            )
            prices.append(float(price) if price is not None else np.nan)
            if price is None or prev_price is None or prev_price <= 0 or price <= 0:
                log_returns.append(np.nan)
            else:
                log_returns.append(float(np.log(price / prev_price)))
            if price is not None and price > 0:
                prev_price = float(price)

        parts.append(
            pd.DataFrame(
                {
                    "week_id": week_ids,
                    "week_period": [str(p) for p in full_periods],
                    "market_close_at": market_closes,
                    "ticker": ticker,
                    "week_close_price": prices,
                    "log_return_week": log_returns,
                    "period_end": period_ends,
                }
            )
        )

    return pd.concat(parts, ignore_index=True)


def attach_future_weekly_log_returns(
    weekly_returns: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    return_col: str = "log_return_week",
) -> pd.DataFrame:
    """R_w^(h) = ln(P_{w+h} / P_w) em semanas civis W-FRI (lacunas permanecem NaN)."""

    working = weekly_returns.sort_values(["ticker", "week_id"]).reset_index(drop=True)
    price_col = "week_close_price"
    if price_col not in working.columns:
        raise KeyError(
            f"Coluna {price_col!r} ausente; use weekly_log_returns_from_prices atualizado."
        )

    for horizon in horizons:
        col = f"future_{return_col}_{horizon}"
        future_values: list[float] = []
        for _, group in working.groupby("ticker", sort=False):
            periods = [
                pd.Period(value, freq=WEEK_FREQ)
                if not isinstance(value, pd.Period)
                else value
                for value in group["week_period"]
            ]
            prices = {
                period: float(price)
                for period, price in zip(periods, group[price_col])
                if pd.notna(price) and float(price) > 0
            }
            for period in periods:
                future_period = period + horizon
                p0 = prices.get(period)
                p1 = prices.get(future_period)
                if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
                    future_values.append(np.nan)
                else:
                    future_values.append(float(np.log(p1 / p0)))
        working[col] = future_values

    return working


def weekly_market_session_calendar(
    market_prices: pd.DataFrame,
    *,
    date_col: str = "date",
    ticker_col: str = "ticker",
    price_col: str = "adj_close",
) -> pd.DataFrame:
    """Calendário semanal com fechamento de mercado e cutoff causal (dia civil anterior)."""

    closes = weekly_closes_from_prices(
        market_prices,
        date_col=date_col,
        ticker_col=ticker_col,
        price_col=price_col,
    )
    if closes.empty:
        return closes.assign(signal_cutoff_at=pd.Series(dtype="datetime64[ns]"))

    out = closes.copy()
    out["signal_cutoff_at"] = (
        pd.to_datetime(out["market_close_at"]).dt.normalize() - pd.Timedelta("1D")
    )
    return out
