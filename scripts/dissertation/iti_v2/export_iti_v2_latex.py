#!/usr/bin/env python3
"""Gera trechos LaTeX a partir de métricas ITI-v2 (run de produção)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ROOT / "docs/Dissertacao_PPGCC/generated"
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
from _contrast_labels import label_for  # noqa: E402  # type: ignore[import-not-found]


def _fmt_float(value: object, digits: int = 3) -> str:
    if value is None:
        return "---"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "---"
    return f"{number:.{digits}f}".replace(".", ",")


def _holdout_sentence(run_dir: Path) -> str:
    holdout_path = run_dir / "metrics_holdout.json"
    lock_path = run_dir / "protocol_lock_ref.json"
    if not holdout_path.is_file():
        return ""
    hold = json.loads(holdout_path.read_text(encoding="utf-8"))
    rows = hold.get("horizons") or []
    if not rows:
        return ""
    row = rows[0]
    n_ho = row.get("n", "---")
    rule = "reserva de notícias por calendário"
    cutoff = ""
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        ho = (lock.get("lock") or {}).get("holdout_status") or {}
        if ho.get("selection_rule"):
            rule = str(ho["selection_rule"]).replace("_", " ")
        if ho.get("cutoff_date_inclusive"):
            cutoff = str(ho["cutoff_date_inclusive"])[:10]
    dev_n = ""
    dev_path = run_dir / "metrics_development.json"
    if dev_path.is_file():
        dev = json.loads(dev_path.read_text(encoding="utf-8"))
        dev_rows = dev.get("horizons") or []
        if dev_rows:
            dev_n = str(dev_rows[0].get("n", ""))
    parts = [
        f"No subpainel de holdout exploratório ($n={n_ho}$ semanas alinhadas de SBSP3",
    ]
    if cutoff:
        parts.append(f", após corte em {cutoff}")
    parts.append(
        f"; regra de reserva no corpus: {rule}"
    )
    if dev_n:
        parts.append(f"; desenvolvimento: $n={dev_n}$ semanas")
    parts.append(
        f"), a correlação marginal de Spearman ITI-H7 com retorno $h=1$ foi "
        f"{_fmt_float(row.get('estimate'))} ($p={_fmt_float(row.get('p_value'))}$)."
    )
    return "".join(parts)


def _holdout_delta_sentence(run_dir: Path) -> str:
    path = run_dir / "metrics_holdout_contrasts.json"
    if not path.is_file():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("execution_mode") != "exploratory":
        return ""
    test = data.get("primary_test") or {}
    if test.get("status") != "ok":
        return ""
    delta_path = run_dir / "metrics_primary_delta.json"
    primary = json.loads(delta_path.read_text(encoding="utf-8")) if delta_path.is_file() else {}
    p_ho = test.get("p_value")
    caveat = (
        "Esse subpainel é exploratório e não promove a hipótese principal"
        if p_ho is not None and float(p_ho) < 0.05
        else "Esse subpainel é exploratório e não substitui o contraste canônico no painel completo"
    )
    return (
        f" No mesmo subpainel, o $\\Delta\\rho$ pré-registrado (ITI-H7 menos Soft, $h=1$) "
        f"foi {_fmt_float(test.get('delta'))} "
        f"(IC 95\\% [{_fmt_float(test.get('ci_low'))}; {_fmt_float(test.get('ci_high'))}], "
        f"$p$ bootstrap {_fmt_float(test.get('p_value'))}, $n={test.get('n', '---')}$). "
        f"{caveat}: o contraste canônico no painel completo permanece inconclusivo "
        f"($n={primary.get('n', '---')}$, $p$ bootstrap {_fmt_float(primary.get('p_value'))}); "
        "a reserva de notícias antecede a referência humana independente (P06) e não foi analisada "
        "com correção de multiplicidade adicional além do desenho exploratório."
    )


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

    holdout_line = _holdout_sentence(run_dir) + _holdout_delta_sentence(run_dir)

    delta_block = ""
    if delta.get("status") == "ok":
        delta_block = (
            f"O contraste principal pré-registrado ($\\Delta\\rho = \\rho_{{\\mathrm{{ITI\\text{{-}}H7}}}} "
            f"- \\rho_{{\\mathrm{{Soft}}}}$, Spearman, $h=1$) foi {_fmt_float(delta.get('delta'))} "
            f"(IC 95\\% [{_fmt_float(delta.get('ci_low'))}; {_fmt_float(delta.get('ci_high'))}], "
            f"$p$ bootstrap {_fmt_float(delta.get('p_value'))}, $n={delta.get('n', '---')}$ semanas). "
            f"Coeficientes marginais no mesmo universo pareado: "
            f"$\\rho_{{\\mathrm{{ITI\\text{{-}}H7}}}}={_fmt_float(delta.get('rho_candidate'))}$, "
            f"$\\rho_{{\\mathrm{{Soft}}}}={_fmt_float(delta.get('rho_baseline'))}$. "
        )

    marginal = (
        f"A correlação marginal exploratória de Spearman entre ITI-H7 e retorno "
        f"$h={metrics.get('horizon_weeks', 1)}$ no painel completo alinhado "
        f"($n={metrics.get('n_panel', '---')}$ semanas de SBSP3, antes de excluir aquecimento) "
        f"foi {_fmt_float(metrics.get('estimate'))} "
        f"(IC [{_fmt_float(metrics.get('ci_low'))}; {_fmt_float(metrics.get('ci_high'))}], "
        f"$p={_fmt_float(metrics.get('p_value'))}$)."
    )

    return f"""% Gerado por scripts/dissertation/iti_v2/export_iti_v2_latex.py — não editar manualmente
