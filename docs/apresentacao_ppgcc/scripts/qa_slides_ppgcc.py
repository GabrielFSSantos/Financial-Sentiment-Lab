#!/usr/bin/env python3
"""QA visual de PDF de apresentações; gera PNGs, contatos e alertas heurísticos."""

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

RULE_Y_FRAC = 0.925
RULE_BAND_PT = 1.25
BIBLIO_Y0_FRAC = 0.82
BIBLIO_Y1_FRAC = 0.905
SYNTH_Y0_FRAC = 0.76
SYNTH_Y1_FRAC = 0.82
INST_Y0_FRAC = 0.935

PLACEHOLDER_PAT = re.compile(
    r"Asset ausente|Pillow não|raster indisponível|não instalado|\*\*",
    re.I,
)

CRITICAL = {
    "FORA_DA_PAGINA",
    "PLACEHOLDER",
    "FIGURA_AUSENTE",
    "INVASAO_TITULO",
    "LINHA_ATRAVESSA_TEXTO",
    "TITULO_CONTEUDO_COLISAO",
    "MANIFEST_OVERLAP",
}

HIGH = {
    "SINTESE_BIBLIO_COLISAO",
    "GEOM_ESTOURO",
    "POSSIVEL_SOBREPOSICAO",
    "FONTE_PEQUENA",
}

FIGURE_SLIDES = {22, 26, 35}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def load_slide_ids() -> list[str]:
    data = load_manifest()
    return [s["id"] for s in data.get("slides", [])] + [s["id"] for s in data.get("backup", [])]


def manifest_overlap_warnings(page_no: int) -> list[tuple[str, str, str]]:
    data = load_manifest()
    ids = load_slide_ids()
    if page_no < 1 or page_no > len(ids):
        return []
    sid = ids[page_no - 1]
    slide = None
    for sec in ("slides", "backup"):
        slide = next((s for s in data.get(sec, []) if s.get("id") == sid), None)
        if slide:
            break
    if not slide:
        return []
    warns: list[tuple[str, str, str]] = []
    els = [e for e in slide.get("elements", []) if e.get("type") != "arrow" and e.get("rect")]
    for i, a in enumerate(els):
        for b in els[i + 1 :]:
            ax, ay, aw, ah = a["rect"]
            bx, by, bw, bh = b["rect"]
            if ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by:
                warns.append(
                    (
                        "MANIFEST_OVERLAP",
                        f"{a.get('id')} ∩ {b.get('id')}",
                        "CRÍTICO",
                    )
                )
    return warns


def manifest_geometry_warnings(page_no: int) -> list[tuple[str, str, str]]:
    if not GEOM.is_file():
        return []
    ids = load_slide_ids()
    if page_no < 1 or page_no > len(ids):
        return []
    sid = ids[page_no - 1]
    geom = json.loads(GEOM.read_text(encoding="utf-8"))
    warns: list[tuple[str, str, str]] = []
    for g in geom:
        if g.get("slide_id") != sid:
            continue
        rect = g.get("rect") or []
        if len(rect) != 4:
            continue
        _x, y, _w, h = rect
        if g.get("type") in ("chart", "table", "image", "raster_chart") and y + h > 80:
            warns.append(("GEOM_ESTOURO", f"{g.get('element_id')}: y+h={y+h:.1f}%", "ALTO"))
    return warns


def page_frac_y(box: fitz.Rect, page_h: float) -> tuple[float, float]:
    return box.y0 / page_h, box.y1 / page_h


def _institutional_skip(txt: str) -> bool:
    t = txt.strip()
    if not t:
        return True
    if "UFSJ" in t or "PPGCC" in t or "Ciência" in t or "Computação" in t:
        return True
    if t in ("da", "·", "/"):
        return True
    if re.fullmatch(r"\d{2}", t) or re.fullmatch(r"A\d{2}", t):
        return True
    if re.fullmatch(r"\d{1,2}", t):
        return True
    if re.fullmatch(r"[A\d/ ]+", t) and "/" in t:
        return True
    return False


