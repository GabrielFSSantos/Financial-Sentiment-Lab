#!/usr/bin/env python3
"""Gera build/slides_content.tex a partir do manifesto (layouts UFSJ)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dados" / "manifesto_slides.json"
FATOS_PATH = ROOT / "dados" / "fatos_cientificos.json"
OUT = ROOT / "build" / "slides_content.tex"
ASSETS = ROOT / "assets"

_BULLET_PLACEHOLDER = "\ue000"

FIGURE_NAMES = (
    "figura_2_soft_iti_noticias.png",
    "figura_3_meias_vidas.png",
    "figura_4_contrastes_bootstrap.png",
)


def load_fatos() -> dict:
    if FATOS_PATH.is_file():
        return json.loads(FATOS_PATH.read_text(encoding="utf-8")).get("ancoras", {})
    return {}


def normalize_unicode(text: str) -> str:
    subs = {
        "≠": r"$\neq$",
        "Δ": r"$\Delta$",
        "ρ": r"$\rho$",
        "λ": r"$\lambda$",
        "κ": r"$\kappa$",
        "≈": r"$\approx$",
        "≤": r"$\leq$",
        "≥": r"$\geq$",
        "−": "-",
        "→": r"$\rightarrow$",
        "•": _BULLET_PLACEHOLDER,
        "⁺": r"$^+$",
        "⁻": r"$^-$",
        "⁰": r"$^0$",
        "₁": r"$_1$",
        "₂": r"$_2$",
        "₃": r"$_3$",
        "₄": r"$_4$",
        "₅": r"$_5$",
        "₆": r"$_6$",
        "₇": r"$_7$",
        "ᵢ": r"$_i$",
        "ₛ": r"$_s$",
        "ᵈ": r"$_d$",
        "ʷ": r"$_w$",
        "⁽": r"$^{(}$",
        "⁾": r"$^{)}$",
        "¹": r"$^1$",
    }
    for u, tex in subs.items():
        text = text.replace(u, tex)
    return text


def _latex_escape_plain(text: str) -> str:
    text = text.replace("\\", "\\textbackslash{}")
    for a, b in (
        ("&", r"\&"),
        ("%", r"\%"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ):
        text = text.replace(a, b)
    return text.replace("−", "-")


def latex_escape(text: str) -> str:
    text = normalize_unicode(text)
    parts = re.split(r"(\$[^$]+\$)", text)
    out: list[str] = []
    for part in parts:
        if part.startswith("$") and part.endswith("$"):
            out.append(part)
        else:
            out.append(_latex_escape_plain(part))
    out_text = "".join(out)
    return out_text.replace(_BULLET_PLACEHOLDER, r"\textbullet{}")


def figure_path(visual: str) -> str | None:
    for name in FIGURE_NAMES:
        if name in (visual or "") and (ASSETS / name).is_file():
            return name
    return None


def bullets_block(lines: list[str], max_items: int = 5) -> str:
    if not lines:
        return ""
    rows = ["  \\begin{itemize}"]
    for line in lines[:max_items]:
        rows.append(f"    \\item {latex_escape(line)}")
    rows.append("  \\end{itemize}")
    return "\n".join(rows)


def footer_block(footer: str | None) -> str:
    if not footer:
        return ""
    return f"  \\vfill\\footnotesize{{\\color{{ufsjgray}}{latex_escape(footer)}}}"


def frame_begin(title: str | None, capa: bool = False) -> str:
    if capa:
        return "\\begin{frame}[plain,noframenumbering]"
    if title:
        return f"\\begin{{frame}}\n  \\frametitle{{{latex_escape(title)}}}"
    return "\\begin{frame}"


def frame_end() -> str:
    return "\\end{frame}"


def render_capa(s: dict) -> str:
    lines = s.get("screen", [])
    parts = [
        frame_begin(None, capa=True),
        "  \\begin{columns}[T]",
        "    \\begin{column}{\\paperwidth}",
        "      \\vspace{-0.15cm}",
        "      \\begin{center}",
        "        \\includegraphics[height=1.1cm]{logo_dcomp.png}\\hfill",
        "        \\includegraphics[height=1.1cm]{logo_ufsj_ppgcc.png}",
        "      \\end{center}\\vspace{0.4cm}",
        "      {\\color{ufsjred}\\rule{\\linewidth}{1.2pt}}\\\\[0.5cm]",
        f"      {{\\large\\color{{ufsjgray}}{latex_escape(lines[0] if lines else 'Exame de Qualificação')}}}\\\\[0.35cm]",
        f"      {{\\Large\\bfseries\\color{{ufsjdark}}{latex_escape(lines[1] if len(lines) > 1 else s.get('title', ''))}}}\\\\[0.2cm]",
        f"      {{\\large {latex_escape(lines[2] if len(lines) > 2 else '')}}}\\\\[0.6cm]",
        f"      {{\\normalsize {latex_escape(lines[3] if len(lines) > 3 else '')}}}\\\\[0.2cm]",
        f"      {{\\normalsize\\color{{ufsjgray}}{latex_escape(lines[4] if len(lines) > 4 else 'UFSJ \\textbullet{} 2026')}}}\\\\",
        "    \\end{column}",
        "  \\end{columns}",
        frame_end(),
    ]
    return "\n".join(parts)


def _column_chunks(lines: list[str], ncols: int) -> list[list[str]]:
    if not lines:
        return [[] for _ in range(ncols)]
    n = len(lines)
    base, extra = divmod(n, ncols)
    sizes = [base + (1 if i < extra else 0) for i in range(ncols)]
    chunks: list[list[str]] = []
    idx = 0
    for sz in sizes:
        chunks.append(lines[idx : idx + sz])
        idx += sz
    return chunks


def render_columns_cards(s: dict, ncols: int) -> str:
    lines = list(s.get("screen", []))
    layout = s.get("layout", "")
    tail: list[str] = []
    if layout in ("TRES_ETAPAS", "TRES_PILARES") and len(lines) > ncols:
        tail = lines[ncols:]
        lines = lines[:ncols]
    elif layout == "QUATRO_LIMITES" and len(lines) > ncols:
        tail = lines[ncols:]
        lines = lines[:ncols]
    chunks = _column_chunks(lines, ncols)
    col_w = f"{0.98 / ncols:.2f}\\textwidth"
    parts = [frame_begin(s.get("title", ""))]
    parts.append("  \\begin{columns}[T,onlytextwidth]")
    for chunk in chunks[:ncols]:
        parts.append(f"    \\begin{{column}}{{{col_w}}}")
        for item in chunk:
            parts.append("      \\begin{ufsjcard}")
            parts.append(f"        {latex_escape(item)}")
            parts.append("      \\end{ufsjcard}\\vspace{4pt}")
        parts.append("    \\end{column}")
    parts.append("  \\end{columns}")
    if tail:
        parts.append("  \\vspace{6pt}")
        parts.append(bullets_block(tail, 3))
    parts.append(footer_block(s.get("footer")))
    parts.append(frame_end())
    return "\n".join(parts)


def render_pergunta_hipotese(s: dict) -> str:
    lines = s.get("screen", [])
    q = lines[0] if lines else ""
    rest = lines[1:] if len(lines) > 1 else []
    parts = [
        frame_begin(s.get("title", "")),
        "  \\begin{ufsjcard}",
        f"    \\textbf{{Pergunta}}\\\\[4pt]{latex_escape(q)}",
        "  \\end{ufsjcard}\\vspace{6pt}",
        "  \\begin{ufsjformula}",
        "    \\centering",
        "    $\\Delta\\rho = \\rho_s(\\text{ITI-H7}, R^{1w}) - \\rho_s(\\text{Soft}, R^{1w})$",
        "  \\end{ufsjformula}\\vspace{4pt}",
        bullets_block(rest, 4),
        footer_block(s.get("footer")),
        frame_end(),
    ]
    return "\n".join(parts)


def render_corpus_bars(s: dict, fatos: dict) -> str:
    fontes = fatos.get("fontes", {})
    items = list(fontes.items())[:5]
    max_v = max((v for _, v in items), default=1)
    parts = [
        frame_begin(s.get("title", "")),
        "  \\begin{columns}[T]",
        "    \\begin{column}{0.28\\textwidth}",
        f"    \\ufsjkpi{{{fatos.get('corpus_canonicas', 1253)}}}{{notícias canônicas}}",
        "    \\vspace{6pt}",
        f"    \\footnotesize {latex_escape(s.get('screen', [''])[0] if s.get('screen') else '')}",
        "    \\end{column}",
        "    \\begin{column}{0.68\\textwidth}",
        "    \\begin{tikzpicture}[x=1cm,y=0.42cm]",
    ]
    for i, (nome, val) in enumerate(items):
        w = 4.5 * val / max_v
        parts.append(f"      \\fill[ufsjred] (0,{-i}) rectangle ({w:.2f},{-i+0.35});")
        parts.append(f"      \\node[anchor=west,font=\\scriptsize] at (0,{-i+0.17}) {{{latex_escape(nome)}}};")
        parts.append(f"      \\node[anchor=west,font=\\scriptsize] at ({w+0.1:.2f},{-i+0.17}) {{{val}}};")
    parts.append("    \\end{tikzpicture}")
    parts.append("    \\end{column}")
    parts.append("  \\end{columns}")
    for line in (s.get("screen") or [])[3:]:
        parts.append(f"  \\footnotesize{{\\color{{ufsjgray}}{latex_escape(line)}}}")
    parts.append(footer_block(s.get("footer")))
    parts.append(frame_end())
    return "\n".join(parts)


def render_fluxo(s: dict) -> str:
    lines = s.get("screen", [])
    top = lines[0] if lines else ""
    bottom = lines[1] if len(lines) > 1 else ""
    parts = [
        frame_begin(s.get("title", "")),
        "  \\begin{block}{Frente temporal}",
        f"    {latex_escape(top)}",
        "  \\end{block}",
        "  \\begin{block}{Frente textual}",
        f"    {latex_escape(bottom)}",
        "  \\end{block}",
        bullets_block(lines[2:], 3),
        footer_block(s.get("footer")),
        frame_end(),
    ]
    return "\n".join(parts)


def render_formula_rich(s: dict, eq: str, symbols: list[str]) -> str:
    parts = [
        frame_begin(s.get("title", "")),
        "  \\begin{columns}[T]",
        "    \\begin{column}{0.52\\textwidth}",
        "      \\begin{ufsjformula}",
        f"        \\centering {eq}",
        "      \\end{ufsjformula}",
        "      \\footnotesize",
        bullets_block(symbols, 4),
        "    \\end{column}",
        "    \\begin{column}{0.45\\textwidth}",
        bullets_block(s.get("screen", []), 5),
        "    \\end{column}",
        "  \\end{columns}",
        footer_block(s.get("footer")),
        frame_end(),
    ]
    return "\n".join(parts)


def render_figure_slide(s: dict, visual: str, fig_h: str = "0.58") -> str:
    fig = figure_path(visual)
    parts = [frame_begin(s.get("title", ""))]
    if fig:
        parts.extend(
            [
                "  \\begin{center}",
                f"    \\includegraphics[width=\\linewidth,height=" + fig_h + "\\textheight,keepaspectratio]{" + fig + "}",
                "  \\end{center}",
            ]
        )
        parts.append(bullets_block((s.get("screen") or [])[:3], 3))
    else:
        parts.append(bullets_block(s.get("screen", []), 5))
    parts.append(footer_block(s.get("footer")))
    parts.append(frame_end())
    return "\n".join(parts)


def render_kpis(s: dict, fatos: dict) -> str:
    lines = s.get("screen", [])
    parts = [frame_begin(s.get("title", ""))]
    if "acurácia" in s.get("title", "").lower() or "métricas" in s.get("title", "").lower():
        parts.append("  \\begin{columns}[T]")
        parts.append("    \\begin{column}{0.32\\textwidth}\\ufsjkpi{50\\%}{acurácia}\\end{column}")
        parts.append("    \\begin{column}{0.32\\textwidth}\\ufsjkpi{0,448}{F1 macro}\\end{column}")
        parts.append("    \\begin{column}{0.32\\textwidth}\\ufsjkpi{0,197}{$\\kappa$}\\end{column}")
        parts.append("  \\end{columns}\\vspace{8pt}")
    elif "correlação" in s.get("title", "").lower():
        parts.append("  \\begin{columns}[T]")
        parts.append("    \\begin{column}{0.32\\textwidth}\\ufsjkpi{$-$0,163}{$\\rho_s$ ITI-H7}\\end{column}")
        parts.append("    \\begin{column}{0.32\\textwidth}\\ufsjkpi{$-$0,203}{$\\rho_s$ Soft}\\end{column}")
        parts.append("    \\begin{column}{0.32\\textwidth}\\ufsjkpi{+0,040}{$\\Delta\\rho$}\\end{column}")
        parts.append("  \\end{columns}\\vspace{8pt}")
    parts.append(bullets_block(lines, 5))
    parts.append(footer_block(s.get("footer")))
    parts.append(frame_end())
    return "\n".join(parts)


def render_conclusao(s: dict) -> str:
    parts = [
        frame_begin(s.get("title", "")),
        "  \\begin{enumerate}",
    ]
    for line in (s.get("screen") or [])[:4]:
        parts.append(f"    \\item {latex_escape(line)}")
    parts.append("  \\end{enumerate}")
    if len((s.get("screen") or [])) > 4:
        parts.append(
            "  \\vspace{6pt}\\centering\\textbf{"
            + latex_escape(s["screen"][-1])
            + "}"
        )
    parts.append(footer_block(s.get("footer")))
    parts.append(frame_end())
    return "\n".join(parts)


def render_slide(s: dict, fatos: dict) -> str:
    layout = s.get("layout", "")
    visual = s.get("visual", "")
    title = s.get("title", "")

    if layout == "CAPA":
        return render_capa(s)
    if layout in ("DUPLA_COMPARACAO", "DUAS_REPRESENTACOES", "LIMITACAO_BASELINE"):
        return render_columns_cards(s, 2)
    if layout in ("TRES_ETAPAS", "TRES_PILARES", "QUATRO_LIMITES"):
        n = 3 if "TRES" in layout else 4
        return render_columns_cards(s, n)
    if layout == "PERGUNTA_HIPOTESE":
        return render_pergunta_hipotese(s)
    if layout == "CORPUS_BARRAS":
        return render_corpus_bars(s, fatos)
    if layout == "FLUXO_DUAS_LINHAS":
        return render_fluxo(s)
    if layout == "GRAFICO_DIDATICO":
        parts = [
            frame_begin(title),
            "  \\begin{tikzpicture}[x=0.9cm,y=0.5cm]",
            "    \\foreach \\y/\\v in {0/4,1/0,2/1,3/5,4/0}",
            "      \\fill[ufsjred] (0,\\y) rectangle (\\v,\\y+0.4);",
            "    \\node[font=\\scriptsize,anchor=north] at (2.5,-1) {DADOS ILUSTRATIVOS};",
            "  \\end{tikzpicture}\\vspace{6pt}",
            bullets_block(s.get("screen", []), 4),
            footer_block(s.get("footer")),
            frame_end(),
        ]
        return "\n".join(parts)
    if layout in ("PROBABILIDADES", "FORMULA_EXEMPLO", "MEDIA_DIARIA", "FORMULA_DESTAQUE", "CONTA_PASSO_A_PASSO"):
        eq = {
            "PROBABILIDADES": r"$p^+, p^-, p^0$",
            "FORMULA_EXEMPLO": r"$s_i = p_i^+ - p_i^-$",
            "MEDIA_DIARIA": r"$\bar{s}_d = \frac{1}{n_d}\sum_i s_i$",
            "FORMULA_DESTAQUE": r"$ITI_t = \lambda ITI_{t-1} + S_t$",
            "CONTA_PASSO_A_PASSO": r"$ITI \leftarrow 0{,}2283$",
        }.get(layout, r"$s_i$")
        return render_formula_rich(s, eq, (s.get("screen") or [])[-2:])
    if layout == "MEMORIA_COMPARACAO":
        return render_columns_cards(s, 2)
    if layout in ("GRAFICO_REAL", "INTERVALO_BOOTSTRAP"):
        return render_figure_slide(s, visual, "0.62" if layout == "GRAFICO_REAL" else "0.5")
    if layout in ("METRICAS", "DOIS_VALORES", "AMOSTRA_100") or "correlação" in title.lower():
        return render_kpis(s, fatos)
    if layout == "MATRIZ_CONFUSAO":
        return render_figure_slide(s, visual, "0.45") if figure_path(visual) else render_columns_cards(s, 2)
    if layout in ("TABELA_COMPARACAO", "CRONOGRAMA", "RECORTE_TEXTO", "LINHA_TEMPO"):
        return render_columns_cards(s, 2)
    if layout == "CONCLUSAO":
        return render_conclusao(s)

    fig = figure_path(visual)
    parts = [frame_begin(title)]
    if fig:
        parts.append("  \\begin{center}")
        parts.append(
            f"    \\includegraphics[width=0.88\\linewidth,height=0.55\\textheight,keepaspectratio]{{{fig}}}"
        )
        parts.append("  \\end{center}")
    parts.append(bullets_block(s.get("screen", []), 5))
    parts.append(footer_block(s.get("footer")))
    parts.append(frame_end())
    return "\n".join(parts)


def render_backup(s: dict, fatos: dict) -> str:
    title = f"[Apoio] {s.get('title', '')}"
    s2 = {**s, "title": title}
    return render_slide(s2, fatos)


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fatos = load_fatos()
    chunks: list[str] = ["% Gerado por scripts/render_beamer.py — não editar à mão."]
    for s in data.get("slides", []):
        chunks.append(render_slide(s, fatos))
    for s in data.get("backup", []):
        chunks.append(render_backup(s, fatos))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
    print(f"OK: {OUT} ({len(chunks)-1} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
