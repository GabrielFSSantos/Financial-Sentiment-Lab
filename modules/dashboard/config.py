"""Configuração central do dashboard."""

from __future__ import annotations

from pathlib import Path

from modules.dashboard import PROJECT_ROOT

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data"
CONFIGS_DIR = PROJECT_ROOT / "configs"
DOCS_DIR = PROJECT_ROOT / "docs"
THEME_CSS = Path(__file__).resolve().parent / "theme.css"
CACHE_TTL = 300

DEFAULT_CORPUS = DATA_DIR / "water_utilities_corpus" / "articles_strict_sabesp.csv"
CAMPAIGN_MANIFEST = OUTPUTS_DIR / "campaigns" / "sabesp_2026" / "manifest.json"
CLASSIFIER_EVAL_DIR = OUTPUTS_DIR / "campaigns" / "classifier_eval_pt"
TRAJETORIA_DOC = DOCS_DIR / "research_trail" / "part-04-results.md"
DOCUMENTACAO_DOC = DOCS_DIR / "documentation" / "README.md"
CHART_INVENTORY_DOC = DOCS_DIR / "documentation" / "chart_inventory.md"

RUN_COLORS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#ca8a04",
    "#9333ea",
    "#0891b2",
    "#ea580c",
    "#4f46e5",
    "#be185d",
    "#059669",
]

BASELINE_COLORS: dict[str, str] = {
    "b0": "#64748b",
    "b1": "#2563eb",
    "b2": "#16a34a",
    "b3": "#9333ea",
}
