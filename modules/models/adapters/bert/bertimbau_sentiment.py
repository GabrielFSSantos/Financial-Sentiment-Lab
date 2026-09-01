"""Adaptador BERTimbau sentimento 3 classes (controle de domínio PT)."""

from __future__ import annotations

from modules.models.adapters.bert.finbert_hf import FinBertHfModel

DEFAULT_MODEL_NAME = "bertimbau_sentiment"


class BertimbauSentimentModel(FinBertHfModel):
    """Fine-tune de neuralmind/bert-base-portuguese-cased — não financeiro."""


__all__ = ["DEFAULT_MODEL_NAME", "BertimbauSentimentModel"]
