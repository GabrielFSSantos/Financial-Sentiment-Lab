#!/usr/bin/env python3
"""QA visual de PDF de apresentações; gera PNGs, contatos e alertas heurísticos.
Uso: python scripts/qa_slides_ppgcc.py output/apresentacao_ppgcc.pdf --out build/qa
Dependências: pymupdf, pillow. As advertências precisam de revisão visual.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
GEOM = ROOT / "build" / "layout_geometry.json"

ZONE_TITLE_BOTTOM_FRAC = 18.0 / 100.0
ZONE_FOOTER_TOP_FRAC = 93.0 / 100.0
PLACEHOLDER_PAT = re.compile(
    r"Asset ausente|Pillow não|raster indisponível|não instalado",
    re.I,
)
CRITICAL = {
    "FORA_DA_PAGINA",
    "PLACEHOLDER",
    "FIGURA_AUSENTE",
    "INVASAO_TITULO",
    "ROTEIRO_PLACEHOLDER",
}

FIGURE_SLIDES = {22, 26, 35}


def page_frac_y(box: fitz.Rect, page_h: float) -> tuple[float, float]:
    return box.y0 / page_h, box.y1 / page_h


def inspect(page, number: int, *, strict: bool) -> list[tuple[str, str]]:
    rect = page.rect
    w, h = rect.width, rect.height
    warns: list[tuple[str, str]] = []
    spans: list[tuple[int, fitz.Rect, str, float]] = []
    image_areas: list[float] = []

    for bi, block in enumerate(page.get_text("dict")["blocks"]):
        btype = block.get("type")
        if btype == 1:
            bbox = fitz.Rect(block["bbox"])
            image_areas.append(bbox.get_area())
        if btype != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = span.get("text", "").strip()
                if not txt:
                    continue
                box = fitz.Rect(span["bbox"])
                spans.append((bi, box, txt, span["size"]))
                if PLACEHOLDER_PAT.search(txt):
                    warns.append(("PLACEHOLDER", txt[:80]))
                if box.x0 < -2 or box.y0 < -2 or box.x1 > w + 2 or box.y1 > h + 2:
                    warns.append(("FORA_DA_PAGINA", txt[:80]))
                y0f, _y1f = page_frac_y(box, h)
                # Corpo ou gráficos no miolo da faixa do título (abaixo do bloco institucional ~8%)
                if (
                    number > 1
                    and 0.085 < y0f < ZONE_TITLE_BOTTOM_FRAC
                    and 8.5 <= span["size"] < 16.5
                    and "UFSJ" not in txt
                ):
                    warns.append(("INVASAO_TITULO", f"{span['size']:.1f}pt: {txt[:60]}"))
                if y0f > 0.22 and y0f < 0.88 and span["size"] < 7.5 and len(txt) > 2:
                    warns.append(("FONTE_PEQUENA", f'{span["size"]:.1f}pt: {txt[:70]}'))
                if y0f > ZONE_FOOTER_TOP_FRAC and span["size"] < 6.8 and len(txt) > 1:
                    if "UFSJ" not in txt and "/" not in txt:
                        warns.append(("FONTE_PEQUENA_RODAPE", f'{span["size"]:.1f}pt: {txt[:60]}'))

    if number in FIGURE_SLIDES and not image_areas:
        warns.append(("FIGURA_AUSENTE", "nenhum bloco de imagem detectado"))
    elif number in FIGURE_SLIDES and max(image_areas, default=0) < (w * h) * 0.04:
        warns.append(("FIGURA_AUSENTE", "área de imagem insuficiente"))

    seen: set[tuple[str, str]] = set()
    for i, (bid, a, at, _fs) in enumerate(spans):
        for bid2, b, bt, _fs2 in spans[i + 1 :]:
            if bid == bid2:
                continue
            ay0, ay1 = page_frac_y(a, h)
            if ay0 > ZONE_FOOTER_TOP_FRAC or page_frac_y(b, h)[0] > ZONE_FOOTER_TOP_FRAC:
                continue
            overlap = a & b
            if not overlap or overlap.is_empty or a.get_area() <= 0 or b.get_area() <= 0:
                continue
            frac = overlap.get_area() / min(a.get_area(), b.get_area())
            if frac > 0.42 and len(at) > 2 and len(bt) > 2:
                key = (at[:24], bt[:24])
                if key not in seen:
                    warns.append(("POSSIVEL_SOBREPOSICAO", f"{at[:38]!r} / {bt[:38]!r}"))
                    seen.add(key)
    if len(spans) > 115:
        warns.append(("SLIDE_DENSO", f"{len(spans)} trechos de texto"))
    if len(spans) < 4 and number not in (1, 29) and not image_areas:
        warns.append(("SLIDE_VAZIO", "pouco conteúdo detectado"))
    return warns


def contact_sheet(files, target, cols=3, tile_width=600):
    tw, th = tile_width, round(tile_width * 9 / 16)
    gap = 12
    label_h = 24
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * (tw + gap) + gap, rows * (th + label_h + gap) + gap), (230, 233, 238))
    draw = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        with Image.open(f) as raw:
            img = ImageOps.contain(raw.convert("RGB"), (tw, th))
        x = gap + (i % cols) * (tw + gap)
        y = gap + (i // cols) * (th + label_h + gap)
        sheet.paste(img, (x, y + label_h))
        draw.text((x + 3, y + 4), f.stem, fill=(28, 30, 32))
    sheet.save(target, quality=86)


def write_report(out: Path, rows: list[tuple[int, str, str]], strict: bool) -> None:
    crit = [r for r in rows if r[1] in CRITICAL]
    lines = [
        "# Relatório QA visual",
        "",
        f"- Total de alertas: {len(rows)}",
        f"- Críticos: {len(crit)}",
        f"- Modo strict: {strict}",
        "",
    ]
    if crit:
        lines.append("## Slides para inspeção manual (críticos)")
        for slide, code, detail in crit:
            lines.append(f"- Slide {slide}: **{code}** — {detail}")
        lines.append("")
    by_slide: dict[int, list[str]] = {}
    for slide, code, detail in rows:
        by_slide.setdefault(slide, []).append(f"{code}: {detail}")
    lines.append("## Por slide")
    for slide in sorted(by_slide):
        lines.append(f"### Slide {slide}")
        for item in by_slide[slide]:
            lines.append(f"- {item}")
    (out / "relatorio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default="build/qa")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--strict", action="store_true", help="Falha se alertas críticos")
    args = ap.parse_args()
    out = Path(args.out)
    pages_dir = out / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)
    rows: list[tuple[int, str, str]] = []
    images: list[Path] = []
    for ix, page in enumerate(doc):
        filename = pages_dir / f"slide_{ix + 1:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(args.dpi / 72, args.dpi / 72), alpha=False).save(filename)
        images.append(filename)
        for code, detail in inspect(page, ix + 1, strict=args.strict):
            rows.append((ix + 1, code, detail))
    with (out / "alertas.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["slide", "alerta", "detalhe"])
        writer.writerows(rows)
    for chunk in range(0, len(images), 12):
        contact_sheet(images[chunk : chunk + 12], out / f"contato_{chunk // 12 + 1:02d}.jpg")
    write_report(out, rows, args.strict)
    crit_n = sum(1 for _s, c, _d in rows if c in CRITICAL)
    print(f"OK: {len(doc)} slides, {len(rows)} alertas ({crit_n} críticos).")
    print(f"Relatório: {out / 'relatorio.md'}")
    if args.strict and crit_n:
        print(f"FALHA strict: {crit_n} alertas críticos", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
