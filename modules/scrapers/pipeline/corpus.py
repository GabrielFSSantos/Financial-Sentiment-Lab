"""Merge de CSVs brutos em corpus classificado e pendente."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modules.scrapers.schema.csv import CORPUS_COLUMNS, dedupe_records, read_csv, write_csv
from modules.scrapers.schema.entities import PENDING_COMPANY, match_entity

GENERIC_CORPUS_COMPANIES = frozenset({"Saneamento"})
GENERIC_CORPUS_TICKERS = frozenset({"SETOR"})


@dataclass(frozen=True)
class CorpusBuildResult:
    classified_count: int
    pending_count: int
    discarded_count: int


def _is_generic_corpus_record(record: dict[str, str]) -> bool:
    empresa = str(record.get("empresa", "")).strip()
    ticker = str(record.get("ticker", "")).strip()
    return empresa in GENERIC_CORPUS_COMPANIES or ticker in GENERIC_CORPUS_TICKERS


def _is_pending_record(record: dict[str, str]) -> bool:
    return str(record.get("empresa", "")).strip() == PENDING_COMPANY


def _is_classified_record(record: dict[str, str]) -> bool:
    if _is_generic_corpus_record(record) or _is_pending_record(record):
        return False
    empresa = str(record.get("empresa", "")).strip()
    ticker = str(record.get("ticker", "")).strip()
    return bool(empresa) and bool(ticker)


def apply_strict_entity_filter(records: list[dict[str, str]]) -> list[dict[str, str]]:
    """Reaplica match_entity (equivalente a collection_mode: strict na coleta)."""

    strict: list[dict[str, str]] = []
    for record in records:
        combined = (
            f"{record.get('titulo', '')} {record.get('noticia', '')}".strip()
        )
        entity = match_entity(combined)
        if entity is None:
            continue
        updated = dict(record)
        updated["empresa"] = entity.company
        updated["setor"] = entity.sector
        updated["ticker"] = entity.ticker
        strict.append(updated)
    return strict


def filter_corpus_records(
    records: list[dict[str, str]],
    *,
    company: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for record in records:
        if company and str(record.get("empresa", "")).strip() != company:
            continue
        record_date = str(record.get("data", "")).strip()[:10]
        if since and record_date and record_date < since:
            continue
        if until and record_date and record_date > until:
            continue
        filtered.append(record)
    return filtered


def build_strict_corpus(
    *,
    raw_dir: Path,
    strict_path: Path,
) -> CorpusBuildResult:
    records: list[dict[str, str]] = []
    if raw_dir.is_dir():
        for path in sorted(raw_dir.glob("*.csv")):
            records.extend(read_csv(path))

    merged = dedupe_records(records)
    strict_records = apply_strict_entity_filter(merged)
    classified = [record for record in strict_records if _is_classified_record(record)]
    discarded = len(merged) - len(strict_records) + len(strict_records) - len(classified)

    if discarded:
        print(
            f"Corpus strict: {discarded} registro(s) descartado(s) "
            "(sem entidade ou classificação inválida)."
        )

    write_csv(strict_path, classified)
    return CorpusBuildResult(
        classified_count=len(classified),
        pending_count=0,
        discarded_count=discarded,
    )


def build_merged_corpus(
    *,
    raw_dir: Path,
    corpus_path: Path,
    pending_path: Path | None = None,
) -> CorpusBuildResult:
    records: list[dict[str, str]] = []
    if raw_dir.is_dir():
        for path in sorted(raw_dir.glob("*.csv")):
            records.extend(read_csv(path))

    merged = dedupe_records(records)
    classified = [record for record in merged if _is_classified_record(record)]
    pending = [record for record in merged if _is_pending_record(record)]
    discarded = len(merged) - len(classified) - len(pending)

    if discarded:
        print(
            f"Corpus: {discarded} registro(s) descartado(s) "
            "(genéricos ou sem classificação válida)."
        )

    write_csv(corpus_path, classified)
    if pending_path is not None:
        write_csv(pending_path, pending)

    return CorpusBuildResult(
        classified_count=len(classified),
        pending_count=len(pending),
        discarded_count=discarded,
    )
