"""Testes do Índice Temporal Informacional (ITI)."""

from __future__ import annotations

import json

import pandas as pd

from pipeline.temporal_index import (
    build_news_impact_frame,
    compute_daily_company_impact,
    compute_iti_daily_series,
    resample_iti_series,
)


def test_build_news_impact_uses_defaults() -> None:
    predictions = pd.DataFrame(
        {
            "news_id": ["1", "2"],
            "date": ["2024-01-01", "2024-01-01"],
            "company": ["ACME", "ACME"],
            "sector": ["Tech", "Tech"],
            "continuous_sentiment": [0.5, -0.2],
            "confidence": [0.9, 0.8],
            "prediction_metadata": [None, None],
        }
    )

    impact = build_news_impact_frame(
        predictions,
        defaults={
            "magnitude": 1.0,
            "relevance": 1.0,
            "event_weight": 1.0,
            "horizon": 1.0,
            "risk": 1.0,
            "novelty": 1.0,
        },
    )

    assert len(impact) == 2
    assert impact.loc[0, "I_n"] == 0.5 * 0.9
    assert impact.loc[1, "R_n"] == 0.2 * 0.8


def test_build_news_impact_reads_metadata_dimensions() -> None:
    metadata = json.dumps(
        {
            "magnitude": 2.0,
            "relevance": 0.5,
            "event_weight": 1.5,
            "novelty": 0.8,
            "risk": 1.2,
        }
    )
    predictions = pd.DataFrame(
        {
            "news_id": ["1"],
            "date": ["2024-01-01"],
            "company": ["ACME"],
            "sector": ["Tech"],
            "continuous_sentiment": [0.4],
            "confidence": [0.7],
            "prediction_metadata": [metadata],
        }
    )

    impact = build_news_impact_frame(
        predictions,
        defaults={
            "magnitude": 1.0,
            "relevance": 1.0,
            "event_weight": 1.0,
            "horizon": 1.0,
            "risk": 1.0,
            "novelty": 1.0,
        },
    )

    expected = 0.4 * 2.0 * 0.5 * 0.7 * 1.5 * 0.8
    assert impact.loc[0, "I_n"] == expected


def test_iti_recurrence_with_dissipation() -> None:
    news_impact = pd.DataFrame(
        {
            "news_id": ["1", "2"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "company": ["ACME", "ACME"],
            "sector": ["Tech", "Tech"],
            "d": [1.0, -1.0],
            "m": [1.0, 1.0],
            "r": [1.0, 1.0],
            "c": [1.0, 1.0],
            "e": [1.0, 1.0],
            "h": [1.0, 1.0],
            "q": [1.0, 1.0],
            "u": [1.0, 1.0],
            "I_n": [1.0, -1.0],
            "R_n": [0.0, 1.0],
            "w_n": [1.0, 1.0],
        }
    )

    daily = compute_daily_company_impact(news_impact)
    iti = compute_iti_daily_series(
        daily,
        alpha=0.5,
        initial_value=0.0,
    )

    assert len(iti) == 3
    assert iti.loc[0, "impacto_dia"] == 1.0
    assert iti.loc[0, "iti_liquido"] == 0.5
    assert iti.loc[1, "impacto_dia"] == 0.0
    assert iti.loc[1, "iti_liquido"] == 0.25
    assert iti.loc[2, "impacto_dia"] == -1.0
    assert iti.loc[2, "iti_liquido"] == -0.375


def test_resample_weekly_produces_period_rows() -> None:
    iti_daily = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="D"),
            "company": ["ACME"] * 10,
            "sector": ["Tech"] * 10,
            "impacto_dia": [0.1] * 10,
            "risco_dia": [0.0] * 10,
            "news_count": [1] * 10,
            "iti_liquido": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "iti_risco": [0.0] * 10,
        }
    )

    weekly = resample_iti_series(iti_daily, frequency="weekly")

    assert not weekly.empty
    assert weekly.loc[0, "frequency"] == "weekly"
    assert weekly.loc[0, "news_count"] >= 1
