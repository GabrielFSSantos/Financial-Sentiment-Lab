"""Testes de estatísticas do corpus."""

from __future__ import annotations

from pathlib import Path

from modules.dashboard.services.corpus import compute_stats, load_corpus


def test_corpus_sabesp_stats(project_root: Path) -> None:
    path = project_root / "data/water_utilities_corpus/articles_strict_sabesp.csv"
    if not path.is_file():
        return
    frame = load_corpus(path)
    stats = compute_stats(frame)
    assert stats.total > 0
    assert stats.companies >= 1
    assert stats.date_min is not None
