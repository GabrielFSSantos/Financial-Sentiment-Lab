"""Rótulos amigáveis para valores do domínio FSL."""

from __future__ import annotations

_BASELINE_LABELS: dict[str, str] = {
    "b0": "B0 — contagem de notícias",
    "b1": "B1 — sentimento médio",
    "b2": "B2 — sentimento ponderado por confiança",
    "b3": "B3 — sentimento setorial",
    "b0_news_count": "B0 — contagem de notícias",
    "b1_mean_sentiment": "B1 — sentimento médio",
    "b2_confidence_weighted_sentiment": "B2 — sentimento ponderado",
}


def baseline_label(key: str) -> str:
    normalized = key.strip().lower().replace("-", "")
    if normalized in _BASELINE_LABELS:
        return _BASELINE_LABELS[normalized]
    if normalized.startswith("b") and len(normalized) == 2 and normalized[1].isdigit():
        return _BASELINE_LABELS.get(normalized, key.upper())
    return key


def horizon_label(weeks: int) -> str:
    if weeks == 1:
        return "1 semana"
    return f"{weeks} semanas"


def run_short_name(run_id: str, *, max_len: int = 24) -> str:
    if len(run_id) <= max_len:
        return run_id
    return run_id[: max_len - 1] + "…"


def model_label(model_key: str) -> str:
    labels = {
        "finbert_ptbr": "FinBERT PT-BR",
        "bertweet_pt_sentiment": "BERTweet PT",
        "bertimbau_sentiment": "BERTimbau Sentiment",
    }
    return labels.get(model_key, model_key.replace("_", " ").title())
