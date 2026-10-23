"""Cache de inferência por chave estável (texto+view+checkpoint); retomada sem duplicar."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


def inference_cache_key(
    *,
    effective_text_hash: str,
    view_id: str,
    model_key: str,
    model_revision_sha: str,
    tokenizer_sha: str = "",
    config_sha: str = "",
    dtype: str = "float32",
) -> str:
    """Monta chave; meia-vida H/h não entram na inferência."""

    payload = "|".join(
        (
            effective_text_hash,
            view_id,
            model_key,
            model_revision_sha,
            tokenizer_sha,
            config_sha,
            dtype,
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _shard_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.jsonl"


def read_cache_hits(cache_dir: Path, keys: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Lê entradas existentes; chaves ausentes ficam de fora do dict."""

    hits: dict[str, dict[str, Any]] = {}
    for key in keys:
        path = _shard_path(cache_dir, key)
        if not path.is_file():
            continue
        line = path.read_text(encoding="utf-8").strip().splitlines()[-1]
        if line:
            hits[key] = json.loads(line)
    return hits


def append_cache_entry(cache_dir: Path, key: str, record: dict[str, Any]) -> None:
    """Append atômico de uma linha JSON (última linha = versão vigente)."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _shard_path(cache_dir, key)
    tmp = path.with_suffix(".tmp")
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(payload + "\n")
    os.replace(tmp, path)


def write_batch_parquet(cache_dir: Path, batch_id: str, frame: pd.DataFrame) -> Path:
    """Persiste lote de predições para retomada (CSV para evitar dependência extra)."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"batch_{batch_id}.csv"
    tmp = out.with_suffix(".tmp.csv")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, out)
    return out
