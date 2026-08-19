"""Merge de CSVs brutos em corpus único."""

from __future__ import annotations

from pathlib import Path

from modules.scrapers.schema.csv import CORPUS_COLUMNS, dedupe_records, read_csv, write_csv


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
    write_csv(corpus_path, merged)
    return len(merged)
