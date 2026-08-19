"""Adaptador FinBERT em inglês (ProsusAI/finbert)."""

from __future__ import annotations

from modules.models.adapters.bert.finbert_hf import FinBertHfModel

DEFAULT_MODEL_NAME = "finbert_en"


class FinBertEnModel(FinBertHfModel):
    """Checkpoint ProsusAI/finbert."""


__all__ = ["DEFAULT_MODEL_NAME", "FinBertEnModel"]
