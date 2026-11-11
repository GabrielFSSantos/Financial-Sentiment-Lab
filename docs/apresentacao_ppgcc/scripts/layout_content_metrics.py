#!/usr/bin/env python3
"""Estimativa de altura efetiva de elementos do manifesto v4 (% da página)."""

from __future__ import annotations

import math
import re

PAGE_W_PT = 336.0
PAGE_H_PT = 189.0
SAFETY = 1.12

FOOTER_NOTE_IDS = frozenset(
    {
        "message",
        "legenda",
        "aviso",
        "fim",
        "futuro",
        "nota_ref",
    }
)

CONTENT_MAX_BOTTOM_PCT = 73.0
SYNTH_MIN_Y_PCT = 73.0
SYNTH_MAX_BOTTOM_PCT = 80.5
MIN_TEXT_H_PCT = 3.0


def _style(el: dict) -> dict:
    return el.get("style") or {}


def title_content_top_pct(title: str, *, width_pct: float = 88.0) -> float:
    """Y mínimo (% page) para o primeiro elemento após o título renderizado."""
    size = 18.0
    lead = 20.0
    width_pt = PAGE_W_PT * width_pct / 100
    chars_per_line = max(18.0, width_pt / (size * 0.48))
    words = title.split()
    lines = 1
    cur = 0.0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur + add > chars_per_line:
            lines += 1
            cur = float(len(w))
        else:
            cur += add
    title_h_pt = 4.0 / 100 * PAGE_H_PT + lines * lead
    return min(28.0, title_h_pt / PAGE_H_PT * 100 + 1.5)


def est_text_lines(text: str, width_pct: float, size_pt: float) -> float:
    text = re.sub(r"\*+", "", text or "")
    explicit = text.count("\n") + (1 if text else 0)
    width_pt = PAGE_W_PT * width_pct / 100
    cpl = max(12.0, width_pt / (size_pt * 0.52))
    wrapped = 0.0
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            wrapped += 0.5
            continue
        wrapped += max(1.0, math.ceil(len(para) / cpl))
    return max(explicit, wrapped)


def height_pct_for_text(text: str, width_pct: float, style: dict) -> float:
    sz = float(style.get("size_pt", 12))
    lead = float(style.get("leading_pt", sz * 1.22))
    lines = est_text_lines(text, width_pct, sz)
    h_pt = lines * lead * SAFETY + 2.0
    return max(MIN_TEXT_H_PCT, h_pt / PAGE_H_PT * 100)


def height_pct_for_formula(el: dict) -> float:
    style = _style(el)
    sz = float(style.get("size_pt", 15))
    lead = float(style.get("leading_pt", sz * 1.22))
    latex = el.get("latex", "") or ""
    text = el.get("text", "") or ""
    base_lines = 1.2
    if "\\frac" in latex or "\\sum" in latex or "\\left" in latex:
        base_lines = 2.4
    if text and not latex:
        w = el.get("rect", [0, 0, 90, 8])[2]
        return height_pct_for_text(text, w, style)
    h_pt = base_lines * lead * SAFETY + 4.0
    return max(MIN_TEXT_H_PCT, h_pt / PAGE_H_PT * 100)


def height_pct_for_table(el: dict) -> float:
    style = _style(el)
    sz = float(style.get("size_pt", 11))
    row_pad = float(el.get("row_padding_pt", 3))
    headers = el.get("headers") or []
    rows = el.get("rows") or []
    n = 1 + len(rows)
    row_h = (sz * 1.32 + 2 * row_pad) * SAFETY
    h_pt = n * row_h + 8
    return max(8.0, h_pt / PAGE_H_PT * 100)


def required_height_pct(el: dict) -> float | None:
    t = el.get("type")
    rect = el.get("rect")
    if not rect or len(rect) != 4:
        return None
    _, _, w, _ = rect
    if t == "text":
        return height_pct_for_text(el.get("text", "") or "", w, _style(el))
    if t == "formula":
        return height_pct_for_formula(el)
    if t == "table":
        return height_pct_for_table(el)
    return None


def is_synthesis_element(el: dict) -> bool:
    return el.get("id", "") in FOOTER_NOTE_IDS


def validate_element_height(el: dict, slide_id: str) -> list[str]:
    if slide_id == "qual30_01":
        return []
    need = required_height_pct(el)
    if need is None:
        return []
    rect = el.get("rect") or []
    if len(rect) != 4:
        return []
    h = rect[3]
    errs: list[str] = []
    if h < 2.0 and el.get("type") in ("text", "formula"):
        errs.append(f"{slide_id}/{el.get('id')}: altura nominal {h}% insuficiente")
    tol = 1.35 if (el.get("style") or {}).get("weight") == "bold" else 1.22
    if h >= 2.0 and need > h * tol:
        errs.append(
            f"{slide_id}/{el.get('id')}: altura {h:.1f}% < necessária ~{need:.1f}%"
        )
    return errs
