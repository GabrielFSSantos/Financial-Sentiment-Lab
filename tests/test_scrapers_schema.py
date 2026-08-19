"""Testes do schema CSV dos scrapers."""

from __future__ import annotations

from modules.scrapers.pipeline.corpus import build_merged_corpus
from modules.scrapers.schema.csv import (
    CORPUS_COLUMNS,
    dedupe_key,
    dedupe_records,
    normalize_title,
    normalize_url,
)
from modules.scrapers.schema.entities import match_entity


def test_match_entity_returns_none_for_generic_sector_text() -> None:
    assert match_entity("Setor de saneamento avança no trimestre") is None


def test_match_entity_matches_copasa() -> None:
    entity = match_entity("Copasa anuncia investimentos")
    assert entity is not None
    assert entity.company == "Copasa"
    assert entity.ticker == "CSMG3"


def test_build_merged_corpus_filters_generic_records(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "sample.csv").write_text(
        "id,data,empresa,setor,ticker,titulo,noticia,fonte,url\n"
        "1,2024-01-01,Sabesp,Saneamento,SBSP3,t1,n1,f1,https://a\n"
        "2,2024-01-02,Saneamento,Saneamento,SETOR,t2,n2,f2,https://b\n",
        encoding="utf-8",
    )
    corpus_path = tmp_path / "noticias.csv"
    count = build_merged_corpus(raw_dir=raw_dir, corpus_path=corpus_path)
    assert count == 1
    content = corpus_path.read_text(encoding="utf-8")
    assert "SETOR" not in content
    assert "Sabesp" in content


def test_corpus_columns_order() -> None:
    assert CORPUS_COLUMNS[0] == "id"
    assert "noticia" in CORPUS_COLUMNS


def test_dedupe_records_by_id() -> None:
    records = [
        {"id": "a", "data": "2024-01-01", "noticia": "x"},
        {"id": "a", "data": "2024-01-02", "noticia": "y"},
        {"id": "b", "data": "2024-01-03", "noticia": "z"},
    ]
    unique = dedupe_records(records)
    assert len(unique) == 2


def test_normalize_url_strips_query_and_trailing_slash() -> None:
    assert normalize_url("HTTPS://Valor.Globo.com/foo/?utm=1#x") == "https://valor.globo.com/foo"


def test_dedupe_records_by_normalized_url() -> None:
    records = [
        {"id": "a", "url": "https://valor.globo.com/foo/"},
        {"id": "b", "url": "https://valor.globo.com/foo?utm=1"},
    ]
    unique = dedupe_records(records)
    assert len(unique) == 1


def test_dedupe_records_by_composite_title() -> None:
    records = [
        {"data": "2024-01-01", "fonte": "Valor", "titulo": "Sabesp avança"},
        {"data": "2024-01-01", "fonte": "Valor", "titulo": "  SABESP   AVANÇA  "},
    ]
    assert dedupe_key(records[0]) == dedupe_key(records[1])
    unique = dedupe_records(records)
    assert len(unique) == 1


def test_normalize_title() -> None:
    assert normalize_title("  Sabesp   AVANÇA  ") == "sabesp avança"
