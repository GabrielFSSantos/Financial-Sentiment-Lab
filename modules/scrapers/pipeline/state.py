"""Estado incremental da coleta (cron)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from modules.scrapers.schema.csv import normalize_url, read_csv


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"sites": {}, "seen_urls": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"sites": {}, "seen_urls": []}
    payload.setdefault("sites", {})
    payload.setdefault("seen_urls", [])
    return payload


def save_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(state), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def resolve_cron_window(
    *,
    state_path: Path,
    corpus_path: Path,
    default_since: str,
) -> tuple[str, str]:
    until = date.today().isoformat()
    since_candidates: list[date] = []

    default_date = _parse_iso_date(default_since)
    if default_date is not None:
        since_candidates.append(default_date)

    state = load_state(state_path)
    for site_state in state.get("sites", {}).values():
        if isinstance(site_state, dict):
            last_until = _parse_iso_date(str(site_state.get("last_until", "")))
            if last_until is not None:
                since_candidates.append(last_until + timedelta(days=1))

    if corpus_path.is_file():
        max_corpus_date = _max_date_from_corpus(corpus_path)
        if max_corpus_date is not None:
            since_candidates.append(max_corpus_date + timedelta(days=1))

    if since_candidates:
        since = max(since_candidates).isoformat()
    else:
        since = default_since

    if since > until:
        since = until
    return since, until


def merge_seen_urls(state: dict[str, Any], urls: Iterable[str]) -> None:
    seen = {normalize_url(item) for item in state.get("seen_urls", []) if item}
    for url in urls:
        normalized = normalize_url(url)
        if normalized:
            seen.add(normalized)
    state["seen_urls"] = sorted(seen)


def update_site_state(
    state: dict[str, Any],
    *,
    site_key: str,
    last_until: str,
    collected_urls: Iterable[str],
) -> None:
    sites = state.setdefault("sites", {})
    site_state = sites.setdefault(site_key, {})
    if isinstance(site_state, dict):
        site_state["last_until"] = last_until
        site_state["last_run"] = datetime.now().isoformat(timespec="seconds")
    merge_seen_urls(state, collected_urls)


def is_url_seen(state: Mapping[str, Any], url: str) -> bool:
    normalized = normalize_url(url)
    if not normalized:
        return False
    seen = state.get("seen_urls", [])
    if normalized in seen:
        return True
    return normalized in {normalize_url(str(item)) for item in seen}


def _parse_iso_date(value: str) -> date | None:
    raw = str(value or "").strip()[:10]
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _max_date_from_corpus(corpus_path: Path) -> date | None:
    records = read_csv(corpus_path)
    dates: list[date] = []
    for record in records:
        parsed = _parse_iso_date(record.get("data", ""))
        if parsed is not None:
            dates.append(parsed)
    return max(dates) if dates else None
