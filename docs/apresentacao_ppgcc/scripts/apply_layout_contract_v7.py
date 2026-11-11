#!/usr/bin/env python3
"""Rodada 7 — composição profissional (piloto + harmonização global leve)."""

from __future__ import annotations

import json
from pathlib import Path

import apply_layout_contract_v6 as v6
from design_system import NOTE_RECT, SYNTHESIS_RECT, beamer_typography

MANIFEST = Path(__file__).resolve().parents[1] / "dados" / "manifesto_slides.json"


def set_rect(el: dict, rect: list[float]) -> None:
    el["rect"] = [round(x, 2) for x in rect]


def style_pt(el: dict, size: float, leading: float | None = None) -> None:
    st = el.setdefault("style", {})
    st["size_pt"] = size
    st["leading_pt"] = leading if leading is not None else round(size * 1.18, 2)


def fix_capa(slide: dict) -> None:
    typo = beamer_typography()
    for el in slide.get("elements") or []:
        eid = el.get("id")
        if eid == "ufsj":
            set_rect(el, [5, 5.5, 32, 14])
        elif eid == "dcomp":
            set_rect(el, [63, 5.5, 32, 14])
        elif eid == "tipo":
            set_rect(el, [8, 21, 84, 5])
        elif eid == "titulo_capa":
            set_rect(el, [8, 28, 84, 18])
            style_pt(el, typo["title_capa"], 28)
        elif eid == "subtitulo":
            set_rect(el, [10, 48, 80, 8])
            style_pt(el, typo["subtitle_capa"], 14.5)
        elif eid == "recorte":
            set_rect(el, [10, 57, 80, 5])
        elif eid == "autor":
            set_rect(el, [10, 70, 80, 5])
        elif eid == "orientador":
            set_rect(el, [10, 76, 80, 6])
        elif eid == "instituicao":
            set_rect(el, [10, 84, 80, 5])


def fix_corpus(slide: dict) -> None:
    v6.fix_slide_07(slide)
    for el in slide.get("elements") or []:
        if el.get("id") == "fontes":
            set_rect(el, [5, 33, 58, 38])
        elif el.get("id") == "consolidacao":
            style_pt(el, 12.5, 14.5)


def fix_meia_vida(slide: dict) -> None:
    mapping = {
        "lambda": [5, 24, 90, 9],
        "recorrencia": [5, 35, 90, 12],
        "defs": [5, 52, 48, 18],
        "pesos": [56, 52, 39, 18],
        "message": SYNTHESIS_RECT,
    }
    for el in slide.get("elements") or []:
        eid = el.get("id")
        if eid in mapping:
            set_rect(el, mapping[eid])


def fix_matriz(slide: dict) -> None:
    v6.fix_slide_19(slide)
    for el in slide.get("elements") or []:
        eid = el.get("id")
        if eid == "matriz":
            set_rect(el, [5, 29, 60, 44])
        elif eid == "diag":
            set_rect(el, [68, 32, 27, 14])
        elif eid == "neutras":
            set_rect(el, [68, 48, 27, 20])


def fix_intervalo(slide: dict) -> None:
    for el in slide.get("elements") or []:
        eid = el.get("id")
        if eid == "metodo":
            set_rect(el, [5, 24, 90, 6])
        elif eid == "ic":
            set_rect(el, [5, 32, 90, 34])
        elif eid == "p":
            set_rect(el, [5, 68, 90, 5])
        elif eid == "message":
            set_rect(el, SYNTHESIS_RECT)


def fix_cronograma(slide: dict) -> None:
    """Linha do tempo em duas fileiras (3+2) com cartões largos."""
    row1 = [("m1", "p1", 5), ("m2", "p2", 36), ("m3", "p3", 67)]
    row2 = [("m4", "p4", 14), ("m5", "p5", 52)]
    y1, y1p = 24, 33
    y2, y2p = 50, 59
    for mid, pid, x in row1:
        for el in slide.get("elements") or []:
            if el.get("id") == mid:
                set_rect(el, [x, y1, 28, 7])
            elif el.get("id") == pid:
                set_rect(el, [x, y1p, 28, 12])
                style_pt(el, 10.5, 12.2)
    for mid, pid, x in row2:
        for el in slide.get("elements") or []:
            if el.get("id") == mid:
                set_rect(el, [x, y2, 34, 7])
            elif el.get("id") == pid:
                set_rect(el, [x, y2p, 34, 11])
                style_pt(el, 10.5, 12.2)
    for el in slide.get("elements") or []:
        if el.get("id") == "linha":
            el["from"] = [8, 47]
            el["to"] = [92, 47]
        elif el.get("id") == "linha2":
            pass
        elif el.get("id") == "message":
            set_rect(el, SYNTHESIS_RECT)


def harmonize_messages(slide: dict) -> None:
    for el in slide.get("elements") or []:
        if el.get("id") == "message" and el.get("type") == "text":
            r = el.get("rect") or []
            if len(r) == 4 and r[1] >= 80 and r[3] < 4:
                set_rect(el, SYNTHESIS_RECT)


PILOT = {
    "qual30_01": fix_capa,
    "qual30_07": fix_corpus,
    "qual30_14": fix_meia_vida,
    "qual30_19": fix_matriz,
    "qual30_24": fix_intervalo,
    "qual30_28": fix_cronograma,
}


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for s in data.get("slides", []):
        v6.normalize_slide(s, capa=s.get("layout") == "CAPA_INSTITUCIONAL")
        fn = PILOT.get(s.get("id", ""))
        if fn:
            fn(s)
        elif s.get("layout") != "CAPA_INSTITUCIONAL":
            harmonize_messages(s)
    for s in data.get("backup", []):
        v6.normalize_slide(s)
        harmonize_messages(s)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: apply_layout_contract_v7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
