#!/usr/bin/env python3
"""Contrato v6: corrige caixas colapsadas (1%) sem recomprimir conteúdo."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "dados" / "manifesto_slides.json"

# Zona de síntese acima do rodapé bibliográfico (~79%)
SYNTHESIS_RECT = [5, 73.5, 90, 5.5]
NOTE_RECT = [5, 73.0, 90, 6.0]


def set_rect(el: dict, rect: list[float]) -> None:
    el["rect"] = [round(x, 2) for x in rect]


def fix_slide_02(slide: dict) -> None:
    mapping = {
        "caso": [12, 24, 76, 9],
        "consumidor": [5, 36, 42, 8],
        "efeito1": [5, 46, 42, 22],
        "empresa": [53, 36, 42, 8],
        "efeito2": [53, 46, 42, 22],
        "message": SYNTHESIS_RECT,
    }
    for el in slide["elements"]:
        if el.get("id") in mapping:
            if el["id"] == "consumidor":
                el["text"] = "CONSUMIDOR"
            set_rect(el, mapping[el["id"]])


def fix_slide_04(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid == "lacuna":
            set_rect(el, [5, 64, 90, 8])
        elif eid in ("alvot", "classt", "tempot"):
            x, y, w, h = el["rect"]
            set_rect(el, [x, y, w, max(h, 10)])
        elif eid == "message":
            set_rect(el, SYNTHESIS_RECT)


def fix_slide_05(slide: dict) -> None:
    mapping = {
        "pergunta": [5, 24, 90, 17],
        "contraste": [5, 43, 90, 12],
        "gloss": [5, 57, 90, 8],
        "hipotese": [5, 66, 32, 9],
        "objetivo": [38, 66, 57, 9],
        "message": SYNTHESIS_RECT,
    }
    for el in slide["elements"]:
        if el.get("id") in mapping:
            set_rect(el, mapping[el["id"]])


def fix_slide_06(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid == "antecedentes":
            set_rect(el, [5, 22, 90, 44])
            el["row_padding_pt"] = 1.0
            el.setdefault("style", {})["size_pt"] = 9.0
            el["style"]["leading_pt"] = 10.5
        elif eid == "message":
            set_rect(el, SYNTHESIS_RECT)


def fix_slide_07(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid == "destaque_total":
            el["id"] = "destaque_num"
            set_rect(el, [66, 28, 28, 8])
            el["text"] = "1.253"
            el.setdefault("style", {})["size_pt"] = 28
            el["style"]["leading_pt"] = 32
        elif eid == "consolidacao":
            set_rect(el, [5, 23, 58, 8])
        elif eid == "fontes":
            set_rect(el, [5, 34, 58, 36])
        elif eid == "periodo":
            set_rect(el, [66, 43, 28, 27])
        elif eid == "message":
            set_rect(el, SYNTHESIS_RECT)
    if not any(e.get("id") == "destaque_legenda" for e in slide["elements"]):
        slide["elements"].insert(
            2,
            {
                "id": "destaque_legenda",
                "type": "text",
                "rect": [66, 36.5, 28, 5],
                "text": "notícias canônicas",
                "style": {
                    "font": "Latin Modern Sans",
                    "size_pt": 11,
                    "leading_pt": 12.5,
                    "weight": "regular",
                    "color": "#59636E",
                    "background": "#FFFFFF",
                    "align": "center",
                    "valign": "top",
                    "padding_pt": 0,
                },
            },
        )


def fix_slide_17(slide: dict) -> None:
    mapping = {
        "retorno": [5, 58, 48, 11],
        "feriado": [58, 57, 37, 14],
        "legenda": NOTE_RECT,
    }
    for el in slide["elements"]:
        if el.get("id") in mapping:
            set_rect(el, mapping[el["id"]])


def fix_slide_19(slide: dict) -> None:
    mapping = {
        "eixos": [5, 22, 90, 7],
        "neutras": [66, 48, 29, 22],
        "message": SYNTHESIS_RECT,
    }
    for el in slide["elements"]:
        if el.get("id") in mapping:
            set_rect(el, mapping[el["id"]])


def fix_slide_22(slide: dict) -> None:
    mapping = {
        "figura_series": [8, 28, 84, 44],
        "aviso": NOTE_RECT,
    }
    for el in slide["elements"]:
        if el.get("id") in mapping:
            set_rect(el, mapping[el["id"]])


def fix_slide_28(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id", "")
        if eid.startswith("p") and len(eid) == 2:
            x, y, w, h = el["rect"]
            set_rect(el, [x, y, w, max(h, 11)])
        elif eid == "message":
            set_rect(el, SYNTHESIS_RECT)


def fix_slide_29(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid == "fim":
            set_rect(el, NOTE_RECT)
        elif eid in ("feitot", "evidenciat"):
            x, y, w, h = el["rect"]
            set_rect(el, [x, y, w, max(h, 9)])
        elif eid == "proximot":
            set_rect(el, [33, 62, 62, 9])


def fix_a02(slide: dict) -> None:
    for el in slide["elements"]:
        if el.get("id") == "def":
            set_rect(el, [5, 70, 90, 8])


def fix_a03(slide: dict) -> None:
    for el in slide["elements"]:
        if el.get("id") == "sens":
            set_rect(el, [5, 24, 90, 46])
        elif el.get("id") == "limite":
            set_rect(el, NOTE_RECT)


def fix_a04(slide: dict) -> None:
    for el in slide["elements"]:
        if el.get("id") == "composicao":
            set_rect(el, [5, 72, 90, 7])


def fix_a05(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid and eid.startswith("passo"):
            x, y, w, h = el["rect"]
            set_rect(el, [x, y, w, max(h, 16)])
        elif eid == "p":
            set_rect(el, NOTE_RECT)


def fix_a06(slide: dict) -> None:
    mapping = {
        "legenda": [5, 22, 90, 5],
        "h_apoio": [8, 28, 84, 40],
        "residuo": [5, 70, 55, 10],
        "numeros": [62, 70, 33, 10],
    }
    for el in slide["elements"]:
        if el.get("id") in mapping:
            set_rect(el, mapping[el["id"]])


def fix_a07(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid == "defs":
            set_rect(el, [5, 58, 90, 13])
        elif eid == "futuro":
            set_rect(el, NOTE_RECT)


def fix_a08(slide: dict) -> None:
    for el in slide["elements"]:
        eid = el.get("id")
        if eid == "ref4":
            set_rect(el, [5, 67.5, 43, 5.5])
        elif eid == "ref8":
            set_rect(el, [52, 67.5, 43, 5.5])
        elif eid == "nota_ref":
            set_rect(el, [5, 73.5, 90, 5.0])


COLLAPSED_FIX = {
    "legenda": NOTE_RECT,
    "aviso": NOTE_RECT,
    "fim": NOTE_RECT,
    "limite": NOTE_RECT,
    "futuro": NOTE_RECT,
    "nota_ref": [5, 73, 90, 5.5],
    "message": SYNTHESIS_RECT,
}


def repair_collapsed_boxes(slide: dict) -> None:
    for el in slide.get("elements") or []:
        rect = el.get("rect")
        if not rect or len(rect) != 4:
            continue
        if rect[3] > 1.5:
            continue
        eid = el.get("id", "")
        if eid in COLLAPSED_FIX:
            set_rect(el, COLLAPSED_FIX[eid])


FIXERS = {
    "qual30_02": fix_slide_02,
    "qual30_04": fix_slide_04,
    "qual30_05": fix_slide_05,
    "qual30_06": fix_slide_06,
    "qual30_07": fix_slide_07,
    "qual30_17": fix_slide_17,
    "qual30_19": fix_slide_19,
    "qual30_22": fix_slide_22,
    "qual30_28": fix_slide_28,
    "qual30_29": fix_slide_29,
    "A02": fix_a02,
    "A03": fix_a03,
    "A04": fix_a04,
    "A05": fix_a05,
    "A06": fix_a06,
    "A07": fix_a07,
    "A08": fix_a08,
}


def normalize_slide(slide: dict, *, capa: bool = False) -> None:
    if capa:
        return
    fn = FIXERS.get(slide.get("id", ""))
    if fn:
        fn(slide)
    repair_collapsed_boxes(slide)


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for s in data.get("slides", []):
        normalize_slide(s, capa=s.get("layout") == "CAPA_INSTITUCIONAL")
    for s in data.get("backup", []):
        normalize_slide(s)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: apply_layout_contract_v6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
