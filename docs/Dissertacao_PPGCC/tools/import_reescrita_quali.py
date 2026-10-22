#!/usr/bin/env python3
"""Importador legado (markdown → capítulos LaTeX). Texto canônico: Dissertacao_PPGCC/*.tex."""
from __future__ import annotations

import re
import sys
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[3]
MD = LAB_ROOT / "docs" / "Dissertacao_Qualificacao_Reescrita_Integral_2026-10-22.md"
OUT = Path(__file__).resolve().parents[1]
PRETEXTUAL = OUT / "00_pretextual.tex"

TABLE_COUNTER = 0

PIPELINE_FIGURE_TEX = r"""
\begin{figure}[htbp]
\centering
\resizebox{\textwidth}{!}{%
\begin{tikzpicture}[
  x=1.12cm, y=1.05cm,
  font=\footnotesize,
  box/.style={draw, rectangle, rounded corners=2pt, align=center, inner sep=2pt, text width=2.5cm, minimum height=1.05cm},
  arr/.style={-{Stealth[length=1.8mm]}, thick},
  lane/.style={font=\itshape\scriptsize, align=center, text width=2.8cm}
]
\node[box] (c) at (0,0) {Corpus de\\notícias};
\node[box] (a) at (-3.25,-1.55) {Amostra para\\anotação humana};
\node[box] (t) at (-3.25,-3.15) {Concordância\\($\kappa$, F1)};
\node[box] (s) at (0,-1.55) {Classificador\\(escore $d$)};
\node[box] (e) at (2.55,-1.55) {Agregação\\diária};
\node[box] (iti) at (5.1,-1.55) {ITI\\(EWMA)};
\node[box] (b) at (2.55,-3.15) {Baselines\\B0--B3};
\node[box] (m) at (0,-3.15) {Retornos\\futuros};
\node[box] (r) at (5.1,-3.15) {Comparação\\semanal};
\draw[arr] (c.south) -- ++(0,-0.32) -| (a.north);
\draw[arr] (c.south) -- ++(0,-0.32) -| (s.north);
\draw[arr] (a.south) -- (t.north);
\draw[arr] (s.east) -- (e.west);
\draw[arr] (e.east) -- (iti.west);
\draw[arr] (e.south) -- (b.north);
\draw[arr] (iti.south) -- (r.north);
\draw[arr] (b.east) -- (r.west);
\draw[arr] (m.east) -- ++(0.55,0) |- (r.south);
\node[lane] at (-3.25,-4.05) {Validação textual\\(Cap.~\ref{cap:resultados})};
\node[lane] at (2.55,-4.05) {Avaliação temporal\\(correlações e bootstrap)};
\end{tikzpicture}%
}
\caption{Fluxo da pesquisa: trilha de validação textual (esquerda) e construção do índice com comparação temporal (direita), a partir do mesmo corpus.}
\label{fig:pipeline}
\vspace{0.3em}
{\footnotesize Fonte: elaboração própria.}
\end{figure}
""".strip()

CHAPTERS = [
    (r"^# 1 Introdução", "01_introducao.tex", r"Introdução", "cap:introducao"),
    (r"^# 2 Fundamentação teórica", "02_fundamentacao.tex", r"Fundamentação teórica", "cap:fundamentacao"),
    (r"^# 3 Trabalhos relacionados", "03_trabalhos_relacionados.tex", r"Trabalhos relacionados", "cap:relacionados"),
    (r"^# 4 Metodologia", "04_metodologia.tex", r"Metodologia", "cap:metodologia"),
    (r"^# 5 Resultados preliminares", "05_resultados.tex", r"Resultados preliminares e discussão", "cap:resultados"),
    (r"^# 6 Considerações finais", "06_consideracoes_finais.tex", r"Considerações finais e plano de continuidade", "cap:consideracoes"),
]

APP_START = r"^# Apêndice A"
APP_END = r"^# PARTE III"

