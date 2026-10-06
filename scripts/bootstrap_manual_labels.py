#!/usr/bin/env python3
"""Bootstrap formal manual_labels_100.csv from exploratory archive (one-shot / re-run)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules.evaluation.core.settings import load_evaluation_settings

LABEL_MAP = {
    "POS": "POSITIVE",
    "NEG": "NEGATIVE",
    "NEU": "NEUTRAL",
    "POSITIVE": "POSITIVE",
    "NEGATIVE": "NEGATIVE",
    "NEUTRAL": "NEUTRAL",
}


def _tipologia_from_notas(notas: str) -> str:
    text = (notas or "").lower()
    if "tangencial" in text or "menção" in text:
        return "mencao_tangencial"
    if "roundup" in text or "setor" in text or "geral" in text or "ibovespa" in text:
        return "roundup_agenda"
    return "focal_sabesp"


def bootstrap(
    *,
    source: Path,
    output: Path,
    anotador: str,
    versao: str,
    draft_rows: int = 35,
) -> None:
    frame = pd.read_csv(source)
    rows = []
    for index, row in frame.iterrows():
        manual = str(row.get("rotulo_manual", "")).strip().upper()
        impacto = LABEL_MAP.get(manual, "")
        notas = str(row.get("notas", "") or "")
        is_draft = index < draft_rows and manual
        rows.append(
            {
                "news_id": row["news_id"],
                "empresa_alvo": "Sabesp",
                "tipologia": _tipologia_from_notas(notas),
                "impacto_alvo": impacto if is_draft else "",
                "sentimento_global": "",
                "ambiguo": "false",
                "rotulo_finbert": row.get("rotulo_finbert", ""),
                "rotulo_llm_juiz": "",
                "notas": (
                    f"{notas}; revisar_criterio_orientacao"
                    if is_draft and notas
                    else ("revisar_criterio_orientacao" if is_draft else notas)
                ),
                "notas_llm": "",
                "anotador": anotador if is_draft else "",
                "anotador_2": "",
                "impacto_alvo_2": "",
                "versao_protocolo": versao if is_draft else "",
            }
        )
    out = pd.DataFrame(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    filled = (out["impacto_alvo"] != "").sum()
    print(f"Gravado {output} — {filled} linhas com rascunho de impacto (revisar protocolo).")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft-rows", type=int, default=35)
    parser.add_argument("--anotador", default="Gabriel Felipe Souza Santos")
    parser.add_argument("--versao", default="2026-10-07")
    args = parser.parse_args()
    settings = load_evaluation_settings()
    source = settings.manual_labels_exploratorio_path or settings.manual_labels_path
    output = settings.manual_labels_path
    bootstrap(
        source=source,
        output=output,
        anotador=args.anotador,
        versao=args.versao,
        draft_rows=args.draft_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
