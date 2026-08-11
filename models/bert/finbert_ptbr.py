"""Adaptador FinBERT-PT-BR (lucas-leme/FinBERT-PT-BR)."""

from __future__ import annotations

from models.bert.finbert_hf import FinBertHfModel

DEFAULT_MODEL_NAME = "finbert_ptbr"


class FinBertPtBrModel(FinBertHfModel):
    """Checkpoint FinBERT-PT-BR."""


__all__ = ["DEFAULT_MODEL_NAME", "FinBertPtBrModel"]
