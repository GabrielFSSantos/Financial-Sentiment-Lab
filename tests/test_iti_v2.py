"""Testes ITI-v2 (P04/P08)."""

import math

import numpy as np
import pandas as pd
import pytest

from modules.experiment.indexing.iti_v2 import (
    _soft_weekly_mean_through_cutoff,
    _values_at_cutoff,
    aggregate_company_day,
    build_daily_iti_v2_frame,
    build_weekly_signals,
    compute_half_life_index,
    continuous_sentiment,
    lambda_from_half_life,
    last_eligible_signal_date,
    validate_probabilities,
)
from modules.market.loader import load_market_prices
from modules.market.config.loader import load_market_configuration
from modules.research.io.market_weekly_returns import weekly_market_session_calendar
from modules.experiment import PROJECT_ROOT


def test_lambda_half_life_two():
    assert math.isclose(lambda_from_half_life(2), 0.70710678, rel_tol=1e-6)


def test_impulse_h2_example():
    """Plano mestre: H=2, estado 0, X1=1 → ITI1≈0,29289322."""
    lam = lambda_from_half_life(2)
    daily = pd.DataFrame(
        {
            "company_id": ["sabesp"],
            "date": [pd.Timestamp("2024-01-01")],
            "soft_input": [1.0],
            "n_articles": [1],
        }
    )
    end = pd.Timestamp("2024-01-03")
    out = compute_half_life_index(daily, 2, calendar_end=end, warmup_days=0)
    series = out.sort_values("date")["iti_v2_h2"].to_numpy()
    row1 = float(series[0])
    row3 = float(series[2])
    assert math.isclose(row1, (1 - lam) * 1.0, rel_tol=1e-5)
    assert math.isclose(row3, (lam ** 2) * row1, rel_tol=1e-5)


def test_mixed_probabilities_soft_mean():
    rows = [
        {"news_id": "a", "p_negative": 0.1, "p_neutral": 0.2, "p_positive": 0.7},
        {"news_id": "b", "p_negative": 0.6, "p_neutral": 0.3, "p_positive": 0.1},
    ]
    frame = pd.DataFrame(rows)
    frame["company_id"] = "sabesp"
    frame["date"] = "2024-01-01"
    daily = aggregate_company_day(frame)
    assert math.isclose(daily["soft_mean"].iloc[0], 0.05, abs_tol=1e-9)


def test_validate_probabilities_rejects_bad_sum():
    with pytest.raises(Exception):
        validate_probabilities(0.5, 0.3, 0.1)


def test_continuous_sentiment_range():
    assert continuous_sentiment(0.7, 0.1) == pytest.approx(0.6)


def test_build_daily_preserves_silent_calendar_days():
    rows = [
        {
            "news_id": "a",
            "p_negative": 0.1,
            "p_neutral": 0.2,
            "p_positive": 0.7,
        }
    ]
    frame = pd.DataFrame(rows)
    frame["company_id"] = "sabesp"
    frame["date"] = "2024-01-01"
    daily = build_daily_iti_v2_frame(
        frame,
        half_lives=(2,),
        calendar_end=pd.Timestamp("2024-01-03"),
        warmup_days=0,
    )
    assert len(daily) == 3
    assert int(daily.loc[daily["date"] == "2024-01-02", "n_articles"].iloc[0]) == 0
    assert "iti_v2_h2" in daily.columns
    assert "warmup" in daily.columns


