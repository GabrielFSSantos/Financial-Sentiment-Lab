"""Cache de inferência ITI-v2."""

from pathlib import Path

from modules.models.inference_cache import (
    append_cache_entry,
    inference_cache_key,
    read_cache_hits,
)


def test_cache_key_changes_with_checkpoint(tmp_path: Path) -> None:
    k1 = inference_cache_key(
        effective_text_hash="abc",
        view_id="entity_context_v1",
        model_key="finbert_ptbr",
        model_revision_sha="sha1",
    )
    k2 = inference_cache_key(
        effective_text_hash="abc",
        view_id="entity_context_v1",
        model_key="finbert_ptbr",
        model_revision_sha="sha2",
    )
    assert k1 != k2


def test_cache_roundtrip(tmp_path: Path) -> None:
    key = inference_cache_key(
        effective_text_hash="x",
        view_id="document_v1",
        model_key="m",
        model_revision_sha="s",
    )
    append_cache_entry(tmp_path, key, {"p_positive": 0.5})
    hits = read_cache_hits(tmp_path, [key])
    assert hits[key]["p_positive"] == 0.5