def footer_and_title_checks(
    page_no: int, spans: list[tuple[int, fitz.Rect, str, float]], page_h: float
) -> list[tuple[str, str, str]]:
    if page_no == 1:
        return []
    warns: list[tuple[str, str, str]] = []
    rule_y = RULE_Y_FRAC * page_h
    band = RULE_BAND_PT
    for _bid, box, txt, sz in spans:
        if _institutional_skip(txt):
            continue
        if box.y0 / page_h >= INST_Y0_FRAC:
            continue
        if sz < 8.5:
            continue
        mid = 0.5 * (box.y0 + box.y1)
        if abs(mid - rule_y) <= band and len(txt.strip()) > 1:
            warns.append(("LINHA_ATRAVESSA_TEXTO", f"{sz:.1f}pt: {txt[:50]}", "CRÍTICO"))
        elif box.y0 < rule_y + band and box.y1 > rule_y - band and len(txt.strip()) > 2:
            overlap = min(box.y1, rule_y + band) - max(box.y0, rule_y - band)
            if overlap > band * 0.35:
                warns.append(("LINHA_ATRAVESSA_TEXTO", f"{sz:.1f}pt: {txt[:50]}", "CRÍTICO"))

    title_boxes = [
        box
        for _b, box, txt, sz in spans
        if sz >= 16 and box.y0 < page_h * 0.12 and not _institutional_skip(txt)
    ]
    content_boxes = [
        box
        for _b, box, txt, sz in spans
        if 0.19 < box.y0 / page_h < 0.78 and sz >= 9 and len(txt.strip()) > 2
    ]
    if title_boxes and content_boxes:
        t_bot = max(b.y1 for b in title_boxes)
        c_top = min(b.y0 for b in content_boxes)
        gap = c_top - t_bot
        if gap < page_h * 0.012:
            warns.append(("TITULO_CONTEUDO_COLISAO", f"gap={gap:.1f}pt", "CRÍTICO"))

    def line_union(subset) -> list[tuple[fitz.Rect, str]]:
        by_line: dict[tuple[int, int], list[tuple[fitz.Rect, str]]] = {}
        for bid, box, txt, sz in subset:
            key = (bid, int(box.y0 / 2))
            by_line.setdefault(key, []).append((box, txt))
        out: list[tuple[fitz.Rect, str]] = []
        for items in by_line.values():
            ub = fitz.Rect(items[0][0])
            parts = []
            for box, txt in items:
                ub |= box
                parts.append(txt)
            out.append((ub, " ".join(parts).strip()))
        return out

    biblio_sp = [
        (_b, box, txt, sz)
        for _b, box, txt, sz in spans
        if BIBLIO_Y0_FRAC * page_h <= box.y0 <= BIBLIO_Y1_FRAC * page_h and sz < 10
    ]
    synth_sp = [
        (_b, box, txt, sz)
        for _b, box, txt, sz in spans
        if SYNTH_Y0_FRAC * page_h <= box.y0 <= SYNTH_Y1_FRAC * page_h and sz >= 9
    ]
    for sb, st in line_union(synth_sp):
        for bb, bt in line_union(biblio_sp):
            if sb & bb and not (sb & bb).is_empty and st != bt:
                warns.append(("SINTESE_BIBLIO_COLISAO", f"{st[:30]} / {bt[:30]}", "ALTO"))
    return warns


