#!/usr/bin/env python3
"""Contrato de layout v5: cabeçalho adaptativo, síntese, conteúdo e rodapé — sem voice."""

from __future__ import annotations

import json
import math
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "dados" / "manifesto_slides.json"

SYNTH_Y = 81.0
SYNTH_H = 5.5
CONTENT_BOTTOM = 79.0


def title_min_content_y(title: str) -> float:
    width_chars = 38
    lines = max(1, math.ceil(len(title) / width_chars))
    base = 20.0 if lines == 1 else 20.0 + (lines - 1) * 5.0
    return min(base, 28.0)


def clamp_rect(rect: list[float], *, min_y: float, max_bottom: float) -> list[float]:
    x, y, w, h = rect
    if y < min_y:
        h = max(1.0, h - (min_y - y))
        y = min_y
    if y + h > max_bottom:
        h = max(1.0, max_bottom - y)
    return [round(x, 2), round(y, 2), round(w, 2), round(h, 2)]


def rects_intersect(a: list[float], b: list[float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def fix_slide_02(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el["id"]
        if eid == "caso":
            el["rect"] = [12, 24, 76, 9]
        elif eid == "consumidor":
            el["rect"] = [5, 36, 42, 8]
            el["text"] = "CONSUMIDOR"
        elif eid == "efeito1":
            el["rect"] = [5, 46, 42, 22]
        elif eid == "empresa":
            el["rect"] = [53, 36, 42, 8]
        elif eid == "efeito2":
            el["rect"] = [53, 46, 42, 22]
        elif eid == "message":
            el["rect"] = [5, SYNTH_Y, 90, SYNTH_H]


def fix_a06(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el["id"]
        if eid == "legenda":
            el["rect"] = [5, 22, 90, 5]
        elif eid == "h_apoio":
            el["rect"] = [8, 28, 84, 42]
        elif eid == "residuo":
            el["rect"] = [5, 72, 55, 9]
        elif eid == "numeros":
            el["rect"] = [62, 72, 33, 10]


def normalize_slide(slide: dict, *, capa: bool = False) -> None:
    if capa:
        return
    sid = slide.get("id", "")
    if sid == "qual30_02":
        fix_slide_02(slide)
        return
    if sid == "A06":
        fix_a06(slide)
        return

    min_y = title_min_content_y(slide.get("title", ""))
    for el in slide.get("elements") or []:
        if el.get("type") == "arrow":
            continue
        if "rect" not in el:
            continue
        eid = el.get("id", "")
        if eid == "message" or eid.endswith("_msg"):
            el["rect"] = [5, SYNTH_Y, 90, SYNTH_H]
            continue
        el["rect"] = clamp_rect(el["rect"], min_y=min_y, max_bottom=CONTENT_BOTTOM)

    if sid == "qual30_05":
        for el in slide["elements"]:
            if el.get("id") == "pergunta":
                el["rect"] = [5, 25, 90, 16]
            elif el.get("id") == "contraste":
                el["rect"] = [5, 44, 90, 11]
            elif el.get("id") == "gloss":
                el["rect"] = [5, 57, 90, 8]
            elif el.get("id") == "hipotese":
                el["rect"] = [5, 68, 32, 8]
            elif el.get("id") == "objetivo":
                el["rect"] = [38, 68, 57, 8]


def check_manifest_overlaps(data: dict) -> list[str]:
    errors: list[str] = []
    for section in ("slides", "backup"):
        for slide in data.get(section, []):
            sid = slide.get("id", "?")
            els = [e for e in slide.get("elements", []) if e.get("type") != "arrow" and "rect" in e]
            for i, a in enumerate(els):
                for b in els[i + 1 :]:
                    if rects_intersect(a["rect"], b["rect"]):
                        errors.append(f"{sid}: {a.get('id')} ∩ {b.get('id')}")
    return errors


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for s in data.get("slides", []):
        normalize_slide(s, capa=s.get("layout") == "CAPA_INSTITUCIONAL")
    for s in data.get("backup", []):
        normalize_slide(s)
    overlaps = check_manifest_overlaps(data)
    if overlaps:
        print("AVISO: retângulos ainda intersectam:")
        for o in overlaps[:20]:
            print(" ", o)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: apply_layout_contract_v5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
