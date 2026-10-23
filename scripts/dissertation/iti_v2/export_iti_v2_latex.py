#!/usr/bin/env python3
"""Gera trechos LaTeX a partir de métricas ITI-v2 (run de produção)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ROOT / "docs/Dissertacao_PPGCC/generated"


def _tex_id(run_id: str) -> str:
    return run_id.replace("_", r"\_")


def _fmt_float(value: object, digits: int = 3) -> str:
    if value is None:
        return "---"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "---"
    return f"{number:.{digits}f}".replace(".", ",")


def build_snippet(run_dir: Path) -> str:
    metrics = json.loads((run_dir / "metrics_primary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "inference_manifest.json").read_text(encoding="utf-8"))
    registry_path = run_dir / "result_registry.json"
    n_articles = manifest.get("n_ok")
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        counts = registry.get("prediction_counts") or {}
        if counts.get("n_articles_ok"):
            n_articles = counts["n_articles_ok"]
    delta = {}
    delta_path = run_dir / "metrics_primary_delta.json"
    if delta_path.is_file():
        delta = json.loads(delta_path.read_text(encoding="utf-8"))

    run_id = metrics.get("run_id", run_dir.name)
    run_id_tex = _tex_id(str(run_id))
    mode = metrics.get("execution_mode", "exploratory")
    holdout_line = ""
    holdout_path = run_dir / "metrics_holdout.json"
    if holdout_path.is_file():
        hold = json.loads(holdout_path.read_text(encoding="utf-8"))
        rows = hold.get("horizons") or []
        if rows:
            row = rows[0]
            holdout_line = (
                f" No holdout temporal (12 semanas civis, $n={row.get('n', '---')}$ semanas no painel), "
                f"Spearman marginal = {_fmt_float(row.get('estimate'))} ($p={_fmt_float(row.get('p_value'))}$)."
            )

    delta_block = ""
    if delta.get("status") == "ok":
        delta_block = (
            f"O contraste principal pré-registrado ($\\Delta = \\rho_{{ITI\\text{{-}}H7}} - \\rho_{{Soft}}$, "
            f"Spearman, $h=1$) foi {_fmt_float(delta.get('delta'))} "
            f"(IC 95\\% [{_fmt_float(delta.get('ci_low'))}; {_fmt_float(delta.get('ci_high'))}], "
            f"$p$ bootstrap {_fmt_float(delta.get('p_value'))}, $n={delta.get('n', '---')}$). "
            f"Coeficientes marginais: $\\rho_{{candidato}}={_fmt_float(delta.get('rho_candidate'))}$, "
            f"$\\rho_{{baseline}}={_fmt_float(delta.get('rho_baseline'))}$. "
        )

    return f"""% Gerado por scripts/dissertation/iti_v2/export_iti_v2_latex.py — não editar manualmente
\\subsection{{Estimadores da rodada exploratória (outubro de 2026)}}
\\label{{subsec:campanha-iti}}

Foram processadas {n_articles} notícias com probabilidades válidas na view primária \\texttt{{entity\\_context\\_v1}}; a ablação \\texttt{{document\\_v1}} e o modo \\textbf{{{mode}}} estão registrados no manifesto de execução (Apêndice~\\ref{{ap:iti-math}}).

{delta_block}A correlação marginal exploratória de Spearman entre ITI-H7 e retorno $h={metrics.get("horizon_weeks", 1)}$ no painel ($n={metrics.get("n_panel", "---")}$) foi {_fmt_float(metrics.get("estimate"))} (IC [{_fmt_float(metrics.get("ci_low"))}; {_fmt_float(metrics.get("ci_high"))}], $p={_fmt_float(metrics.get("p_value"))}$).{holdout_line}

A Tabela~\\ref{{tab:iti-secondary}} resume os oito contrastes secundários com correção de Holm. \\textbf{{Referência humana independente pendente}} (Capítulo~\\ref{{cap:metodologia}}); não interpretar como confirmação da hipótese substantiva.

\\noindent\\textit{{Fonte:}} elaboração própria a partir da avaliação temporal do ITI em outubro de 2026 (manifesto de execução e pacote de reprodutibilidade no apêndice).
"""


def build_results_macros(run_dir: Path) -> str:
    metrics = json.loads((run_dir / "metrics_primary.json").read_text(encoding="utf-8"))
    delta_path = run_dir / "metrics_primary_delta.json"
    delta = json.loads(delta_path.read_text(encoding="utf-8")) if delta_path.is_file() else {}
    return f"""% Gerado por scripts/dissertation/iti_v2/export_iti_v2_latex.py
\\newcommand{{\\ITIvTwoRunId}}{{{_tex_id(str(metrics.get("run_id", run_dir.name)))}}}
\\newcommand{{\\ITIvTwoNPanel}}{{{metrics.get("n_panel", "---")}}}
\\newcommand{{\\ITIvTwoDeltaPrimary}}{{{_fmt_float(delta.get("delta"))}}}
\\newcommand{{\\ITIvTwoDeltaP}}{{{_fmt_float(delta.get("p_value"))}}}
\\newcommand{{\\ITIvTwoRhoMarginal}}{{{_fmt_float(metrics.get("estimate"))}}}
"""


def build_figures_snippet() -> str:
    fig_dir = GENERATED / "figures/iti_v2"
    names = (
        ("figure_daily_signal.png", "Sinal diário Soft e ITI-H7 com volume de notícias."),
        ("figure_h_sensitivity.png", "Sensibilidade da meia-vida (H2, H7, H14) na mesma inferência."),
        ("figure_delta_intervals.png", "Intervalos bootstrap dos contrastes secundários (Holm)."),
    )
    lines = [
        "% Gerado por scripts/dissertation/iti_v2/export_iti_v2_latex.py",
        "\\subsubsection{Figuras da avaliação temporal}",
    ]
    for index, (filename, caption) in enumerate(names, start=1):
        path = fig_dir / filename
        if not path.is_file():
            continue
        lines.extend(
            [
                "\\begin{figure}[htbp]",
                "\\centering",
                f"\\includegraphics[width=0.92\\linewidth]{{generated/figures/iti_v2/{filename}}}",
                f"\\caption{{{caption}}}",
                f"\\label{{fig:iti-campanha-{index}}}",
                "\\end{figure}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "iti_v2_prod_20261022"
    run_dir = ROOT / "outputs/campaigns/iti_v2" / run_id
    if not (run_dir / "metrics_primary.json").is_file():
        print(f"Run ausente: {run_dir}", file=sys.stderr)
        return 1
    GENERATED.mkdir(parents=True, exist_ok=True)
    snippet_path = GENERATED / "iti_v2_results_snippet.tex"
    snippet_path.write_text(build_snippet(run_dir), encoding="utf-8")
    macros_path = GENERATED / "results_macros.tex"
    macros_path.write_text(build_results_macros(run_dir), encoding="utf-8")
    figures_path = GENERATED / "iti_v2_figures_snippet.tex"
    figures_path.write_text(build_figures_snippet(), encoding="utf-8")
    print(snippet_path)
    print(macros_path)
    print(figures_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