CITE_MAP = [
    (r"Tetlock \(2007\)", r"\\citeonline{tetlock2007media}"),
    (r"Baker, Bloom e Davis \(2016\)", r"\\citeonline{baker2016epu}"),
    (r"Baker e Shapiro", r"Baker e Shapiro"),  # keep prose if any
    (r"Santos, Bianchi e Costa \(2023\)", r"\\citeonline{santos2023finbert}"),
    (r"\(Brasil, 2020\)", r"(\\cite{lei14026})"),
    (r"Devlin et al\. \(2019\)", r"\\citeonline{devlin2019bert}"),
    (r"Souza, Nogueira e Lotufo \(2020\)", r"\\citeonline{souza2020bertimbau}"),
    (r"Loughran e McDonald \(2011\)", r"\\citeonline{loughran2011liability}"),
    (r"Araci \(2019\)", r"\\citeonline{araci2020finbert}"),
    (r"Cohen \(1960\)", r"\\citeonline{cohen1960kappa}"),
    (r"Artstein e Poesio \(2008\)", r"\\citeonline{artstein2008agreement}"),
    (r"Fleiss \(1971\)", r"\\citeonline{fleiss1971nominal}"),
    (r"Shapiro, Sudhof e Wilson \(2022\)", r"\\citeonline{shapiro2022fed}"),
    (r"Federal Reserve Bank of San Francisco, s\.d\.", r"\\citeonline{frbsfNewsSentiment}"),
    (r"Yoshinaga e Castro Junior \(2012\)", r"\\citeonline{yoshinaga2012sentimento}"),
    (r"Duarte, Montenegro González e Cruz Junior \(2021\)", r"\\citeonline{duarte2020news}"),
    (r"Brito et al\. \(2022\)", r"\\citeonline{racef2022sentimento}"),
    (r"Cortis et al\. \(2017\)", r"\\citeonline{cortis2017semeval5}"),
    (r"Yuan et al\. \(2020\)", r"\\citeonline{yuan2020target}"),
    (r"Sinha et al\. \(2022\)", r"\\citeonline{sinha2022sentfin}"),
    (r"Künsch \(1989\)", r"\\citeonline{kunsch1989bootstrap}"),
    (r"Holm \(1979\)", r"\\citeonline{holm1979multiple}"),
    (r"Capítulo~5", r"Capítulo~\\ref{cap:resultados}"),
    (r"Capítulo 5", r"Capítulo~\\ref{cap:resultados}"),
    (r"Capítulo~2", r"Capítulo~\\ref{cap:fundamentacao}"),
    (r"Capítulo 2", r"Capítulo~\\ref{cap:fundamentacao}"),
    (r"Capítulo~3", r"Capítulo~\\ref{cap:relacionados}"),
    (r"Capítulo 3", r"Capítulo~\\ref{cap:relacionados}"),
    (r"Capítulo~4", r"Capítulo~\\ref{cap:metodologia}"),
    (r"Capítulo 4", r"Capítulo~\\ref{cap:metodologia}"),
    (r"Capítulo~6", r"Capítulo~\\ref{cap:consideracoes}"),
    (r"Capítulo 6", r"Capítulo~\\ref{cap:consideracoes}"),
    (r"Apêndice A", r"Apêndice~\\ref{ap:protocolo}"),
    (r"Apêndice B", r"Apêndice~\\ref{ap:rastreabilidade}"),
]


def extract_body(text: str) -> str:
    m1 = text.find("<!-- INICIO_TEXTO_ACADEMICO -->")
    m2 = text.find("<!-- FIM_TEXTO_ACADEMICO -->")
    if m1 < 0 or m2 < 0:
        raise SystemExit("Marcadores INICIO/FIM_TEXTO_ACADEMICO não encontrados")
    return text[m1:m2]


def split_chapters(body: str) -> dict[str, str]:
    lines = body.splitlines()
    chunks: dict[str, str] = {}
    current_key = None
    buf: list[str] = []

    def flush():
        nonlocal buf, current_key
        if current_key:
            chunks[current_key] = "\n".join(buf).strip() + "\n"
        buf = []

    for line in lines:
        if line.startswith("# Elementos pré-textuais"):
            flush()
            current_key = "__pretext__"
            continue
        matched = None
        for pat, _, _, _ in CHAPTERS:
            if re.match(pat, line):
                matched = pat
                break
        if matched:
            flush()
            current_key = matched
            continue
        if re.match(APP_START, line):
            flush()
            current_key = "__appendix__"
            buf.append(line)
            continue
        if current_key == "__pretext__":
            buf.append(line)
            continue
        if current_key:
            buf.append(line)
    flush()
    return chunks


