#!/usr/bin/env python3
"""Exporta tabelas LaTeX a partir de artefatos ITI-v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "docs/Dissertacao_PPGCC/generated/tables"
_SCRIPT_DIR = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(_SCRIPT_DIR))
from _contrast_labels import label_for  # noqa: E402


def _tex_escape(value: object) -> str:
    return str(value).replace("_", r"\_")


def _num(value: object, digits: int = 3) -> str:
    if value is None or value == "":
        return "---"
    try:
        return f"{float(value):.{digits}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "---"


def write_primary_table(run_dir: Path) -> Path | None:
    delta_path = run_dir / "metrics_primary_delta.json"
    if not delta_path.is_file():
        return None
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    metrics_path = run_dir / "metrics_primary.json"
    n_panel = "---"
    if metrics_path.is_file():
        n_panel = json.loads(metrics_path.read_text(encoding="utf-8")).get("n_panel", "---")
    if delta.get("status") != "ok":
        return None
    lines = [
        "% Gerado por scripts/dissertation/iti_v2/export_iti_v2_dissertation_tables.py",
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Contraste principal pré-especificado (Spearman; $h=1$ semana; painel SBSP3).}",
        r"\label{tab:iti-primary}",
        r"\begin{tabularx}{\textwidth}{@{}lrrrrrr@{}}",
        r"\toprule",
        r"$n$ & $\rho_{\mathrm{ITI\text{-}H7}}$ & $\rho_{\mathrm{Soft}}$ & $\Delta$ & IC inf. & IC sup. & $p$ \\",
        r"\midrule",
        (
            f"{delta.get('n', '---')} & "
            f"{_num(delta.get('rho_candidate'))} & "
            f"{_num(delta.get('rho_baseline'))} & "
            f"{_num(delta.get('delta'))} & "
            f"{_num(delta.get('ci_low'))} & "
            f"{_num(delta.get('ci_high'))} & "
            f"{_num(delta.get('p_value'))} \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\vspace{0.4em}",
        r"{\footnotesize Fonte: campanha exploratória de outubro de 2026. "
        r"$n$: semanas com retorno futuro completo, fora do período inicial de amortecimento da condição inicial (70 dias civis; ver Cap.~\ref{cap:metodologia}) "
        + f"(painel alinhado: {n_panel} semanas; 10 semanas de aquecimento excluídas)."
        + r"}",
        r"\end{table}",
        "",
    ]
    out = OUT_DIR / "iti_v2_table_primary.tex"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_secondary_table(run_dir: Path) -> Path | None:
    sec_path = run_dir / "table_secondary.csv"
    if not sec_path.is_file():
        return None
    import pandas as pd

    df = pd.read_csv(sec_path)
    n_primary = "---"
    delta_path = run_dir / "metrics_primary_delta.json"
    if delta_path.is_file():
        n_primary = json.loads(delta_path.read_text(encoding="utf-8")).get("n", "---")
    lines = [
        "% Gerado por scripts/dissertation/iti_v2/export_iti_v2_dissertation_tables.py",
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Família secundária do ITI (IC bootstrap nominal de 95\%; $p_{\mathrm{Holm}}$ corrigido por família; exploratório).}",
        r"\label{tab:iti-secondary}",
        r"\begin{tabularx}{\textwidth}{@{}Lrrrr@{}}",
        r"\toprule",
        r"Comparação & $\Delta\rho$ & IC inf. & IC sup. & $p_{\mathrm{Holm}}$ \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        cid = str(row.get("contrast_id", ""))
        lines.append(
            f"{label_for(cid)} & "
            f"{_num(row.get('delta'))} & "
            f"{_num(row.get('ci_low'))} & "
            f"{_num(row.get('ci_high'))} & "
            f"{_num(row.get('p_holm'))} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\vspace{0.4em}",
            (
                f"{{\\footnotesize Fonte: elaboração própria (mesma máscara do contraste principal quando $n={n_primary}$). "
                r"Intervalos: percentis bootstrap nominais de 95\%; significância familiar baseada em $p_{\mathrm{Holm}}$, não no IC.}"
            ),
            r"\end{table}",
            "",
        ]
    )
    out = OUT_DIR / "iti_v2_table_secondary.tex"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "iti_v2_prod_20261022"
    run_dir = ROOT / "outputs/campaigns/iti_v2" / run_id
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for writer in (write_primary_table, write_secondary_table):
        path = writer(run_dir)
        if path is not None:
            paths.append(path)
    if not paths:
        print("Nenhuma tabela gerada", file=sys.stderr)
        return 1
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