def test_corpus_span_marks_unknown_outside_inventory():
    rows = [
        {
            "news_id": "a",
            "p_negative": 0.1,
            "p_neutral": 0.2,
            "p_positive": 0.7,
        }
    ]
    frame = pd.DataFrame(rows)
    frame["company_id"] = "sabesp"
    frame["date"] = "2024-01-15"
    span = (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-10"))
    daily = build_daily_iti_v2_frame(
        frame,
        half_lives=(2,),
        calendar_end=pd.Timestamp("2024-01-15"),
        warmup_days=0,
        corpus_span=span,
    )
    late = daily.loc[daily["date"] == "2024-01-15"].iloc[0]
    assert late["coverage_status"] == "unknown"
    assert pd.isna(late["soft_input"])


def test_soft_weekly_mean_through_cutoff():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    indexed = pd.DataFrame(
        {
            "soft_input": [0.0, 0.6, 0.2],
            "coverage_status": ["eligible", "eligible", "eligible"],
        },
        index=dates,
    )
    cutoff = pd.Timestamp("2024-01-03")
    mean = _soft_weekly_mean_through_cutoff(indexed, cutoff, week_anchor="W-FRI")
    assert abs(mean - (0.0 + 0.6 + 0.2) / 3) < 1e-9
    assert float(indexed.loc[cutoff, "soft_input"]) == 0.2


def test_build_weekly_signals_friday_anchor():
    daily = pd.DataFrame(
        {
            "company_id": ["sabesp", "sabesp"],
            "date": ["2024-01-01", "2024-01-02"],
            "iti_v2_h7": [0.1, 0.2],
            "n_articles": [1, 0],
        }
    )
    weekly = build_weekly_signals(daily, value_columns=("iti_v2_h7", "n_articles"))
    assert len(weekly) >= 1
    assert "week_id" in weekly.columns


def test_values_at_cutoff_rejects_sessions_after_corpus_end():
    rows = [
        {
            "news_id": "a",
            "p_negative": 0.1,
            "p_neutral": 0.2,
            "p_positive": 0.7,
        }
    ]
    frame = pd.DataFrame(rows)
    frame["company_id"] = "sabesp"
    frame["date"] = "2024-04-28"
    span = (pd.Timestamp("2024-04-01"), pd.Timestamp("2024-04-30"))
    daily = build_daily_iti_v2_frame(
        frame,
        half_lives=(7,),
        calendar_end=pd.Timestamp("2024-04-30"),
        warmup_days=0,
        corpus_span=span,
    )
    indexed = daily.set_index("date")
    assert last_eligible_signal_date(indexed) == pd.Timestamp("2024-04-30")
    vals = _values_at_cutoff(
        indexed,
        pd.Timestamp("2026-08-13"),
        ("iti_v2_h7",),
    )
    assert pd.isna(vals["iti_v2_h7"])
    assert vals["signal_exclusion"] == "cutoff_after_corpus_coverage"


def test_weekly_signals_do_not_extend_past_corpus_with_long_market_calendar():
    rows = [
        {
            "news_id": "a",
            "p_negative": 0.1,
            "p_neutral": 0.2,
            "p_positive": 0.7,
        }
    ]
    frame = pd.DataFrame(rows)
    frame["company_id"] = "sabesp"
    frame["date"] = "2024-04-28"
    span = (pd.Timestamp("2024-04-01"), pd.Timestamp("2024-04-30"))
    daily = build_daily_iti_v2_frame(
        frame,
        half_lives=(7,),
        calendar_end=pd.Timestamp("2024-04-30"),
        warmup_days=0,
        corpus_span=span,
    )
    market = load_market_prices(load_market_configuration(project_root=PROJECT_ROOT))
    price_col = "adj_close" if "adj_close" in market.columns else "close"
    sessions = weekly_market_session_calendar(market, price_col=price_col)
    weekly = build_weekly_signals(
        daily,
        value_columns=("iti_v2_h7", "soft_input"),
        market_sessions=sessions,
        company_to_ticker={"sabesp": "SBSP3.SA"},
        corpus_span=span,
    )
    assert "soft_weekly_mean" in weekly.columns
    assert weekly["signal_cutoff_at"].max() <= span[1]
    after = weekly.loc[pd.to_datetime(weekly["week_end"]) > span[1]]
    assert after.empty
    late = weekly.loc[pd.to_datetime(weekly["week_end"]) > "2024-05-01"]
    if not late.empty:
        for col in ("iti_v2_h7", "soft_input"):
            assert late[col].nunique(dropna=True) > 1 or late[col].isna().all()


def test_unknown_coverage_gap_restarts_exponential_state():
    dates = pd.date_range("2024-01-01", periods=7, freq="D")
    status = ["eligible", "eligible", "unknown", "unknown", "eligible", "eligible", "eligible"]
    soft = [1.0, 0.0, np.nan, np.nan, 0.0, 0.0, 0.0]
    daily = pd.DataFrame(
        {
            "company_id": ["sabesp"] * 7,
            "date": dates,
            "soft_input": soft,
            "n_articles": [1, 0, 0, 0, 0, 0, 0],
            "coverage_status": status,
        }
    )
    out = compute_half_life_index(daily, 2, warmup_days=0)
    series = out.sort_values("date")["iti_v2_h2"].to_numpy(dtype=float)
    pre_gap = float(series[1])
    assert pre_gap > 0.0
    after_gap = float(series[4])
    assert after_gap == 0.0
    assert after_gap < pre_gap * 0.5


def test_corpus_closed_apr_2024_no_flat_iti_propagation_into_2026():
    """Regressão: mercado até 2026 não pode congelar ITI de abril/2024 em dezenas de semanas."""

    rows = [
        {
            "news_id": "a",
            "p_negative": 0.1,
            "p_neutral": 0.2,
            "p_positive": 0.7,
        },
        {
            "news_id": "b",
            "p_negative": 0.6,
            "p_neutral": 0.3,
            "p_positive": 0.1,
        },
    ]
    frame = pd.DataFrame(rows)
    frame["company_id"] = "sabesp"
    frame["date"] = ["2024-04-15", "2024-04-28"]
    span = (pd.Timestamp("2022-05-02"), pd.Timestamp("2024-04-30"))
    daily = build_daily_iti_v2_frame(
        frame,
        half_lives=(7,),
        calendar_end=pd.Timestamp("2024-04-30"),
        warmup_days=0,
        corpus_span=span,
    )
    market = load_market_prices(load_market_configuration(project_root=PROJECT_ROOT))
    price_col = "adj_close" if "adj_close" in market.columns else "close"
    sessions = weekly_market_session_calendar(market, price_col=price_col)
    weekly = build_weekly_signals(
        daily,
        value_columns=("iti_v2_h7",),
        market_sessions=sessions,
        company_to_ticker={"sabesp": "SBSP3.SA"},
        corpus_span=span,
    )
    assert weekly["signal_cutoff_at"].max().normalize() <= span[1]
    after_corpus = weekly.loc[pd.to_datetime(weekly["signal_cutoff_at"]) > span[1]]
    assert after_corpus.empty
    late_2025 = weekly.loc[pd.to_datetime(weekly["week_end"]) >= "2025-01-01"]
    assert late_2025.empty
