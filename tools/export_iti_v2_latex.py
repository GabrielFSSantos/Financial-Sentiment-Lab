#!/usr/bin/env python3
"""Gera trecho LaTeX a partir de métricas ITI-v2 (run de produção)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    run_id = metrics.get("run_id", run_dir.name)
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
                f"Spearman = {_fmt_float(row.get('estimate'))} ($p={_fmt_float(row.get('p_value'))}$)."
            )

    return f"""% Gerado por tools/export_iti_v2_latex.py — não editar manualmente
\\subsection{{Campanha ITI-v2 (\\texttt{{{run_id}}})}}
\\label{{subsec:iti-v2-campanha}}

Execução exploratória do protocolo ITI-v2 (visão \\texttt{{entity\\_context\\_v1}}, corpus canônico P02, FinBERT-PT-BR com pesos fixados por SHA). Foram processadas {manifest.get("n_ok", "---")} notícias com probabilidades válidas; modo de execução: \\textbf{{{mode}}}.

Para o sinal semanal \\texttt{{{metrics.get("signal_column", "iti_v2_h7")}}} e horizonte $h={metrics.get("horizon_weeks", 1)}$ semana(s), a correlação de Spearman no painel alinhado ($n={metrics.get("n_panel", "---")}$ semanas com overlap) foi {_fmt_float(metrics.get("estimate"))}, com intervalo de confiança de 95\\% [{_fmt_float(metrics.get("ci_low"))}; {_fmt_float(metrics.get("ci_high"))}] e $p$ bootstrap {_fmt_float(metrics.get("p_value"))} (Holm: {_fmt_float(metrics.get("p_holm"))}).{holdout_line} Não se interpreta como confirmação da hipótese: a referência humana independente segue pendente (Capítulo~\\ref{{cap:metodologia}}).

\\noindent\\textit{{Fonte:}} artefatos em \\texttt{{outputs/campaigns/iti\\_v2/{run_id}/}}; métricas em \\texttt{{metrics\\_primary.json}}.
"""


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "iti_v2_prod_20261022"
    run_dir = ROOT / "outputs/campaigns/iti_v2" / run_id
    if not (run_dir / "metrics_primary.json").is_file():
        print(f"Run ausente: {run_dir}", file=sys.stderr)
        return 1
    snippet = build_snippet(run_dir)
    out = ROOT / "docs/Dissertacao_PPGCC/generated/iti_v2_results_snippet.tex"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(snippet, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