def md_table_to_latex(block: str) -> str:
    rows = [r.strip() for r in block.strip().splitlines() if r.strip()]
    if len(rows) < 2:
        return block
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    sep = rows[1]
    if not re.match(r"^\|?[\s\-:|]+\|?$", sep):
        return block
    data_rows = rows[2:]
    col_spec = "|" + "|".join(["l"] * len(header)) + "|"
    out = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{...}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\hline",
    ]
    out.append(" & ".join(f"\\textbf{{{h}}}" for h in header) + " \\\\")
    out.append("\\hline")
    for row in data_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        out.append(" & ".join(cells) + " \\\\")
    out.append("\\hline")
    out.append("\\end{tabular}")
    out.append("\\end{table}")
    return "\n".join(out)


def clean_heading_title(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\s+", "", title).strip()


def convert_block(md: str) -> str:
    global TABLE_COUNTER
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_table = False
    table_buf: list[str] = []

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and not in_table:
            in_table = True
            table_buf = [line]
            i += 1
            continue
        if in_table:
            if line.strip().startswith("|"):
                table_buf.append(line)
                i += 1
                continue
            in_table = False
            tbl = "\n".join(table_buf)
            # preserve markdown tables as tabular manually in source - use simple conversion
            out.append(convert_table_simple(table_buf))
            table_buf = []
            continue

        if line.startswith("<!-- CONFIRMAR") or line.startswith("<!-- FIM"):
            out.append("% " + line.strip("<!- ").rstrip(">"))
            i += 1
            continue
        if line.startswith("<!--"):
            out.append("% " + line)
            i += 1
            continue

        if "**[Figura 1" in line:
            out.append(PIPELINE_FIGURE_TEX)
            i += 1
            continue

        if m := re.match(r"^### (.+)$", line):
            out.append(f"\\subsection{{{clean_heading_title(m.group(1))}}}")
            i += 1
            continue
        if m := re.match(r"^## (.+)$", line):
            out.append(f"\\section{{{clean_heading_title(m.group(1))}}}")
            i += 1
            continue
        if line.startswith("# "):
            i += 1
            continue

        if line.startswith("> "):
            out.append(line[2:])
            i += 1
            continue

        if line.strip() == "---":
            i += 1
            continue

        if line.startswith("**Quadro") or line.startswith("**Tabela"):
            out.append(line.replace("**", ""))
            i += 1
            continue

        stripped = line.strip()
        if stripped.startswith("**Fonte:") or stripped.startswith("Fonte:"):
            plain = stripped.replace("**", "")
            out.append("{\\footnotesize " + inline_format(plain) + "}")
            i += 1
            continue

        if line.strip().startswith("- "):
            if not out or out[-1] != "\\begin{itemize}":
                out.append("\\begin{itemize}")
            item = line.strip()[2:]
            item = inline_format(item)
            out.append(f"  \\item {item}")
            i += 1
            while i < len(lines) and lines[i].strip().startswith("- "):
                item = lines[i].strip()[2:]
                out.append(f"  \\item {inline_format(item)}")
                i += 1
            out.append("\\end{itemize}")
            continue

        if re.match(r"^\d+\. ", line.strip()):
            if not out or out[-1] != "\\begin{enumerate}":
                out.append("\\begin{enumerate}")
            item = re.sub(r"^\d+\.\s*", "", line.strip())
            out.append(f"  \\item {inline_format(item)}")
            i += 1
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                item = re.sub(r"^\d+\. ", "", lines[i].strip())
                out.append(f"  \\item {inline_format(item)}")
                i += 1
            out.append("\\end{enumerate}")
            continue

        if line.strip() == "":
            out.append("")
            i += 1
            continue

        if line.strip().startswith("*O que isso significa"):
            out.append("\\textit{" + inline_format(line.strip().lstrip("*").rstrip("*")) + "}")
            i += 1
            continue

        out.append(inline_format(line))
        i += 1

    if in_table and table_buf:
        out.append(convert_table_simple(table_buf))

    return "\n".join(out)


def convert_table_simple(rows: list[str]) -> str:
    global TABLE_COUNTER
    parsed = []
    for r in rows:
        if re.match(r"^\|?[\s\-:|]+\|?$", r.strip()):
            continue
        parsed.append([c.strip() for c in r.strip().strip("|").split("|")])
    if not parsed:
        return ""
    ncol = len(parsed[0])
    header_raw = parsed[0]
    if ncol <= 2:
        colspec = "|l|L|"
    elif ncol == 3:
        colspec = "|L|L|L|"
    elif ncol == 4:
        colspec = "|L|r|r|r|"
    else:
        colspec = "|" + "|".join(["L"] * ncol) + "|"
    TABLE_COUNTER += 1
    label = f"tab:import{TABLE_COUNTER}"
    caption = infer_table_caption(header_raw)
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabularx}}{{\\textwidth}}{{{colspec}}}",
        "\\hline",
    ]
    header = [inline_format(c) for c in header_raw]
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\hline")
    for row in parsed[1:]:
        cells = [inline_format(c) for c in row]
        lines.append(" & ".join(cells) + " \\\\")
    lines.append("\\hline")
    lines.append("\\end{tabularx}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def infer_table_caption(header: list[str]) -> str:
    """Legenda descritiva a partir do cabeçalho (evita 'Tabela N – Tabela N')."""
    h = " ".join(header).lower()
    rules: list[tuple[str, str]] = [
        ("linha de pesquisa", "Posicionamento do ITI em relação à literatura"),
        ("medida", "Definição dos baselines e agregação semanal"),
        ("avaliação textual", "Concordância do classificador nas rodadas textuais"),
        ("subconjunto", "Desempenho por tipo de notícia"),
        ("configuração", "Confrontos favoráveis ao ITI na janela principal"),
        ("recorte experimental", "Síntese de execuções temporais"),
        ("dimensão", "Ameaças à validade e encaminhamentos"),
        ("etapa", "Plano de continuidade"),
        ("campo", "Campos do protocolo de anotação"),
        ("item", "Registros de rastreabilidade experimental"),
    ]
    for needle, caption in rules:
        if needle in h:
            return caption
    first = header[0].strip()
    return first if first else "Quadro resumo"


def escape_percent_in_text(s: str) -> str:
    """Converte percentuais textuais (48%) em 48\\% sem alterar comentários LaTeX."""

    return re.sub(r"(?<!\\)(\d+(?:,\d+)?)%", r"\1\\%", s)


def escape_latex_identifier(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("#", "\\#")
        .replace("%", "\\%")
    )


def inline_format(s: str) -> str:
    s = s.replace("α", "$\\alpha$")
    s = s.replace("κ", "$\\kappa$")
    s = re.sub(r"\*\*(.+?)\*\*", lambda m: "\\textbf{" + m.group(1) + "}", s)
    s = re.sub(
        r"`([^`]+)`",
        lambda m: "\\texttt{" + escape_latex_identifier(m.group(1)) + "}",
        s,
    )
    # \( \) to $ $
    s = re.sub(r"\\\((.+?)\\\)", r"$\1$", s)
    s = re.sub(r"\\\[(.+?)\\\]", r"\\[\n\\1\n\\]", s, flags=re.DOTALL)
    for pat, rep in CITE_MAP:
        s = re.sub(pat, rep, s)
    return escape_percent_in_text(s)


def write_chapter(path: Path, title: str, label: str, body_md: str) -> None:
    # drop first lines until past chapter title in md chunk
    body_md = re.sub(r"^# .+\n", "", body_md, count=1)
    tex = convert_block(body_md)
    content = f"\\chapter{{{title}}}\n\\label{{{label}}}\n\n{tex}\n"
    path.write_text(content, encoding="utf-8")


def write_pretextual(pretext_md: str) -> None:
    if not pretext_md.strip() or not PRETEXTUAL.exists():
        return

    def grab(header: str, nxt: str | None) -> str:
        end = rf"(?=^## {nxt}\s*$)" if nxt else r"\Z"
        m = re.search(rf"^## {header}\s*\n(.*?){end}", pretext_md, re.M | re.S)
        return m.group(1).strip() if m else ""

    agrad = grab("Agradecimentos", "Resumo")
    resumo_block = grab("Resumo", "Abstract")
    abstract_block = grab("Abstract", None)

    pk = re.search(r"\*\*Palavras-chave:\*\*\s*(.+)", resumo_block, re.I)
    resumo_body = resumo_block
    palavras = ""
    if pk:
        palavras = pk.group(1).strip()
        resumo_body = resumo_block[: pk.start()].strip()

    kw = re.search(r"\*\*Keywords:\*\*\s*(.+)", abstract_block, re.I)
    abstract_body = abstract_block
    keywords = ""
    if kw:
        keywords = kw.group(1).strip()
        abstract_body = abstract_block[: kw.start()].strip()

    resumo_body = escape_percent_in_text(inline_format(resumo_body))
    abstract_body = escape_percent_in_text(inline_format(abstract_body))
    agrad_tex = "\n\n".join(inline_format(p) for p in agrad.split("\n\n") if p.strip())

    base = PRETEXTUAL.read_text(encoding="utf-8")

    def _agrad_block(_: re.Match[str]) -> str:
        return "\\begin{agradecimentos}\n" + agrad_tex + "\n\\end{agradecimentos}"

    base = re.sub(
        r"\\begin\{agradecimentos\}.*?\\end\{agradecimentos\}",
        _agrad_block,
        base,
        count=1,
        flags=re.S,
    )
    resumo_tex = (
        "\\begin{resumo}\n\n"
        + resumo_body
        + "\n\n\\vspace{\\onelineskip}\n\n\\noindent\n"
        + f"\\textbf{{Palavras-chave}}: {palavras}.\n\\end{{resumo}}"
    )
    idx_abs = base.find("\\begin{resumo}[Abstract]")
    idx_res = base.find("\\begin{resumo}")
    if idx_res >= 0 and idx_abs > idx_res:
        end_res = base.find("\\end{resumo}", idx_res) + len("\\end{resumo}")
        base = base[:idx_res] + resumo_tex + base[end_res:idx_abs] + base[idx_abs:]

    abstract_tex = (
        "\\begin{resumo}[Abstract]\n\\begin{otherlanguage*}{english}\n\n"
        + abstract_body
        + "\n\n\\vspace{\\onelineskip}\n\n\\noindent\n"
        + f"\\textbf{{Keywords}}: {keywords}.\n"
        + "\\end{otherlanguage*}\n\\end{resumo}"
    )
    idx_abs = base.find("\\begin{resumo}[Abstract]")
    if idx_abs >= 0:
        end_abs = base.find("\\end{resumo}", idx_abs) + len("\\end{resumo}")
        base = base[:idx_abs] + abstract_tex + base[end_abs:]
    PRETEXTUAL.write_text(base, encoding="utf-8")


def write_appendices(path: Path, body_md: str) -> None:
    body_md = re.sub(r"^# Apêndice A[^\n]*\n", "", body_md, count=1)
    parts = re.split(r"^# Apêndice B[^\n]*", body_md, maxsplit=1, flags=re.M)
    a_md = parts[0]
    b_md = parts[1] if len(parts) > 1 else ""
    b_md = re.split(r"<!-- FIM", b_md)[0]
    a_tex = convert_block(a_md)
    b_tex = convert_block(b_md)
    content = (
        "\\chapter{Protocolo de anotação orientada à empresa}\n"
        "\\label{ap:protocolo}\n\n"
        + a_tex
        + "\n\\chapter{Rastreabilidade experimental}\n"
        "\\label{ap:rastreabilidade}\n\n"
        + b_tex
        + "\n"
    )
    path.write_text(content, encoding="utf-8")


def main() -> int:
    global TABLE_COUNTER
    TABLE_COUNTER = 0
    if not MD.is_file():
        print(
            f"Arquivo mestre ausente ({MD.name}). "
            "Edite docs/Dissertacao_PPGCC/*.tex; o markdown de reescrita foi retirado.",
            file=sys.stderr,
        )
        return 1
    text = MD.read_text(encoding="utf-8")
    body = extract_body(text)
    chunks = split_chapters(body)

    pre = chunks.get("__pretext__", "")
    if pre:
        write_pretextual(pre)
        print("Updated 00_pretextual.tex")

    for pat, fname, title, label in CHAPTERS:
        md_chunk = chunks.get(pat, "")
        if not md_chunk:
            print(f"AVISO: capítulo vazio {fname}", file=sys.stderr)
        write_chapter(OUT / fname, title, label, md_chunk)
        print(f"Wrote {fname}")

    app = chunks.get("__appendix__", "")
    if app:
        write_appendices(OUT / "99_apendices.tex", app)
        print("Wrote 99_apendices.tex")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
