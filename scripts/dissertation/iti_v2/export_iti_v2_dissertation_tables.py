#!/usr/bin/env python3
"""Exporta tabelas LaTeX (longtable) a partir de artefatos ITI-v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "docs/Dissertacao_PPGCC/generated/tables"


def _tex_escape(value: object) -> str:
    text = str(value).replace("_", r"\_")
    return text


def write_secondary_table(run_dir: Path) -> Path | None:
    sec_path = run_dir / "table_secondary.csv"
    if not sec_path.is_file():
        return None
    import pandas as pd

    df = pd.read_csv(sec_path)
    lines = [
        "% Gerado por scripts/dissertation/iti_v2/export_iti_v2_dissertation_tables.py",
        r"\begin{longtable}{@{}p{3.2cm}rrrr@{}}",
        r"\caption{Família secundária do ITI (Holm; painel completo; exploratório)}\label{tab:iti-secondary} \\",
        r"\toprule",
        r"Contraste & $\Delta$ & IC inf. & IC sup. & $p_{\mathrm{Holm}}$ \\",
        r"\midrule",
        r"\endfirsthead",
        r"\multicolumn{5}{c}{\tablename\ \thetable\ -- continuação} \\",
        r"\toprule",
        r"Contraste & $\Delta$ & IC inf. & IC sup. & $p_{\mathrm{Holm}}$ \\",
        r"\midrule",
        r"\endhead",
    ]
    def _num(value: object) -> str:
        if value is None or value == "":
            return "---"
        try:
            return f"{float(value):.3f}"
        except (TypeError, ValueError):
            return "---"

    for _, row in df.iterrows():
        lines.append(
            f"{_tex_escape(row.get('contrast_id', ''))} & "
            f"{_num(row.get('delta'))} & "
            f"{_num(row.get('ci_low'))} & "
            f"{_num(row.get('ci_high'))} & "
            f"{_num(row.get('p_holm'))} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", ""])
    out = OUT_DIR / "iti_v2_table_secondary.tex"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "iti_v2_prod_20261022"
    run_dir = ROOT / "outputs/campaigns/iti_v2" / run_id
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = write_secondary_table(run_dir)
    if path is None:
        print("Tabela secundária ausente", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
