"""Schema CSV do corpus de saneamento."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

CORPUS_COLUMNS: tuple[str, ...] = (
    "id",
    "data",
    "empresa",
    "setor",
    "ticker",
    "titulo",
    "noticia",
    "fonte",
    "url",
)

_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", "", ""))


def normalize_title(title: str) -> str:
    collapsed = _WHITESPACE_PATTERN.sub(" ", str(title or "").strip().lower())
    return collapsed


def dedupe_key(record: Mapping[str, str]) -> str:
    url_key = normalize_url(str(record.get("url", "")))
    if url_key:
        return f"url:{url_key}"

    record_id = str(record.get("id", "")).strip()
    if record_id:
        return f"id:{record_id}"

    composite = (
        str(record.get("data", "")).strip(),
        str(record.get("fonte", "")).strip().lower(),
        normalize_title(str(record.get("titulo", ""))),
    )
    if any(composite):
        return f"meta:{composite[0]}|{composite[1]}|{composite[2]}"
    return ""


def write_csv(path: Path, records: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORPUS_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in CORPUS_COLUMNS})


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def dedupe_records(records: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for record in records:
        key = dedupe_key(record)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append({column: str(record.get(column, "")) for column in CORPUS_COLUMNS})
    return unique


def append_records(path: Path, records: Iterable[Mapping[str, str]]) -> tuple[int, int]:
    existing = read_csv(path)
    merged = dedupe_records([*existing, *records])
    write_csv(path, merged)
    return len(merged), max(len(merged) - len(existing), 0)

