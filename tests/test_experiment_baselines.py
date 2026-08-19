"""Testes dos baselines B0–B2."""

from __future__ import annotations

import pandas as pd
import pytest

from modules.experiment.indexing.baselines import build_baselines_daily


def test_baselines_daily_counts_and_means() -> None:
    predictions = pd.DataFrame(
        {
            "news_id": ["1", "2", "3"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "company": ["Sabesp", "Sabesp", "Sabesp"],
            "sector": ["Saneamento", "Saneamento", "Saneamento"],
            "continuous_sentiment": [0.4, -0.2, 0.1],
            "confidence": [0.9, 0.8, 0.7],
        }
    )
    baselines = build_baselines_daily(predictions)
    day_one = baselines[baselines["date"] == "2024-01-01"].iloc[0]
    assert day_one["b0_news_count"] == 2
    assert day_one["b1_mean_sentiment"] == pytest.approx(0.1)
    assert day_one["b2_confidence_weighted_sentiment"] == pytest.approx(
        (0.4 * 0.9 + -0.2 * 0.8) / (0.9 + 0.8)
    )
