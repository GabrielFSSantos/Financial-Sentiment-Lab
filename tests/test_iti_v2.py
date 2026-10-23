"""Testes ITI-v2 (P04/P08)."""

import math

import pandas as pd
import pytest

from modules.experiment.indexing.iti_v2 import (
    aggregate_company_day,
    build_daily_iti_v2_frame,
    build_weekly_signals,
    compute_half_life_index,
    continuous_sentiment,
    lambda_from_half_life,
    validate_probabilities,
)


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
