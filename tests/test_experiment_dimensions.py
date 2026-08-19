"""Testes das dimensões heurísticas do ITI."""

from __future__ import annotations

import pandas as pd

from modules.experiment.indexing.dimensions import resolve_dimensions


def test_heuristics_boost_relevance_for_ticker_match() -> None:
    frame = pd.DataFrame(
        {
            "title": ["Sabesp anuncia investimentos"],
            "text": ["A Sabesp SBSP3 detalhou plano de saneamento"],
            "company": ["Sabesp"],
            "ticker": ["SBSP3"],
            "continuous_sentiment": [0.6],
            "confidence": [0.9],
        }
    )
    dimensions = resolve_dimensions(
        frame,
        settings={"dimensions": {"heuristics": {"enabled": True}}},
        defaults={
            "magnitude": 1.0,
            "relevance": 1.0,
            "event_weight": 1.0,
            "horizon": 1.0,
            "risk": 1.0,
            "novelty": 1.0,
        },
    )
    assert dimensions["relevance"].iloc[0] >= 1.0
    assert dimensions["magnitude"].iloc[0] > 0.5
    assert dimensions["event_weight"].iloc[0] >= 1.15


def test_dataset_columns_override_defaults() -> None:
    frame = pd.DataFrame(
        {
            "title": ["Notícia"],
            "text": ["Texto"],
            "m": [1.5],
            "r": [0.4],
        }
    )
    dimensions = resolve_dimensions(
        frame,
        settings={
            "dimensions": {
                "provider_order": ["dataset_columns", "defaults"],
                "heuristics": {"enabled": False},
            }
        },
        defaults={
            "magnitude": 1.0,
            "relevance": 1.0,
            "event_weight": 1.0,
            "horizon": 1.0,
            "risk": 1.0,
            "novelty": 1.0,
        },
    )
    assert dimensions["magnitude"].iloc[0] == 1.5
    assert dimensions["relevance"].iloc[0] == 0.4
