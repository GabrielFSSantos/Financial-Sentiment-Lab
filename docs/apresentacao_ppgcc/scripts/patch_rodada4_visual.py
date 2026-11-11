#!/usr/bin/env python3
"""Ajustes finais de layout (rodada 4). Não altera voice/transition."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "dados" / "manifesto_slides.json"


def set_rect(slide: dict, eid: str, rect: list[float]) -> None:
    for el in slide.get("elements") or []:
        if el.get("id") == eid:
            el["rect"] = rect
            return
    raise KeyError(f"{slide['id']}: elemento {eid}")


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    slides = {s["id"]: s for s in data["slides"]}
    backup = {s["id"]: s for s in data.get("backup", [])}

    s06 = slides["qual30_06"]
    set_rect(s06, "antecedentes", [5, 22, 90, 42])
    s06["elements"][0].setdefault("style", {})["size_pt"] = 10.5
    set_rect(s06, "message", [5, 66, 90, 6])

    s07 = slides["qual30_07"]
    set_rect(s07, "consolidacao", [5, 22, 58, 9])
    els = s07["elements"]
    if not any(e.get("id") == "destaque_total" for e in els):
        els.insert(
            1,
            {
                "id": "destaque_total",
                "type": "text",
                "rect": [64, 30, 30, 16],
                "text": "1.253\nnotícias canônicas",
                "style": {
                    "font": "Latin Modern Sans",
                    "size_pt": 24,
                    "leading_pt": 28,
                    "weight": "bold",
                    "color": "#C1272F",
                    "background": "#FFFFFF",
                    "align": "center",
                    "valign": "top",
                    "padding_pt": 0,
                },
            },
        )
        s07["screen"] = list(s07.get("screen", []))
        if "1.253" not in str(s07["screen"]):
            pass
    set_rect(s07, "fontes", [5, 34, 58, 40])
    set_rect(s07, "periodo", [66, 34, 28, 22])

    s05 = slides["qual30_05"]
    for el in s05["elements"]:
        if el.get("id") == "hipotese":
            el.setdefault("style", {})["size_pt"] = 16

    s23 = slides["qual30_23"]
    set_rect(s23, "correlacoes", [6, 33, 88, 26])
    for el in s23["elements"]:
        if el.get("id") == "correlacoes":
            el["x_label"] = "Spearman ρ · retorno da semana seguinte"
    set_rect(s23, "delta", [5, 62, 90, 10])
    set_rect(s23, "interpretacao", [5, 74, 90, 6])

    if "A05" in backup:
        a05 = backup["A05"]
        steps = [
            ("passo1", [5, 26, 42, 14], "1 · Unidade", "Semana com ITI, referência e retorno juntos"),
            ("passo2", [53, 26, 42, 14], "2 · Bloco", "4 semanas contíguas; respeitar lacunas"),
            ("passo3", [5, 46, 42, 14], "3 · Réplica", "Reamostrar blocos; recalcular Δρ"),
            ("passo4", [53, 46, 42, 14], "4 · Repetição", "10.000 réplicas; IC 2,5–97,5 %"),
        ]
        new_els = []
        for eid, rect, title, body in steps:
            new_els.append(
                {
                    "id": eid,
                    "type": "text",
                    "rect": rect,
                    "text": f"**{title}**\n{body}",
                    "style": {
                        "font": "Latin Modern Sans",
                        "size_pt": 11,
                        "leading_pt": 13,
                        "weight": "regular",
                        "color": "#292D32",
                        "background": "#FFFFFF",
                        "align": "left",
                        "valign": "top",
                        "padding_pt": 0,
                    },
                }
            )
        new_els.extend(
            [
                {
                    "id": "arr_12",
                    "type": "arrow",
                    "from": [48, 33],
                    "to": [53, 33],
                    "color": "#59636E",
                    "width_pt": 0.7,
                },
                {
                    "id": "arr_34",
                    "type": "arrow",
                    "from": [48, 53],
                    "to": [53, 53],
                    "color": "#59636E",
                    "width_pt": 0.7,
                },
            ]
        )
        new_els.append(
            {
                "id": "p",
                "type": "text",
                "rect": [5, 66, 90, 12],
                "text": a05["elements"][-1]["text"],
                "style": a05["elements"][-1].get("style", {}),
            }
        )
        a05["elements"] = new_els

    if "A07" in backup:
        a07 = backup["A07"]
        for el in a07["elements"]:
            if el.get("type") == "formula":
                el.setdefault("style", {})["size_pt"] = min(
                    float(el.get("style", {}).get("size_pt", 14)), 13
                )

    if "A08" in backup:
        a08 = backup["A08"]
        for i, eid in enumerate(["ref1", "ref2", "ref3", "ref4", "ref5", "ref6", "ref7", "ref8"]):
            col = 0 if i < 4 else 1
            row = i % 4
            set_rect(a08, eid, [5 + col * 47, 24 + row * 15, 43, 13])
            for el in a08["elements"]:
                if el.get("id") == eid:
                    el.setdefault("style", {})["size_pt"] = 9.5

    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: patch_rodada4_visual aplicado")


if __name__ == "__main__":
    main()
