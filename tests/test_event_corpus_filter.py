"""Filtro de corpus de evento (janela + roundups)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from modules.evaluation.campaigns.event_corpus_filter import (
    EVENT_DATE_FROM,
    EVENT_DATE_TO,
    filter_roundups,
    load_event_corpus,
)


@pytest.mark.contract
def test_load_event_corpus_filters_date_and_company(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.csv"
    corpus.write_text(
        "id,noticia,data,empresa,setor\n"
        "1,a,2023-12-01,Sabesp,Water\n"
        "2,b,2022-01-01,Sabesp,Water\n"
        "3,c,2023-12-01,Outra,Water\n",
        encoding="utf-8",
    )
    frame = load_event_corpus(corpus_path=corpus)
    assert len(frame) == 1
    assert int(frame.iloc[0]["id"]) == 1


@pytest.mark.contract
def test_filter_roundups_splits_typologies(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        {
            "data": [EVENT_DATE_FROM, EVENT_DATE_FROM],
            "empresa": ["Sabesp", "Sabesp"],
            "noticia": ["focal", "agenda"],
        }
    )

    def _fake_typology(row: pd.Series) -> str:
        return "roundup_agenda" if "agenda" in str(row["noticia"]) else "focal_sabesp"

    monkeypatch.setattr(
        "modules.evaluation.campaigns.event_corpus_filter.classify_typology",
        _fake_typology,
    )
    kept, removed = filter_roundups(frame)
    assert len(kept) == 1
    assert len(removed) == 1
    assert EVENT_DATE_FROM <= EVENT_DATE_TO