def inspect(page, number: int) -> list[tuple[str, str, str]]:
    rect = page.rect
    w, h = rect.width, rect.height
    warns: list[tuple[str, str, str]] = []
    spans: list[tuple[int, fitz.Rect, str, float]] = []
    image_areas: list[float] = []

    for bi, block in enumerate(page.get_text("dict")["blocks"]):
        btype = block.get("type")
        if btype == 1:
            image_areas.append(fitz.Rect(block["bbox"]).get_area())
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
                    warns.append(("PLACEHOLDER", txt[:80], "CRÍTICO"))
                if box.x0 < -2 or box.y0 < -2 or box.x1 > w + 2 or box.y1 > h + 2:
                    warns.append(("FORA_DA_PAGINA", txt[:80], "CRÍTICO"))
                y0f, _y1f = page_frac_y(box, h)
                if (
                    number > 1
                    and 0.10 < y0f < 0.19
                    and 8.5 <= span["size"] < 16.5
                ):
                    warns.append(("INVASAO_TITULO", f"{span['size']:.1f}pt: {txt[:60]}", "CRÍTICO"))
                if 0.22 < y0f < 0.88 and span["size"] < 7.5 and len(txt) > 2:
                    warns.append(("FONTE_PEQUENA", f'{span["size"]:.1f}pt: {txt[:70]}', "ALTO"))

    if number in FIGURE_SLIDES and not image_areas:
        warns.append(("FIGURA_AUSENTE", "sem imagem", "CRÍTICO"))
    elif number in FIGURE_SLIDES and max(image_areas, default=0) < (w * h) * 0.04:
        warns.append(("FIGURA_AUSENTE", "área insuficiente", "CRÍTICO"))

    seen: set[tuple[str, str]] = set()
    for i, (bid, a, at, _fs) in enumerate(spans):
        for bid2, b, bt, _fs2 in spans[i + 1 :]:
            if bid == bid2:
                continue
            ay0 = a.y0 / h
            if ay0 > 0.9 or b.y0 / h > 0.9:
                continue
            overlap = a & b
            if not overlap or overlap.is_empty:
                continue
            frac = overlap.get_area() / min(a.get_area(), b.get_area())
            if frac > 0.45 and len(at) > 2 and len(bt) > 2:
                key = (at[:24], bt[:24])
                if key not in seen:
                    warns.append(("POSSIVEL_SOBREPOSICAO", f"{at[:38]!r} / {bt[:38]!r}", "ALTO"))
                    seen.add(key)

    warns.extend(footer_and_title_checks(number, spans, h))
    warns.extend(manifest_geometry_warnings(number))
    warns.extend(manifest_overlap_warnings(number))
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


def write_report(out: Path, rows: list[tuple[int, str, str, str]]) -> None:
    crit = [r for r in rows if r[2] in CRITICAL or r[3] == "CRÍTICO"]
    lines = [
        "# Relatório QA visual (v5)",
        "",
        f"- Alertas: {len(rows)}",
        f"- Críticos: {len(crit)}",
        "",
    ]
    if crit:
        lines.append("## Críticos")
        for slide, code, detail, _sev in crit:
            lines.append(f"- Slide {slide}: **{code}** — {detail}")
        lines.append("")
    by_slide: dict[int, list[str]] = {}
    for slide, code, detail, sev in rows:
        by_slide.setdefault(slide, []).append(f"[{sev}] {code}: {detail}")
    lines.append("## Por slide")
    for slide in sorted(by_slide):
        lines.append(f"### Slide {slide}")
        for item in by_slide[slide]:
            lines.append(f"- {item}")
    (out / "relatorio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "colisoes.md").write_text(
        "\n".join(f"slide {s}: {c} {d}" for s, c, d, _ in rows if c in CRITICAL or c in HIGH)
        + "\n",
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default="build/qa")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    pages_dir = out / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)
    rows: list[tuple[int, str, str, str]] = []
    images: list[Path] = []
    for ix, page in enumerate(doc):
        filename = pages_dir / f"slide_{ix + 1:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(args.dpi / 72, args.dpi / 72), alpha=False).save(filename)
        images.append(filename)
        for code, detail, sev in inspect(page, ix + 1):
            rows.append((ix + 1, code, detail, sev))
    with (out / "alertas.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["slide", "alerta", "detalhe", "severidade"])
        writer.writerows(rows)
    for chunk in range(0, len(images), 12):
        contact_sheet(images[chunk : chunk + 12], out / f"contato_{chunk // 12 + 1:02d}.jpg")
    write_report(out, rows)
    crit_n = sum(1 for _s, c, _d, sev in rows if c in CRITICAL or sev == "CRÍTICO")
    print(f"OK: {len(doc)} slides, {len(rows)} alertas ({crit_n} críticos).")
    print(f"Relatório: {out / 'relatorio.md'}")
    if args.strict and crit_n:
        print(f"FALHA strict: {crit_n} críticos", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
