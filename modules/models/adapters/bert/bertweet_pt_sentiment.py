"""Adaptador BERTweet-PT sentimento (pysentimiento/bertweet-pt-sentiment)."""

from __future__ import annotations

from modules.models.adapters.bert.finbert_hf import FinBertHfModel

DEFAULT_MODEL_NAME = "bertweet_pt_sentiment"


class BertweetPtSentimentModel(FinBertHfModel):
    """Checkpoint RoBERTa/BERTweet PT — controle genérico, não financeiro."""


__all__ = ["DEFAULT_MODEL_NAME", "BertweetPtSentimentModel"]
