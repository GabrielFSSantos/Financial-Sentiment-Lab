"""Auditoria de alinhamento semanal ITI-v2 × mercado (P05)."""

from __future__ import annotations

import pandas as pd

from modules.research.io.market_weekly_returns import (
    attach_future_weekly_log_returns,
    weekly_log_returns_from_prices,
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
    signals["period_end"] = pd.to_datetime(signals[date_col], errors="coerce").dt.date.astype(
        str
    )

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

    merged = signals.merge(
        market_subset,
        on=["ticker", "period_end"],
        how="outer",
        indicator=True,
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

        audit_rows.append(
            {
                "company_id": row.get("company_id", ""),
                "ticker": row.get("ticker", ""),
                "week_id": row.get("week_id", ""),
                "period_end": row.get("period_end", ""),
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
    for horizon in horizons:
        src = f"future_log_return_week_{horizon}"
        dst = f"future_log_return_{horizon}"
        if src in panel.columns:
            panel[dst] = panel[src]
    return panel, audit
