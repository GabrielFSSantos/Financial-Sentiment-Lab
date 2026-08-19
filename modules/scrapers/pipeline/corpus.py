"""Merge de CSVs brutos em corpus único."""

from __future__ import annotations

from pathlib import Path

from modules.scrapers.schema.csv import CORPUS_COLUMNS, dedupe_records, read_csv, write_csv

GENERIC_CORPUS_COMPANIES = frozenset({"Saneamento"})
GENERIC_CORPUS_TICKERS = frozenset({"SETOR"})


def _is_generic_corpus_record(record: dict[str, str]) -> bool:
    empresa = str(record.get("empresa", "")).strip()
    ticker = str(record.get("ticker", "")).strip()
    return empresa in GENERIC_CORPUS_COMPANIES or ticker in GENERIC_CORPUS_TICKERS


def build_merged_corpus(
    *,
    raw_dir: Path,
    corpus_path: Path,
) -> int:
    records: list[dict[str, str]] = []
    if raw_dir.is_dir():
        for path in sorted(raw_dir.glob("*.csv")):
            records.extend(read_csv(path))

    merged = dedupe_records(records)
    filtered = [record for record in merged if not _is_generic_corpus_record(record)]
    discarded = len(merged) - len(filtered)
    if discarded:
        print(
            f"Corpus: {discarded} registro(s) genérico(s) descartado(s) "
            "(empresa=Saneamento ou ticker=SETOR)."
        )
    write_csv(corpus_path, filtered)
    return len(filtered)
