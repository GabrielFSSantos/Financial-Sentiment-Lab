"""Configuração central do dashboard."""

from __future__ import annotations

from pathlib import Path

from modules.dashboard import PROJECT_ROOT

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data"
CONFIGS_DIR = PROJECT_ROOT / "configs"
THEME_CSS = Path(__file__).resolve().parent / "theme.css"
CACHE_TTL = 300

DEFAULT_CORPUS = DATA_DIR / "saneamento_corpus" / "noticias_strict_sabesp.csv"
CAMPAIGN_MANIFEST = OUTPUTS_DIR / "campaigns" / "sabesp_2026" / "manifest.json"
