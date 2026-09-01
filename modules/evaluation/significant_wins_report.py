"""Extrai vitórias significativas (métricas de conclusão) para relatório da tese."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from modules.experiment import PROJECT_ROOT

DEFAULT_RUN_ID = "sabesp_gap2023_event_r1_alpha070"
DEFAULT_DATASET = "saneamento_sabesp_strict_event"
DEFAULT_MODEL = "finbert_ptbr"
CONCLUSION_METRICS = ("pearson", "spearman")


def _deltas_path(
    run_id: str,
    model_key: str,
    dataset_key: str,
) -> Path:
    return (
        PROJECT_ROOT
        / "outputs"
        / run_id
        / "research"
        / model_key
        / dataset_key
        / "incremental_deltas.csv"
    )


def load_significant_wins(
    run_id: str,
    *,
    model_key: str = DEFAULT_MODEL,
    dataset_key: str = DEFAULT_DATASET,
    conclusion_metrics: tuple[str, ...] = CONCLUSION_METRICS,
) -> pd.DataFrame:
    path = _deltas_path(run_id, model_key, dataset_key)
    if not path.is_file():
        raise FileNotFoundError(f"incremental_deltas ausente: {path}")

    frame = pd.read_csv(path)
    subset = frame[
        frame["metric"].isin(conclusion_metrics)
        & (frame["significant"] == True)  # noqa: E712
        & (frame["delta"] > 0)
    ].copy()
    subset = subset.sort_values(["horizon", "baseline", "metric"])
    return subset


def format_markdown(
    wins: pd.DataFrame,
    *,
    run_id: str,
    conclusion_metrics: tuple[str, ...] = CONCLUSION_METRICS,
) -> str:
    lines = [
        "# Vitórias significativas — R1 evento",
        "",
        f"Run: `{run_id}` | Métricas de conclusão: {', '.join(conclusion_metrics)}.",
        "",
        "Caveat: as **24 comparações** por run (4 baselines × 2 métricas × 3 horizontes) "
        "não são testes independentes. Com n≈24 semanas, 2 vitórias significativas "
        "cabem em **busca múltipla** sem rejeitar H₀ global.",
        "",
    ]
    if wins.empty:
        lines.append("_Nenhuma vitória significativa nas métricas de conclusão._")
        return "\n".join(lines)

    lines.extend(
        [
            "| Horizonte (sem.) | Baseline | Métrica | ITI | Baseline | Δ | p-value |",
            "|------------------|----------|---------|-----|----------|---|---------|",
        ]
    )
    for _, row in wins.iterrows():
        lines.append(
            f"| {int(row['horizon'])} | {row['baseline']} | {row['metric']} | "
            f"{float(row['iti_value']):.3f} | {float(row['baseline_value']):.3f} | "
            f"{float(row['delta']):.3f} | {float(row['p_value']):.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(
    run_id: str = DEFAULT_RUN_ID,
    *,
    output_dir: Path | None = None,
) -> Path:
    wins = load_significant_wins(run_id)
    output = output_dir or (PROJECT_ROOT / "outputs/campaigns/sabesp_marco2")
    output.mkdir(parents=True, exist_ok=True)

    md_path = output / "significant_wins_r1_event.md"
    md_path.write_text(format_markdown(wins, run_id=run_id), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "conclusion_metrics": list(CONCLUSION_METRICS),
        "significant_win_count": len(wins),
        "wins": wins.to_dict(orient="records"),
    }
    (output / "significant_wins_r1_event.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vitórias significativas R1 evento")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs/campaigns/sabesp_marco2"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = write_report(args.run_id, output_dir=Path(args.output_dir))
    wins = load_significant_wins(args.run_id)
    print(f"Vitórias significativas: {len(wins)}")
    print(f"Relatório: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
