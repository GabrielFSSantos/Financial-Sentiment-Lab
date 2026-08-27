"""Testes do catálogo de runs."""

from __future__ import annotations

from modules.dashboard.services.catalog import get_run, list_runs


def test_list_runs_finds_sabesp_runs() -> None:
    runs = list_runs()
    ids = [r.run_id for r in runs]
    assert "sabesp_r0_baseline" in ids


def test_get_run_returns_summary() -> None:
    run = get_run("sabesp_r0_baseline")
    assert run is not None
    assert run.status == "success"
    assert "finbert_ptbr" in run.models
