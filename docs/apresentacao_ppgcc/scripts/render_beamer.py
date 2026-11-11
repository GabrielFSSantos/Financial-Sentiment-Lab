#!/usr/bin/env python3
"""Gera build/slides_content.tex a partir do manifesto v4 (elements tipados)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
FATOS_PATH = ROOT / "dados" / "fatos_cientificos.json"
OUT = ROOT / "build" / "slides_content.tex"
GEOM_OUT = ROOT / "build" / "layout_geometry.json"
RASTER_DIR = ROOT / "build" / "raster_cache"
ASSETS = ROOT / "assets"

LAYOUTS = {
    "CAPA_INSTITUCIONAL",
    "COMPARACAO_ALVO",
    "BARRAS_DIDATICAS",
    "FLUXO_TRES_CAMADAS",
    "PERGUNTA_CONTRASTE",
    "TABELA_LITERATURA",
    "CORPUS_BARRAS_SEPARADAS",
    "BIFURCACAO_AVALIACOES",
    "RECORTE_ANOTADO",
    "PROBABILIDADES_BARRA",
    "FORMULA_ESCORE",
    "FORMULA_MEDIA",
    "MEMORIA_DIAGRAMA",
    "FORMULA_MEMORIA",
    "CONTA_DUAS_PARCELAS",
    "TABELA_JANELAS",
    "LINHA_TEMPO_MERCADO",
    "AMOSTRA_CONTEXTO",
    "MATRIZ_REAL",
    "METRICAS_COMPARADAS",
    "COMPARACAO_ENTRADAS",
    "SERIES_DOIS_PAINEIS",
    "CORRELACOES_PONTOS",
    "INTERVALO_HORIZONTAL",
    "BASELINE_CONTAGEM_INTERVALO",
    "SERIE_SENSIBILIDADE",
    "TABELA_AMEACAS",
    "CRONOGRAMA_CINCO",
    "FECHAMENTO_TRES",
    "APOIO_FICHA",
    "APOIO_METRICAS",
    "APOIO_SENSIBILIDADES",
    "APOIO_GRUPOS",
    "APOIO_BOOTSTRAP",
    "APOIO_MEIA_VIDA",
    "APOIO_CONTROLE",
    "APOIO_REFERENCIAS",
}

MATH_TOKENS: list[tuple[str, str]] = [
    ("ITI_(d−1)", r"ITI_{d-1}"),
    ("ITI_d", r"ITI_d"),
    ("X_d", r"X_d"),
    ("N_d", r"\mathcal N_d"),
    ("n_d", r"n_d"),
    ("λ_H", r"\lambda_H"),
    ("λ₇", r"\lambda_7"),
    ("pᵢ⁺", r"p_i^+"),
    ("pᵢ⁻", r"p_i^-"),
    ("pᵢ⁰", r"p_i^0"),
    ("p⁺", r"p^+"),
    ("p⁻", r"p^-"),
    ("p⁰", r"p^0"),
    ("sᵢ", r"s_i"),
    ("P_(w+1)", r"P_{w+1}"),
    ("P_w", r"P_w"),
    ("R¹", r"R^{(1)}"),
    ("U_w", r"U_w"),
    ("E_w", r"E_w"),
    ("d_w", r"d_w"),
    ("Δρ", r"\Delta\rho"),
    ("ρ", r"\rho"),
    ("κ", r"\kappa"),
    ("λ", r"\lambda"),
    ("→", r"\rightarrow"),
    ("×", r"\times"),
    ("≈", r"\approx"),
    ("≠", r"\neq"),
    ("−", "-"),
    ("·", r"\cdot"),
]

_ESCAPE_ORDER = "\\&%#_{}~^"


def load_fatos() -> dict:
    if FATOS_PATH.is_file():
        return json.loads(FATOS_PATH.read_text(encoding="utf-8")).get("ancoras", {})
    return {}


def normalize_text(text: str) -> str:
    text = (
        text.replace("\u2212", "-")
        .replace("−", "-")
        .replace("\u00a0", " ")
    )
    text = re.sub(r"\\{3,}", r"\\\\", text)
    return text


def escape_plain(text: str) -> str:
    """Escape LaTeX specials em passagem única."""
    if not text:
        return ""
    text = normalize_text(text)
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            out.append(r"\textbackslash{}")
            i += 1
            continue
        if ch == "&":
            out.append(r"\&")
        elif ch == "%":
            out.append(r"\%")
        elif ch == "#":
            out.append(r"\#")
        elif ch == "_":
            out.append(r"\_")
        elif ch == "{":
            out.append(r"\{")
        elif ch == "}":
            out.append(r"\}")
        elif ch == "~":
            out.append(r"\textasciitilde{}")
        elif ch == "^":
            out.append(r"\textasciicircum{}")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def format_mixed_text(text: str) -> str:
    """Texto com tokens matemáticos explícitos."""
    if not text:
        return ""
    text = normalize_text(text)
    parts: list[str] = []
    i = 0
    while i < len(text):
        matched = None
        for tok, latex in MATH_TOKENS:
            if text.startswith(tok, i):
                matched = (tok, latex)
                break
        if matched:
            tok, latex = matched
            parts.append(f"\\({latex}\\)")
            i += len(tok)
            continue
        if text[i] == "\n":
            parts.append(r"\\")
            i += 1
            while i < len(text) and text[i] == "\n":
                i += 1
            continue
        j = i + 1
        while j < len(text):
            if text[j] == "\n":
                break
            if any(text.startswith(tok, j) for tok, _ in MATH_TOKENS):
                break
            j += 1
        parts.append(escape_plain(text[i:j]))
        i = j
    return "".join(parts)


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def color_model(h: str) -> str:
    """Modelo xcolor rgb,255 (uso em chaves color=/fill=)."""
    r, g, b = hex_rgb(h)
    return f"rgb,255:red,{int(r*255)};green,{int(g*255)};blue,{int(b*255)}"


def tikz_fill(h: str) -> str:
    return f"fill={{{color_model(h)}}}"


def tikz_draw_color(h: str) -> str:
    return f"color={{{color_model(h)}}}"


def latex_rgb(h: str) -> str:
    r, g, b = hex_rgb(h)
    return f"[rgb]{{{r:.3f},{g:.3f},{b:.3f}}}"


# Zonas verticais (% da página, topo → base) — slides internos 16:9
TITLE_Y_PCT = 4.0
CONTENT_Y_MIN_PCT = 17.0
BIBLIO_FOOTER_Y_PCT = 88.0
INST_RULE_Y_PCT = 94.0
INST_FOOTER_Y_PCT = 98.2


def pos_xy(x: float, y: float) -> str:
    return (
        f"([xshift={x/100:.5f}\\paperwidth,yshift=-{y/100:.5f}\\paperheight]"
        "current page.north west)"
    )


def rect_xywh(rect: list[float]) -> tuple[str, float, float]:
    x, y, w, h = rect
    anchor = pos_xy(x, y)
    return anchor, w / 100, h / 100


def tex_font(size: float, leading: float, content: str, *, bold: bool = False, color: str | None = None) -> str:
    inner = content
    if color:
        r, g, b = hex_rgb(color)
        inner = f"\\color[rgb]{{{r:.3f},{g:.3f},{b:.3f}}}{inner}"
    bf = "\\bfseries " if bold else ""
    return f"{{\\fontsize{{{size:.2f}}}{{{leading:.2f}}}\\selectfont {bf}{inner}}}"


def style_prefix(style: dict | None) -> str:
    if not style:
        return r"{\fontsize{12}{14.16}\selectfont "
    sz = float(style.get("size_pt", 12))
    lead = float(style.get("leading_pt", sz * 1.18))
    color = style.get("color", "#292D32")
    r, g, b = hex_rgb(color)
    weight = "\\bfseries " if style.get("weight") == "bold" else ""
    return (
        f"{{\\color[rgb]{{{r:.3f},{g:.3f},{b:.3f}}}\\fontsize{{{sz:.2f}}}{{{lead:.2f}}}\\selectfont "
        f"{weight}"
    )


def wrap_minipage(anchor: str, w: float, h: float, body: str, align: str = "left") -> str:
    tw = f"{w:.5f}\\paperwidth"
    th = f"{h:.5f}\\paperheight"
    body = re.sub(r"(\\\\\s*){2,}", r"\\\\", body)
    body = re.sub(r"\\\\\s*\}\s*$", "}", body)
    tikz_align = {"left": "left", "center": "center", "right": "right"}.get(align, "left")
    if align == "center":
        rag = "\\centering "
    elif align == "right":
        rag = "\\raggedleft "
    else:
        rag = "\\raggedright "
    return (
        f"  \\node[anchor=north west,inner sep=0pt,outer sep=0pt,text width={tw},"
        f"minimum height={th},align={tikz_align}] at {anchor} {{{rag}{body}\\par}};"
    )


def asset_relpath(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("assets/"):
        return p.split("/", 1)[1]
    if p.startswith("build/"):
        return p
    return p


def render_text(el: dict) -> str:
    anchor, w, h = rect_xywh(el["rect"])
    body = format_mixed_text(el.get("text", ""))
    align = (el.get("style") or {}).get("align", "left")
    return wrap_minipage(anchor, w, h, style_prefix(el.get("style")) + body + "}", align)


def render_formula(el: dict) -> str:
    anchor, w, h = rect_xywh(el["rect"])
    latex = normalize_text(el.get("latex", "").strip())
    sz = float((el.get("style") or {}).get("size_pt", 17))
    body = f"\\displaystyle {latex}"
    tw = f"{w:.5f}\\paperwidth"
    return (
        f"  \\node[anchor=north west,inner sep=0pt,text width={tw}] at {anchor} "
        f"{{\\fontsize{{{sz:.1f}}}{{{sz*1.18:.1f}}}\\selectfont ${body}$}};"
    )


def render_image(el: dict) -> str:
    anchor, w, h = rect_xywh(el["rect"])
    path = asset_relpath(el["path"])
    tw = f"{w:.5f}\\paperwidth"
    th = f"{h:.5f}\\paperheight"
    bg = el.get("background", "#FFFFFF")
    r, g, b = hex_rgb(bg)
    return (
        f"  \\node[anchor=north west,inner sep=0pt,{tikz_fill(bg)}] at {anchor} {{"
        f"\\includegraphics[width={tw},height={th},keepaspectratio]{{{path}}}}};"
    )


def render_arrow(el: dict) -> str:
    x1, y1 = el["from"]
    x2, y2 = el["to"]
    col = tikz_draw_color(el.get("color", "#59636E"))
    wpt = float(el.get("width_pt", 0.8))
    return (
        f"  \\draw[{col},line width={wpt}pt,-{{Stealth[scale=0.5]}}] "
        f"{pos_xy(x1, y1)} -- {pos_xy(x2, y2)};"
    )


def render_marker(el: dict) -> str:
    cx, cy = el["center"]
    rad = float(el.get("radius_pt", 4)) / 72.27 * 2.54  # approx cm from pt
    col = color_model(el.get("color", "#C1272F"))
    shape = el.get("shape", "circle")
    if shape == "circle":
        return f"  \\fill[color={{{col}}}] {pos_xy(cx, cy)} circle (0.08cm);"
    return f"  \\fill[color={{{col}}}] {pos_xy(cx, cy)} rectangle +(0.12cm,0.12cm);"


def render_table(el: dict) -> str:
    anchor, w, h = rect_xywh(el["rect"])
    headers = el.get("headers") or []
    rows = el.get("rows") or []
    cols = len(headers) or 1
    widths = el.get("column_widths_pct") or [100 // cols] * cols
    matrix = bool(el.get("matrix"))
    colspec_parts: list[str] = []
    for i, pct in enumerate(widths):
        if matrix and i > 0:
            colspec_parts.append(f">{{\\centering\\arraybackslash}}p{{{pct/100:.4f}\\linewidth}}")
        else:
            colspec_parts.append(f">{{\\raggedright\\arraybackslash}}p{{{pct/100:.4f}\\linewidth}}")
    colspec = " ".join(colspec_parts)
    sz = float((el.get("style") or {}).get("size_pt", 11.5))
    header_fill = el.get("header_fill", "#F3F5F7")
    diag_fill = el.get("diagonal_fill", "#E5F1ED")
    diagonal = {tuple(x) for x in el.get("diagonal_cells") or []}
    outline = {tuple(x) for x in el.get("outline_cells") or []}

    lines: list[str] = []
    lines.append(r"\renewcommand{\arraystretch}{1.35}")
    lines.append(r"\setlength{\tabcolsep}{4pt}")
    lines.append(r"\begin{tabular}{" + colspec + "}")
    lines.append(r"\toprule")
    hdr_cells = [format_mixed_text(str(h)) for h in headers]
    lines.append(" & ".join(f"\\cellcolor{latex_rgb(header_fill)}{c}" for c in hdr_cells) + r" \\")
    lines.append(r"\midrule")
    for ri, row in enumerate(rows):
        cells = []
        for ci, cell in enumerate(row):
            raw = str(cell)
            if raw.replace(".", "", 1).replace("-", "", 1).isdigit() or raw.isdigit():
                txt = escape_plain(raw)
            else:
                txt = format_mixed_text(raw)
            sty = ""
            key = (ri, ci + 1)
            if key in diagonal:
                sty += f"\\cellcolor{latex_rgb(diag_fill)}"
            if key in outline:
                cells.append(
                    sty + r"\fboxrule=0.8pt\fboxsep=2pt\fbox{" + txt + "}"
                )
            else:
                cells.append(sty + txt)
        lines.append(" & ".join(cells) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    tab = "\n".join(lines)
    tw = f"{w:.5f}\\paperwidth"
    body = (
        f"\\begin{{minipage}}{{\\linewidth}}"
        f"\\fontsize{{{sz:.2f}}}{{{sz*1.28:.2f}}}\\selectfont {tab}"
        "\\end{minipage}"
    )
    return (
        f"  \\node[anchor=north west,inner sep=0pt,text width={tw}] at {anchor} "
        f"{{{body}}};"
    )


def _chart_scope(rect: list[float]) -> str:
    x, y, w, h = rect
    return (
        f"  \\begin{{scope}}"
        f"[shift={{($(current page.north west)+({x/100:.5f}\\paperwidth,-{y/100:.5f}\\paperheight)$)}},"
        f"x={w/100:.5f}\\paperwidth,y={h/100:.5f}\\paperheight]"
    )


def render_chart_bar_vertical(el: dict) -> str:
    rect = el["rect"]
    data = el.get("data") or []
    y0, y1 = el.get("y_domain", [0, 5])
    ymax = max(float(y1), 1.0)
    y_ticks = el.get("y_ticks", list(range(int(y0), int(y1) + 1)))
    bar_color = color_model(el.get("bar_color", "#C1272F"))
    n = len(data) or 1
    plot_b, plot_t, axis_y = 0.18, 0.88, 0.12
    lines = [_chart_scope(rect)]
    lines.append(r"    \clip (0,0) rectangle (1,1);")
    lines.append(f"    \\draw[gray!50,line width=0.3pt] (0,{plot_b:.3f}) -- (1,{plot_b:.3f});")
    for i, row in enumerate(data):
        val = float(row.get(el.get("y_key", "noticias"), 0))
        xc = (i + 0.5) / n
        bw = min(0.55 / n, 0.14)
        x0 = xc - bw / 2
        bh = (val / ymax) * (plot_t - plot_b)
        if val == 0 and el.get("zero_marker") == "circle_open":
            lines.append(
                f"    \\draw[color={{{bar_color}}},line width=0.8pt] "
                f"({x0:.4f},{plot_b:.4f}) rectangle ({x0+bw:.4f},{plot_b+0.02:.4f});"
            )
            lines.append(f"    \\draw[color={{{bar_color}}},line width=0.6pt] ({xc:.4f},{plot_b+0.03:.4f}) circle (0.012);")
        else:
            lines.append(
                f"    \\fill[color={{{bar_color}}}] "
                f"({x0:.4f},{plot_b:.4f}) rectangle ({x0+bw:.4f},{plot_b+bh:.4f});"
            )
        label = str(row.get(el.get("x_key", "dia"), ""))
        lines.append(
            f"    \\node[anchor=north] at ({xc:.4f},{axis_y:.3f}) {{{tex_font(10.5, 12.4, escape_plain(label))}}};"
        )
        if val > 0:
            lines.append(
                f"    \\node[anchor=south] at ({xc:.4f},{plot_b+bh:.3f}) "
                f"{{{tex_font(10.5, 12.4, str(int(val)))}}};"
            )
    for yt in y_ticks:
        yf = plot_b + (float(yt) / ymax) * (plot_t - plot_b)
        lines.append(f"    \\node[anchor=east] at (-0.04,{yf:.3f}) {{{tex_font(10, 11.8, str(yt))}}};")
    yl = el.get("y_label", "")
    if yl:
        lines.append(f"    \\node[anchor=north] at (0.5,{axis_y-0.08:.3f}) {{{tex_font(10.5, 12.4, escape_plain(yl))}}};")
    lines.append(r"  \end{scope}")
    return "\n".join(lines)


def render_chart_bar_horizontal(el: dict) -> str:
    rect = el["rect"]
    data = el.get("data") or []
    label_zone = float(el.get("label_zone_pct", 22)) / 100
    value_zone = float(el.get("value_zone_pct", 12)) / 100
    plot_w = 1 - label_zone - value_zone
    max_v = max((float(r.get(el.get("x_key", "valor"), r.get("noticias", 0))) for r in data), default=1)
    n = len(data) or 1
    bar_h = 0.5 / n
    bar_color = color_model(el.get("bar_color", "#C1272F"))
    lines = [_chart_scope(rect)]
    lines.append(r"    \clip (0,0) rectangle (1,1);")
    for i, row in enumerate(data):
        val = float(row.get(el.get("x_key", "valor"), row.get("noticias", 0)))
        name = str(row.get(el.get("y_key", "fonte"), row.get("fonte", "")))
        yc = 1 - (i + 0.5) / n
        x0 = label_zone
        x1 = label_zone + plot_w * (val / max_v if max_v else 0)
        lines.append(f"    \\node[anchor=east] at ({label_zone-0.02:.3f},{yc:.3f}) {{{tex_font(10, 11.8, escape_plain(name))}}};")
        lines.append(f"    \\fill[color={{{bar_color}}}] ({x0:.3f},{yc-bar_h/2:.3f}) rectangle ({x1:.3f},{yc+bar_h/2:.3f});")
        lines.append(
            f"    \\node[anchor=west] at ({x1+0.01:.3f},{yc:.3f}) {{{tex_font(10, 11.8, str(int(val) if val==int(val) else val))}}};"
        )
    lines.append(r"  \end{scope}")
    return "\n".join(lines)


def render_chart_stacked_probability(el: dict) -> str:
    rect = el["rect"]
    data = el.get("data") or []
    lines = [_chart_scope(rect)]
    lines.append(r"    \clip (0,0) rectangle (1,1);")
    bar_b, bar_t = 0.48, 0.72
    x = 0.05
    span = 0.9
    for row in data:
        v = float(row.get("valor", 0))
        col = color_model(row.get("cor", "#68737D"))
        w = v * span
        x1 = x + w
        lines.append(f"    \\fill[color={{{col}}}] ({x:.3f},{bar_b:.3f}) rectangle ({x1:.3f},{bar_t:.3f});")
        if v >= 0.12:
            cx = (x + x1) / 2
            lines.append(
                f"    \\node[anchor=center] at ({cx:.3f},{(bar_b+bar_t)/2:.3f}) "
                f"{{{tex_font(10.5, 12.4, f'{v:.2f}'.replace('.',','))}}};"
            )
        x = x1
    for tick in el.get("x_ticks", [0, 0.5, 1]):
        lbl = f"{tick:.1f}".replace(".", ",")
        tx = 0.05 + tick * span
        lines.append(f"    \\node[anchor=north] at ({tx:.3f},{bar_b-0.04:.3f}) {{{tex_font(10.5, 12.4, lbl)}}};")
    leg = el.get("legend") or []
    for i, item in enumerate(leg[:3]):
        lx = 0.05 + (i + 0.5) * span / 3
        lines.append(f"    \\node[anchor=north] at ({lx:.3f},{bar_b-0.18:.3f}) {{{tex_font(10.5, 12.4, escape_plain(item))}}};")
    xl = el.get("x_label", "")
    if xl:
        lines.append(f"    \\node[anchor=north] at (0.5,0.08) {{{tex_font(10.5, 12.4, escape_plain(xl))}}};")
    if el.get("illustrative"):
        lines.append(
            r"    \node[anchor=south east] at (0.98,0.96) "
            r"{{\fontsize{9}{10.6}\selectfont DADOS ILUSTRATIVOS}};"
        )
    lines.append(r"  \end{scope}")
    return "\n".join(lines)


def render_chart_numberline(el: dict) -> str:
    rect = el["rect"]
    x0, x1 = el.get("x_domain", [-1, 1])
    marker = float(el.get("marker_value", el.get("data", [{}])[0].get("valor", 0.5)))
    lines = [
        _chart_scope(rect),
        f"    \\draw[line width=0.6pt] (0,0.5) -- (1,0.5);",
    ]
    for t in el.get("x_ticks", [x0, 0, x1]):
        frac = (t - x0) / (x1 - x0) if x1 != x0 else 0.5
        lbl = f"{t:+g}".replace(".", ",")
        lines.append(f"    \\node[anchor=north] at ({frac:.3f},0.42) {{{tex_font(10, 11.8, escape_plain(lbl))}}};")
    frac_m = (marker - x0) / (x1 - x0)
    lines.append(f"    \\fill[red] ({frac_m:.3f},0.5) circle (0.02);")
    lines.append(r"  \end{scope}")
    return "\n".join(lines)


def render_chart_dot_horizontal(el: dict) -> str:
    rect = el["rect"]
    data = el.get("data") or []
    x0, x1 = el.get("x_domain", [-0.3, 0.1])
    label_zone = float(el.get("label_zone_pct", 16)) / 100
    plot_b, plot_t = 0.28, 0.82
    lines = [_chart_scope(rect)]
    lines.append(r"    \clip (0,0) rectangle (1,1);")
    for t in el.get("x_ticks", []):
        frac = (float(t) - x0) / (x1 - x0)
        lines.append(
            f"    \\node[anchor=north] at ({label_zone + (1-label_zone)*frac:.3f},{plot_b-0.1:.3f}) "
            f"{{{tex_font(10, 11.8, escape_plain(str(t).replace('.',',')))}}};"
        )
    if el.get("zero_line"):
        zf = (0 - x0) / (x1 - x0)
        zx = label_zone + (1 - label_zone) * zf
        lines.append(f"    \\draw[line width=0.5pt,gray] ({zx:.3f},{plot_b:.3f}) -- ({zx:.3f},{plot_t:.3f});")
    n = len(data) or 1
    for i, row in enumerate(data):
        rho = float(row.get("rho", 0))
        frac = (rho - x0) / (x1 - x0)
        yc = plot_t - (i + 0.5) / n * (plot_t - plot_b)
        col = color_model(row.get("color", "#292D32"))
        name = row.get("indicador", "")
        lines.append(f"    \\node[anchor=east] at ({label_zone-0.02:.3f},{yc:.3f}) {{{tex_font(10.5, 12.4, escape_plain(name))}}};")
        xp = label_zone + (1 - label_zone) * frac
        if row.get("marker") == "square":
            lines.append(f"    \\fill[color={{{col}}}] ({xp:.3f},{yc:.3f}) rectangle +(0.018,-0.018);")
        else:
            lines.append(f"    \\fill[color={{{col}}}] ({xp:.3f},{yc:.3f}) circle (0.015);")
        lines.append(
            f"    \\node[anchor=west] at ({xp+0.02:.3f},{yc:.3f}) "
            f"{{{tex_font(10.5, 12.4, escape_plain(f'{rho:+.3f}'.replace('.',',')))}}};"
        )
    xl = el.get("x_label", "")
    if xl:
        lines.append(
            f"    \\node[anchor=north,text width={1-label_zone:.2f}\\linewidth,align=center] at (0.5,{plot_b-0.12:.3f}) "
            f"{{{tex_font(10, 11.8, escape_plain(xl))}}};"
        )
    lines.append(r"  \end{scope}")
    return "\n".join(lines)


def render_chart_interval_horizontal(el: dict) -> str:
    rect = el["rect"]
    row = (el.get("data") or [{}])[0]
    est = float(row.get("estimativa", 0))
    lo = float(row.get("inferior", 0))
    hi = float(row.get("superior", 0))
    x0, x1 = el.get("x_domain", [-0.2, 0.1])
    label_zone = 0.08
    def fx(v: float) -> float:
        return label_zone + (1 - label_zone) * (v - x0) / (x1 - x0)
    yc = 0.58
    lines = [_chart_scope(rect)]
    lines.append(r"    \clip (0,0) rectangle (1,1);")
    if el.get("zero_line"):
        lines.append(f"    \\draw[line width=0.6pt,ufsjgray] ({fx(0):.3f},0.2) -- ({fx(0):.3f},0.85);")
        lines.append(f"    \\node[anchor=south] at ({fx(0):.3f},0.18) {{{tex_font(9, 10.6, '0')}}};")
    icol = color_model(el.get("interval_color", "#59636E"))
    lines.append(f"    \\draw[color={{{icol}}},line width=1.2pt] ({fx(lo):.3f},{yc:.3f}) -- ({fx(hi):.3f},{yc:.3f});")
    lines.append(f"    \\draw[color={{{icol}}},line width=1.2pt] ({fx(lo):.3f},{yc-0.07:.3f}) -- ({fx(lo):.3f},{yc+0.07:.3f});")
    lines.append(f"    \\draw[color={{{icol}}},line width=1.2pt] ({fx(hi):.3f},{yc-0.07:.3f}) -- ({fx(hi):.3f},{yc+0.07:.3f});")
    pcol = color_model(el.get("point_color", "#292D32"))
    lines.append(f"    \\fill[color={{{pcol}}}] ({fx(est):.3f},{yc:.3f}) circle (0.022);")
    if el.get("value_labels"):
        lines.append(
            f"    \\node[anchor=south] at ({fx(est):.3f},{yc+0.12:.3f}) "
            f"{{{tex_font(10, 11.8, escape_plain(f'{est:+.3f}'.replace('.',',')))}}};"
        )
        lines.append(
            f"    \\node[anchor=north] at ({fx(lo):.3f},{yc-0.12:.3f}) "
            f"{{{tex_font(9.5, 11.2, escape_plain(f'{lo:+.3f}'.replace('.',',')))}}};"
        )
        lines.append(
            f"    \\node[anchor=north] at ({fx(hi):.3f},{yc-0.12:.3f}) "
            f"{{{tex_font(9.5, 11.2, escape_plain(f'{hi:+.3f}'.replace('.',',')))}}};"
        )
    for t in el.get("x_ticks", []):
        lines.append(
            f"    \\node[anchor=north] at ({fx(float(t)):.3f},0.32) "
            f"{{{tex_font(10, 11.8, escape_plain(str(t).replace('.',',')))}}};"
        )
    xl = el.get("x_label", "")
    if xl:
        lines.append(
            f"    \\node[anchor=north] at (0.5,0.12) "
            f"{{{tex_font(10.5, 12.4, format_mixed_text(xl))}}};"
        )
    il = el.get("interval_label", "")
    if il:
        lines.append(
            f"    \\node[anchor=south] at (0.5,0.88) "
            f"{{{tex_font(10, 11.8, format_mixed_text(il))}}};"
        )
    lines.append(r"  \end{scope}")
    return "\n".join(lines)


def render_chart(el: dict) -> str:
    kind = el.get("kind", "")
    dispatch = {
        "bar_vertical": render_chart_bar_vertical,
        "bar_horizontal": render_chart_bar_horizontal,
        "stacked_probability": render_chart_stacked_probability,
        "numberline": render_chart_numberline,
        "dot_horizontal": render_chart_dot_horizontal,
        "interval_horizontal": render_chart_interval_horizontal,
    }
    fn = dispatch.get(kind)
    if not fn:
        raise ValueError(f"chart kind desconhecido: {kind}")
    return fn(el)


def render_raster_chart(el: dict, slide_id: str) -> str:
    rel = el["path"].replace("assets/", "")
    src = ASSETS / rel if (ASSETS / rel).is_file() else ROOT / el["path"]
    if not src.is_file():
        return render_text(
            {
                "rect": el["rect"],
                "text": f"Asset ausente: {el.get('path')}",
                "style": {"size_pt": 10, "leading_pt": 12, "color": "#A54270", "weight": "bold"},
            }
        )
    try:
        from PIL import Image
    except ImportError:
        return render_image({"rect": el["rect"], "path": el["path"], "background": "#FFFFFF"})
    crop = el.get("plot_crop_px")
    if not crop:
        return render_image({"rect": el["rect"], "path": el["path"], "background": "#FFFFFF"})
    left, top, right, bottom = crop
    im = Image.open(src)
    cropped = im.crop((left, top, right, bottom))
    RASTER_DIR.mkdir(parents=True, exist_ok=True)
    out_name = f"{slide_id}_{el['id']}.png"
    out_path = RASTER_DIR / out_name
    cropped.save(out_path)
    anchor, w, h = rect_xywh(el["rect"])
    tw = f"{w:.5f}\\paperwidth"
    th = f"{h:.5f}\\paperheight"
    lines = [
        f"  \\node[anchor=north west,inner sep=0pt] at {anchor} "
        f"{{\\includegraphics[width={tw},height={th},keepaspectratio]{{{out_name}}}}};"
    ]
    # rótulos externos de eixo
    crop_w = right - left
    crop_h = bottom - top
    for tick_px, label in el.get("y_ticks_source_px", []):
        frac = (tick_px - top) / crop_h
        yp = el["rect"][1] + el["rect"][3] * frac
        xp = el["rect"][0] - 1
        lines.append(
            f"  \\node[anchor=east] at {pos_xy(xp, yp)} {{{tex_font(9, 10.6, escape_plain(str(label)))}}};"
        )
    yl = el.get("y_label", "")
    if yl:
        yp = el["rect"][1] + el["rect"][3] / 2
        lines.append(
            f"  \\node[anchor=east] at {pos_xy(el['rect'][0]-3, yp)} {{{tex_font(10, 11.8, escape_plain(yl))}}};"
        )
    for tick_px, label in el.get("x_ticks_source_px", []):
        frac = (tick_px - left) / crop_w
        xp = el["rect"][0] + el["rect"][2] * frac
        yp = el["rect"][1] + el["rect"][3] + 2
        lines.append(
            f"  \\node[anchor=north] at {pos_xy(xp, yp)} {{{tex_font(9, 10.6, escape_plain(str(label)))}}};"
        )
    return "\n".join(lines)


def render_element(el: dict, slide_id: str) -> str:
    t = el.get("type")
    if t == "text":
        return render_text(el)
    if t == "formula":
        return render_formula(el)
    if t == "table":
        return render_table(el)
    if t == "chart":
        return render_chart(el)
    if t == "raster_chart":
        return render_raster_chart(el, slide_id)
    if t == "arrow":
        return render_arrow(el)
    if t == "marker":
        return render_marker(el)
    if t == "image":
        return render_image(el)
    raise ValueError(f"tipo de elemento desconhecido: {t}")


def render_chrome(slide: dict, *, backup: bool = False, capa: bool = False) -> list[str]:
    lines: list[str] = []
    if capa:
        n = int(slide.get("n", 1))
        lines.append(
            f"  \\draw[ufsjred,line width=0.5pt] {pos_xy(5, 17.5)} -- {pos_xy(95, 17.5)};"
        )
        lines.append(
            f"  \\node[anchor=south east] at {pos_xy(95, 98.5)} "
            f"{{{tex_font(7, 8, f'{n:02d} / 29', color='#59636E')}}};"
        )
        return lines
    title = slide.get("title", "")
    footer = slide.get("footer", "")
    if backup:
        sid = slide.get("id", "A01")
        num = sid[1:3]
        page = f"A{num} / 08"
        ttl = title
    else:
        n = int(slide.get("n", 0))
        page = f"{n:02d} / 29"
        ttl = title
    lines.append(
        f"  \\node[anchor=north west,text width=0.9\\paperwidth] at {pos_xy(5, TITLE_Y_PCT)} "
        f"{{{tex_font(18, 20, format_mixed_text(ttl), bold=True, color='#C1272F')}}};"
    )
    if footer:
        lines.append(
            f"  \\node[anchor=north west,text width=0.9\\paperwidth] at {pos_xy(5, BIBLIO_FOOTER_Y_PCT)} "
            f"{{{tex_font(8, 9.2, format_mixed_text(footer), color='#59636E')}}};"
        )
    lines.append(
        f"  \\draw[ufsjred,line width=0.5pt] {pos_xy(5, INST_RULE_Y_PCT)} -- {pos_xy(95, INST_RULE_Y_PCT)};"
    )
    sig = "UFSJ $\\cdot$ PPGCC $\\cdot$ Ciência da Computação"
    lines.append(
        f"  \\node[anchor=south west] at {pos_xy(5, INST_FOOTER_Y_PCT)} "
        f"{{{tex_font(7.5, 8.5, sig, color='#59636E')}}};"
    )
    lines.append(
        f"  \\node[anchor=south east] at {pos_xy(95, INST_FOOTER_Y_PCT)} "
        f"{{{tex_font(7, 8, page, color='#59636E')}}};"
    )
    return lines


def render_slide(slide: dict, fatos: dict, geom: list) -> str:
    layout = slide.get("layout", "")
    if layout not in LAYOUTS:
        raise ValueError(f"layout não registrado: {layout} ({slide.get('id')})")
    capa = layout == "CAPA_INSTITUCIONAL"
    backup = slide.get("id", "").startswith("A")
    parts = ["\\begin{frame}[plain]"]
    parts.append("\\begin{tikzpicture}[remember picture,overlay]")
    for el in slide.get("elements") or []:
        parts.append(render_element(el, slide.get("id", "")))
        geom.append(
            {
                "slide_id": slide.get("id"),
                "element_id": el.get("id"),
                "type": el.get("type"),
                "rect": el.get("rect"),
            }
        )
    parts.extend(render_chrome(slide, backup=backup, capa=capa))
    parts.append("\\end{tikzpicture}")
    parts.append("\\end{frame}")
    return "\n".join(parts)


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema") != "qualificacao-ufsj-presentation-v4":
        raise SystemExit("Manifesto deve estar em qualificacao-ufsj-presentation-v4")
    fatos = load_fatos()
    geom: list = []
    chunks: list[str] = ["% Gerado por scripts/render_beamer.py — não editar à mão."]
    for s in data.get("slides", []):
        chunks.append(render_slide(s, fatos, geom))
    for s in data.get("backup", []):
        chunks.append(render_slide(s, fatos, geom))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
    GEOM_OUT.write_text(json.dumps(geom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {OUT} ({len(chunks)-1} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
