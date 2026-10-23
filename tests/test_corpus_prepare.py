"""Testes P02: preparação de corpus determinística."""

from pathlib import Path

import pandas as pd

from modules.datasets.corpus_prepare import build_dedup_map, run_p02_prepare
from modules.datasets.corpus_inventory import file_sha256


def test_dedup_by_url(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {"id": "a1", "url": "https://x.com/1/", "titulo": "T", "noticia": "body", "data": "2020-01-01", "fonte": "f"},
            {"id": "a2", "url": "https://x.com/1", "titulo": "T2", "noticia": "other", "data": "2020-01-02", "fonte": "f"},
        ]
    )
    canonical, dedup = build_dedup_map(frame)
    assert len(canonical) == 1
    assert len(dedup) == 1
    assert dedup.iloc[0]["rule"] == "url_canonical"


def test_run_p02_prepare_artifacts(tmp_path: Path, project_root: Path) -> None:
    src = project_root / "data" / "water_utilities_corpus" / "articles_strict_sabesp.csv"
    if not src.is_file():
        return
    out = tmp_path / "p02"
    paths = run_p02_prepare(src, out)
    assert paths["corpus_manifest"].is_file()
    assert paths["articles_canonical"].is_file()
    assert paths["dedup_map"].is_file()
    assert paths["split_manifest"].is_file()
    h1 = file_sha256(paths["articles_canonical"])
    paths2 = run_p02_prepare(src, tmp_path / "p02b")
    h2 = file_sha256(paths2["articles_canonical"])
    assert h1 == h2