\\subsection{{Estimadores da rodada exploratória (outubro de 2026)}}
\\label{{subsec:campanha-iti}}

Foram processadas {n_articles} notícias com probabilidades válidas no recorte contextual da empresa-alvo; a ablação com texto integral e o modo exploratório constam do registro da execução (Apêndice~\\ref{{ap:rastreabilidade}}).

{delta_block}{marginal} {holdout_line}

A Tabela~\\ref{{tab:iti-primary}} resume o contraste principal; a Tabela~\\ref{{tab:iti-secondary}} reúne os oito contrastes secundários com correção de Holm. A referência humana independente permanece pendente (Capítulo~\\ref{{cap:metodologia}}); os intervalos não confirmam a hipótese substantiva de associação superior do ITI-H7.

\\noindent\\textit{{Fonte:}} elaboração própria a partir da avaliação temporal do ITI em outubro de 2026.
"""


def build_results_macros(run_dir: Path) -> str:
    metrics = json.loads((run_dir / "metrics_primary.json").read_text(encoding="utf-8"))
    delta_path = run_dir / "metrics_primary_delta.json"
    delta = json.loads(delta_path.read_text(encoding="utf-8")) if delta_path.is_file() else {}
    return f"""% Gerado por scripts/dissertation/iti_v2/export_iti_v2_latex.py
\\newcommand{{\\ITIvTwoNPanel}}{{{metrics.get("n_panel", "---")}}}
\\newcommand{{\\ITIvTwoDeltaPrimary}}{{{_fmt_float(delta.get("delta"))}}}
\\newcommand{{\\ITIvTwoDeltaP}}{{{_fmt_float(delta.get("p_value"))}}}
\\newcommand{{\\ITIvTwoRhoMarginal}}{{{_fmt_float(metrics.get("estimate"))}}}
"""


def build_figures_snippet() -> str:
    fig_dir = GENERATED / "figures/iti_v2"
    figures = (
        ("figure_daily_signal.png", "Sinal diário Soft e ITI-H7 com volume de notícias elegíveis."),
        ("figure_h_sensitivity.png", "Sensibilidade da meia-vida (H=2, 7 e 14 dias) na mesma inferência."),
        ("figure_delta_intervals.png", "Intervalos bootstrap dos contrastes secundários (Holm)."),
    )
    lines = ["% Gerado por scripts/dissertation/iti_v2/export_iti_v2_latex.py"]
    for index, (filename, caption) in enumerate(figures, start=1):
        path = fig_dir / filename
        if not path.is_file():
            continue
        width = "0.92\\linewidth" if index == 1 else "0.88\\linewidth"
        lines.extend(
            [
                "\\begin{figure}[htbp]",
                "\\centering",
                f"\\includegraphics[width={width}]{{generated/figures/iti_v2/{filename}}}",
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
