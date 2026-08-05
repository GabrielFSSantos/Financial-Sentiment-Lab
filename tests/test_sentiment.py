"""Testes das regras de sentimento compartilhadas pelos modelos."""

from __future__ import annotations

import pytest

from models.sentiment import (
    calculate_continuous_sentiment,
    normalize_sentiment_label,
)


def test_normalize_sentiment_label_aliases() -> None:
    assert normalize_sentiment_label("positivo") == "POSITIVE"
    assert normalize_sentiment_label("NEG") == "NEGATIVE"
    assert normalize_sentiment_label(None) is None


def test_normalize_sentiment_label_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="não reconhecido"):
        normalize_sentiment_label("indefinido")


def test_calculate_continuous_sentiment() -> None:
    assert calculate_continuous_sentiment(0.8, 0.1) == pytest.approx(0.7)
    assert calculate_continuous_sentiment(None, 0.5) is None
