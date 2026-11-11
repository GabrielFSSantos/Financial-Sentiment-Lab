#!/usr/bin/env python3
"""Ajustes de geometria Rodada 3 — visual QA. Não altera voice/transition."""

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

    set_rect(slides["qual30_03"], "ritmo", [8, 22, 58, 48])
    set_rect(slides["qual30_07"], "consolidacao", [5, 22, 90, 9])
    set_rect(slides["qual30_07"], "fontes", [5, 34, 62, 38])
    set_rect(slides["qual30_07"], "periodo", [70, 34, 25, 22])
    set_rect(slides["qual30_10"], "modelo", [5, 22, 90, 7])
    set_rect(slides["qual30_10"], "probabilidades", [8, 32, 84, 30])

    set_rect(slides["qual30_19"], "eixos", [5, 22, 90, 6])
    set_rect(slides["qual30_19"], "matriz", [5, 30, 58, 42])
    set_rect(slides["qual30_19"], "diag", [66, 32, 29, 14])
    set_rect(slides["qual30_19"], "neutras", [66, 50, 29, 22])

    set_rect(slides["qual30_20"], "acuracia", [5, 22, 46, 35])
    set_rect(slides["qual30_20"], "f1", [54, 22, 41, 38])
    set_rect(slides["qual30_20"], "macro", [5, 62, 90, 12])

    s22 = slides["qual30_22"]
    for el in s22.get("elements") or []:
        if el.get("id") == "figura_series" and el.get("type") != "image":
            el["type"] = "image"
            el["rect"] = [8, 26, 84, 52]
            el["path"] = "assets/figura_2_soft_iti_noticias.png"
            for k in ("plot_crop_px", "source_size_px", "x_ticks_source_px", "y_ticks_source_px"):
                el.pop(k, None)
    set_rect(s22, "legenda", [8, 22, 84, 6])

    set_rect(slides["qual30_23"], "painel", [5, 22, 90, 7])
    set_rect(slides["qual30_23"], "correlacoes", [6, 32, 88, 30])
    set_rect(slides["qual30_23"], "delta", [5, 66, 90, 10])

    set_rect(slides["qual30_24"], "metodo", [5, 22, 90, 7])
    set_rect(slides["qual30_24"], "ic", [8, 32, 84, 28])

    set_rect(slides["qual30_25"], "contagem", [5, 22, 48, 22])
    set_rect(slides["qual30_25"], "comparacao", [55, 22, 40, 10])
    set_rect(slides["qual30_25"], "ic_semanal", [55, 36, 40, 28])

    s26 = slides["qual30_26"]
    for el in s26.get("elements") or []:
        if el.get("id") == "h" and el.get("type") == "raster_chart":
            el["type"] = "image"
            el["path"] = "assets/figura_3_meias_vidas.png"
            el["rect"] = [8, 26, 84, 50]
            for k in ("plot_crop_px", "source_size_px", "x_ticks_source_px", "y_ticks_source_px", "transform"):
                el.pop(k, None)
    set_rect(s26, "legenda", [5, 22, 90, 6])

    if "A06" in backup:
        a06 = backup["A06"]
        set_rect(a06, "h_apoio", [8, 24, 84, 50])
        for el in a06.get("elements") or []:
            if el.get("type") == "raster_chart" or "figura_3" in el.get("path", ""):
                el["type"] = "image"
                el["rect"] = [8, 24, 84, 50]
                el["path"] = el.get("path", "assets/figura_3_meias_vidas.png").replace(
                    "build/", "assets/"
                )
                for k in (
                    "plot_crop_px",
                    "source_size_px",
                    "x_ticks_source_px",
                    "y_ticks_source_px",
                    "transform",
                ):
                    el.pop(k, None)

    if "A07" in backup:
        a07 = backup["A07"]
        set_rect(a07, "fixos", [5, 24, 90, 8])
        set_rect(a07, "uniforme", [5, 36, 42, 20])
        set_rect(a07, "exponencial", [53, 36, 42, 20])
        set_rect(a07, "defs", [5, 60, 90, 16])

    if "A01" in backup:
        set_rect(backup["A01"], "ficha", [5, 24, 90, 56])

    slides["qual30_02"]["elements"][1]["rect"] = [5, 26, 42, 38]
    slides["qual30_02"]["elements"][3]["rect"] = [53, 26, 42, 38]
    slides["qual30_02"]["elements"][0]["rect"] = [28, 38, 44, 14]

    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: patch_rodada3_visual aplicado")


if __name__ == "__main__":
    main()
