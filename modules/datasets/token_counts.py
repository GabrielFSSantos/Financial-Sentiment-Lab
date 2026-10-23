"""Contagem de tokens do tokenizador do modelo (subpalavras), não contagem por espaços."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def _load_tokenizer(model_dir: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_dir, use_fast=True)


def count_encoder_tokens(text: str, model_dir: Path | str) -> int:
    """Tokens com especiais, como na entrada típica do encoder."""

    stripped = text.strip()
    if not stripped:
        return 0
    tokenizer = _load_tokenizer(str(model_dir))
    return int(len(tokenizer.encode(stripped, add_special_tokens=True)))
