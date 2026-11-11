#!/usr/bin/env python3
"""Ajustes de geometria Rodada 2 — manifesto (slides P0). Não altera voice/transition."""
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

    set_rect(slides["qual30_03"], "ritmo", [8, 20, 55, 50])
    set_rect(slides["qual30_06"], "antecedentes", [5, 19, 90, 52])
    slides["qual30_06"]["elements"][0].setdefault("style", {})["size_pt"] = 11.5

    set_rect(slides["qual30_07"], "consolidacao", [5, 18, 90, 10])
    set_rect(slides["qual30_07"], "fontes", [5, 34, 63, 42])

    set_rect(slides["qual30_10"], "modelo", [5, 18, 90, 7])
    set_rect(slides["qual30_10"], "probabilidades", [8, 30, 84, 32])

    set_rect(slides["qual30_16"], "janelas", [5, 19, 90, 52])
    slides["qual30_16"]["elements"][0].setdefault("style", {})["size_pt"] = 11.5

    set_rect(slides["qual30_19"], "eixos", [5, 17, 90, 6])
    set_rect(slides["qual30_19"], "matriz", [5, 25, 60, 45])
    set_rect(slides["qual30_19"], "diag", [68, 28, 27, 14])
    set_rect(slides["qual30_19"], "neutras", [68, 46, 27, 22])
    slides["qual30_19"]["elements"][3]["text"] = (
        "35 das 67 notícias neutras da referência receberam previsão com polaridade (21+14)"
    )

    set_rect(slides["qual30_20"], "acuracia", [5, 19, 48, 32])
    set_rect(slides["qual30_20"], "f1", [56, 19, 39, 40])

    s22 = slides["qual30_22"]
    s22["elements"] = [
        el for el in s22["elements"] if el["id"] not in ("sinais", "contagens")
    ]
    s22["elements"].insert(
        1,
        {
            "id": "figura_series",
            "type": "image",
            "rect": [8, 28, 84, 50],
            "path": "assets/figura_2_soft_iti_noticias.png",
            "fit": "contain",
            "align": "center",
            "background": "#FFFFFF",
            "alt": "Séries Soft e ITI-H7 e contagens diárias de notícias",
        },
    )
    set_rect(s22, "legenda", [8, 18, 84, 7])

    set_rect(slides["qual30_23"], "painel", [5, 17, 90, 7])
    set_rect(slides["qual30_23"], "correlacoes", [6, 28, 88, 32])
    set_rect(slides["qual30_23"], "delta", [5, 66, 90, 10])

    set_rect(slides["qual30_24"], "metodo", [5, 17, 90, 7])
    set_rect(slides["qual30_24"], "ic", [8, 32, 84, 30])

    set_rect(slides["qual30_25"], "comparacao", [53, 30, 42, 8])
    set_rect(slides["qual30_25"], "ic_semanal", [53, 42, 42, 26])

    set_rect(slides["qual30_26"], "h", [8, 30, 84, 48])
    slides["qual30_26"]["elements"][1]["type"] = "image"
    slides["qual30_26"]["elements"][1].pop("plot_crop_px", None)
    slides["qual30_26"]["elements"][1].pop("source_size_px", None)

    set_rect(slides["qual30_27"], "ameacas", [5, 19, 90, 54])
    slides["qual30_27"]["elements"][0].setdefault("style", {})["size_pt"] = 11.5

    if "A06" in slides:
        a06 = slides["A06"]
        for el in a06.get("elements") or []:
            if el.get("type") == "raster_chart" and "figura_3" in el.get("path", ""):
                el["type"] = "image"
                el["rect"] = [8, 22, 84, 52]
                for k in (
                    "plot_crop_px",
                    "source_size_px",
                    "x_ticks_source_px",
                    "y_ticks_source_px",
                    "transform",
                ):
                    el.pop(k, None)

    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: patch_rodada2_geometry aplicado")


if __name__ == "__main__":
    main()
