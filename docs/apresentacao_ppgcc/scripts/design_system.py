#!/usr/bin/env python3
"""Sistema de design compartilhado (PDF e Google Slides) — coordenadas em %."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "dados" / "design_system.json"

SYNTHESIS_RECT = [5, 73.5, 90, 5.5]
NOTE_RECT = [5, 73.0, 90, 6.0]


@lru_cache(maxsize=1)
def load() -> dict:
    if not DESIGN_PATH.is_file():
        raise FileNotFoundError(DESIGN_PATH)
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def zones() -> dict:
    return load()["zones_pct"]


def colors() -> dict:
    return load()["colors"]


def beamer_typography() -> dict:
    return load()["typography_beamer_pt"]


def component_for_layout(layout: str) -> str:
    return load()["components"].get(layout, "generic_frame")
