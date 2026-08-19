"""Testes do schema CSV dos scrapers."""

from __future__ import annotations

from modules.scrapers.schema.csv import (
    CORPUS_COLUMNS,
    dedupe_key,
    dedupe_records,
    normalize_title,
    normalize_url,
)


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
