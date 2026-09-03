"""Testes de cobertura do CHART_HELP."""

from __future__ import annotations

import re
from pathlib import Path

from modules.dashboard.content.chart_help import CHART_HELP

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "modules" / "dashboard"

# help_keys referenciadas em chart_block(..., "key", ...) e section_block(..., "key")
EXPECTED_KEYS = {
    "corpus_by_company",
    "corpus_by_source",
    "corpus_time_series",
    "corpus_heatmap",
    "class_distribution",
    "sentiment_by_company",
    "sentiment_time_series",
    "iti_daily",
    "iti_vs_return",
    "incremental_delta",
    "market_metrics_heatmap",
    "win_rate_by_run",
    "win_rate_heatmap",
    "alpha_vs_winrate",
    "ablation_bars",
    "sentiment_compare_runs",
    "param_diff_table",
    "pipeline_journey",
    "kappa_gate",
}


def test_chart_help_covers_inventory() -> None:
    missing = EXPECTED_KEYS - set(CHART_HELP.keys())
    assert not missing, f"CHART_HELP sem entradas: {missing}"


def test_chart_help_entries_non_empty() -> None:
    for key, text in CHART_HELP.items():
        assert text.strip(), f"CHART_HELP[{key!r}] vazio"
        assert "**" in text or "O que" in text, f"CHART_HELP[{key!r}] sem estrutura"


def test_pages_reference_known_help_keys() -> None:
    pattern = re.compile(r'chart_block\(\s*["\']([a-z_]+)["\']')
    section_pattern = re.compile(r'section_block\([^,]+,\s*["\']([a-z_]+)["\']')
    found: set[str] = set()
    for py_file in (DASHBOARD_DIR / "pages").glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        found.update(pattern.findall(content))
        found.update(section_pattern.findall(content))
    unknown = found - set(CHART_HELP.keys())
    assert not unknown, f"help_keys em páginas sem CHART_HELP: {unknown}"
