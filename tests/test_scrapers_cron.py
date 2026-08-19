"""Testes de cron/state dos scrapers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from modules.scrapers.pipeline.state import (
    is_url_seen,
    load_state,
    merge_seen_urls,
    resolve_cron_window,
    save_state,
    update_site_state,
)
from modules.scrapers.schema.csv import write_csv


def test_resolve_cron_window_uses_state_and_default(tmp_path: Path) -> None:
    state_path = tmp_path / ".scrape_state.json"
    corpus_path = tmp_path / "noticias.csv"
    save_state(
        state_path,
        {"sites": {"valor": {"last_until": "2024-05-10"}}, "seen_urls": []},
    )
    write_csv(
        corpus_path,
        [{"id": "x", "data": "2024-05-08", "titulo": "t", "fonte": "f", "url": "https://a"}],
    )

    since, until = resolve_cron_window(
        state_path=state_path,
        corpus_path=corpus_path,
        default_since="2020-01-01",
    )
    assert since == "2024-05-11"
    assert until == date.today().isoformat()


def test_seen_urls_are_normalized(tmp_path: Path) -> None:
    state = load_state(tmp_path / "missing.json")
    merge_seen_urls(state, ["https://Valor.Globo.com/foo/?x=1"])
    assert is_url_seen(state, "https://valor.globo.com/foo")


def test_update_site_state_persists(tmp_path: Path) -> None:
    state_path = tmp_path / ".scrape_state.json"
    state = load_state(state_path)
    update_site_state(
        state,
        site_key="valor",
        last_until="2024-06-30",
        collected_urls=["https://valor.globo.com/foo/"],
    )
    save_state(state_path, state)
    loaded = json.loads(state_path.read_text(encoding="utf-8"))
    assert loaded["sites"]["valor"]["last_until"] == "2024-06-30"
    assert "https://valor.globo.com/foo" in loaded["seen_urls"]
