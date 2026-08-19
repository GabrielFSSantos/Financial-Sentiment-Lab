"""Normalização de rótulos e cálculo de sentimento contínuo."""

from __future__ import annotations

import math
from typing import Any

from modules.models.common import is_missing_scalar


CANONICAL_SENTIMENT_LABELS: tuple[str, ...] = (
    "NEGATIVE",
    "NEUTRAL",
    "POSITIVE",
)

LABEL_ALIASES: dict[str, str] = {
    "NEGATIVE": "NEGATIVE",
    "NEGATIVO": "NEGATIVE",
    "NEGATIVA": "NEGATIVE",
    "NEG": "NEGATIVE",
    "NEUTRAL": "NEUTRAL",
    "NEUTRO": "NEUTRAL",
    "NEUTRA": "NEUTRAL",
    "NEU": "NEUTRAL",
    "POSITIVE": "POSITIVE",
    "POSITIVO": "POSITIVE",
    "POSITIVA": "POSITIVE",
    "POS": "POSITIVE",
}


def normalize_sentiment_label(value: Any) -> str | None:
    """Converte rótulos comuns para NEGATIVE, NEUTRAL ou POSITIVE."""

    if is_missing_scalar(value):
        return None

    normalized = str(value).strip().upper()
    if not normalized:
        return None

    canonical = LABEL_ALIASES.get(normalized)
    if canonical is None:
        raise ValueError(
            f"Rótulo de sentimento não reconhecido: {value!r}. "
            "Valores esperados: NEGATIVE, NEUTRAL ou POSITIVE."
        )

    return canonical


def calculate_continuous_sentiment(
    prob_positive: float | None,
    prob_negative: float | None,
) -> float | None:
    """Calcula ``prob_positive - prob_negative``."""

    if prob_positive is None or prob_negative is None:
        return None

    if (
        is_missing_scalar(prob_positive)
        or is_missing_scalar(prob_negative)
    ):
        return None

    positive = float(prob_positive)
    negative = float(prob_negative)

    for field_name, probability in (
        ("prob_positive", positive),
        ("prob_negative", negative),
    ):
        if not math.isfinite(probability):
            raise ValueError(
                f"{field_name} precisa ser finito."
            )
        if not 0.0 <= probability <= 1.0:
            raise ValueError(
                f"{field_name} precisa estar entre 0 e 1."
            )

    return positive - negative


__all__ = [
    "CANONICAL_SENTIMENT_LABELS",
    "LABEL_ALIASES",
    "calculate_continuous_sentiment",
    "normalize_sentiment_label",
]
