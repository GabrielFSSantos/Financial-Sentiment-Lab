"""Adaptador FinBERT-Tone em inglês (yiyanghkust/finbert-tone)."""

from __future__ import annotations

from models.bert.finbert_hf import FinBertHfModel

DEFAULT_MODEL_NAME = "finbert_tone_en"


class FinBertToneEnModel(FinBertHfModel):
    """Checkpoint yiyanghkust/finbert-tone."""


__all__ = ["DEFAULT_MODEL_NAME", "FinBertToneEnModel"]
