"""Resumo comparativo das runs gap2023 vs Marco 1/2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.experiment import PROJECT_ROOT

REPORT_PATH = (
    PROJECT_ROOT / "outputs/campaigns/sabesp_marco2/gap2023_comparison.md"
)

RUN_SPECS: tuple[tuple[str, str, str], ...] = (
    ("sabesp_gap2023_r0_baseline", "Expandido R0 (gap 2023)", "Marco 2 R0"),
    ("sabesp_gap2023_r1_alpha070", "Expandido R1 α=0,70 (gap 2023)", "Marco 2 R1"),
    (
        "sabesp_gap2023_event_r0_baseline",
        "Evento R0 (sanity gap 2023)",
        "Marco 1 R0 / Marco 2 event",
    ),
    (
        "sabesp_gap2023_event_r1_alpha070",
        "Evento R1 α=0,70 (sanity gap 2023)",
        "Marco 1 R1 / Marco 2 event",
    ),
)

BASELINE_CONCLUSIONS: dict[str, str] = {
    "Marco 2 R0": "0/24 vitórias (0.0%), 0 significativas (0.0%)",
    "Marco 2 R1": "5/24 vitórias (20.8%), 0 significativas (0.0%)",
    "Marco 1 R0 / Marco 2 event": "5/24 vitórias (20.8%), 0 significativas (0.0%)",
    "Marco 1 R1 / Marco 2 event": "10/24 vitórias (41.7%), 2 significativas (8.3%)",
}


def _load_conclusion(run_id: str) -> str:
    summary_path = PROJECT_ROOT / "outputs" / run_id / "research" / "research_summary.json"
    if not summary_path.is_file():
        return "_run ausente_"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return str(payload.get("conclusion", "_sem conclusão_"))


def _load_row_count(run_id: str) -> str:
    summary_path = PROJECT_ROOT / "outputs" / run_id / "research" / "research_summary.json"
    if not summary_path.is_file():
        return "—"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    experiment = payload.get("experiment_summary") or {}
    combinations = experiment.get("combinations") or []
    if not combinations:
        return "—"
    return str(combinations[0].get("row_count", "—"))


def build_report() -> str:
    lines = [
        "# Comparação gap 2023 vs Marco 1/2",
        "",
        "Runs novas (`sabesp_gap2023_*`) no corpus **1.254** artigos. "
        "Runs históricas do Marco 2 permanecem em `outputs/sabesp_marco2_*`.",
        "",
        "| Run | Artigos inferidos | Conclusão ITI | Baseline histórico |",
        "|-----|-------------------|---------------|-------------------|",
    ]
    for run_id, label, baseline_key in RUN_SPECS:
        lines.append(
            f"| {label} (`{run_id}`) | {_load_row_count(run_id)} | "
            f"{_load_conclusion(run_id)} | {BASELINE_CONCLUSIONS[baseline_key]} |"
        )
    lines.extend(
        [
            "",
            "## Decisão de janela (Trilha A)",
            "",
            "| Papel na tese | Janela |",
            "|---------------|--------|",
            "| **Resultado principal** | Evento nov/2023–abr/2024 (R1 α=0,70) |",
            "| **Robustez / limitação** | Expandido mai/2022–abr/2024 (incl. lacuna 2023) |",
            "",
            "O sanity de evento deve **reproduzir** Marco 1 (~41,7%, 2 sig.). "
            "O expandido mede se a lacuna jan–abr/2023 altera o quadro do Marco 2 (20,8%).",
            "",
        ]
    )
    return "\n".join(lines)


def write_report() -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    return REPORT_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resumo gap2023 vs Marco 1/2")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write", help="Grava gap2023_comparison.md")
    sub.add_parser("print", help="Imprime relatório no stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report()
    if args.command == "write":
        path = write_report()
        print(f"Relatório: {path}")
        return 0
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
