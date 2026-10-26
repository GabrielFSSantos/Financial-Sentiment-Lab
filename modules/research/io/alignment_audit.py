"""Auditoria de alinhamento semanal ITI-v2 × mercado (P05)."""

from __future__ import annotations

import pandas as pd

from modules.research.io.market_weekly_returns import (
    attach_future_weekly_log_returns,
    weekly_log_returns_from_prices,
)
from modules.research.io.week_key import (
    week_key_from_week_id_column,
    week_key_series,
    week_key_to_iso_string,
)


def _normalize_company_key(value: str) -> str:
    return str(value).strip().lower()


def resolve_ticker(
    company_id: str,
    company_to_ticker: dict[str, str],
) -> str | None:
    direct = company_to_ticker.get(company_id)
    if direct:
        return direct
    lowered = {_normalize_company_key(k): v for k, v in company_to_ticker.items()}
    return lowered.get(_normalize_company_key(company_id))


def _signal_week_key(signals: pd.DataFrame, date_col: str) -> pd.Series:
    if "week_id" in signals.columns:
        return week_key_from_week_id_column(signals["week_id"])
    if "week_end" in signals.columns:
        return week_key_series(signals["week_end"])
    return week_key_series(signals[date_col])


def align_iti_v2_weekly_to_market(
    weekly_signals: pd.DataFrame,
    market_prices: pd.DataFrame,
    *,
    company_to_ticker: dict[str, str],
    horizons: tuple[int, ...],
    signal_column: str,
    price_col: str = "adj_close",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Junta sinais semanais ao calendário de preços; retorna painel e auditoria."""

    if signal_column not in weekly_signals.columns:
        raise KeyError(f"Coluna de sinal ausente: {signal_column}")

    signals = weekly_signals.copy()
    if "company_id" not in signals.columns:
        raise ValueError("weekly_signals precisa de company_id")
    signals["ticker"] = signals["company_id"].map(
        lambda c: resolve_ticker(str(c), company_to_ticker)
    )
    signals = signals.dropna(subset=["ticker"])

    date_col = "date" if "date" in signals.columns else "week_end"
    if "period_end" in signals.columns:
        signals["signal_period_end"] = (
            pd.to_datetime(signals["period_end"], errors="coerce").dt.date.astype(str)
        )
    else:
        signals["signal_period_end"] = (
            pd.to_datetime(signals[date_col], errors="coerce").dt.date.astype(str)
        )
    signals["signal_week_id"] = signals["week_id"] if "week_id" in signals.columns else ""
    signals["week_key"] = _signal_week_key(signals, date_col)
    signals = signals.drop(columns=["period_end"], errors="ignore")

    weekly_market = weekly_log_returns_from_prices(
        market_prices,
        price_col=price_col if price_col in market_prices.columns else "close",
    )
    weekly_market = attach_future_weekly_log_returns(
        weekly_market,
        horizons=horizons,
        return_col="log_return_week",
    )

    tickers = sorted(signals["ticker"].unique())
    market_subset = weekly_market.loc[weekly_market["ticker"].isin(tickers)].copy()
    market_subset["week_key"] = week_key_series(market_subset["week_id"])
    market_subset = market_subset.rename(
        columns={
            "period_end": "market_period_end",
            "week_id": "market_week_id",
        }
    )

    if signals.duplicated(subset=["ticker", "week_key"]).any():
        dup = signals.loc[signals.duplicated(subset=["ticker", "week_key"], keep=False)]
        raise ValueError(
            f"Sinais duplicados por (ticker, week_key): {dup[['ticker', 'week_key']].head()}"
        )
    if market_subset.duplicated(subset=["ticker", "week_key"]).any():
        dup = market_subset.loc[
            market_subset.duplicated(subset=["ticker", "week_key"], keep=False)
        ]
        raise ValueError(
            f"Mercado duplicado por (ticker, week_key): {dup[['ticker', 'week_key']].head()}"
        )

    merged = signals.merge(
        market_subset,
        on=["ticker", "week_key"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )

    audit_rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        reasons: list[str] = []
        if row["_merge"] == "right_only":
            reasons.append("no_news_signal")
        if row["_merge"] == "left_only":
            reasons.append("no_market_week")
        signal_val = row.get(signal_column)
        if pd.isna(signal_val):
            reasons.append("missing_signal_value")
        for horizon in horizons:
            fut_col = f"future_log_return_week_{horizon}"
            if fut_col in row.index and pd.isna(row[fut_col]):
                reasons.append(f"future_return_h{horizon}_undefined")
        join_status = "ok" if not reasons else "partial"
        if row["_merge"] != "both":
            join_status = "dropped"

        wk = row.get("week_key")
        audit_rows.append(
            {
                "company_id": row.get("company_id", ""),
                "ticker": row.get("ticker", ""),
                "week_key": week_key_to_iso_string(wk) if wk is not None else "",
                "signal_week_id": row.get("signal_week_id", ""),
                "market_week_id": row.get("market_week_id", ""),
                "signal_period_end": row.get("signal_period_end", ""),
                "market_period_end": row.get("market_period_end", ""),
                "market_close_at": row.get("market_close_at", ""),
                "signal_column": signal_column,
                "signal_value": signal_val,
                "n_articles": row.get("n_articles", pd.NA),
                "merge_side": row["_merge"],
                "join_status": join_status,
                "loss_reason": ";".join(reasons) if reasons else "",
            }
        )

    audit = pd.DataFrame(audit_rows)
    panel = merged.loc[merged["_merge"] == "both"].copy()
    panel = panel.drop(columns=["_merge"], errors="ignore")
    panel["period_end"] = panel["market_period_end"]
    panel["week_id"] = panel["market_week_id"]
    for horizon in horizons:
        src = f"future_log_return_week_{horizon}"
        dst = f"future_log_return_{horizon}"
        if src in panel.columns:
            panel[dst] = panel[src]
    return panel, audit
