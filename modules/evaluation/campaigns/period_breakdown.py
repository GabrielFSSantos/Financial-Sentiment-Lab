"""Análise exploratória ITI×retorno por subperíodo (aligned_panel)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modules.experiment import PROJECT_ROOT


def _resolve_panel_path(
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
        / "aligned_panel.csv"
    )


def _pick_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        if name in frame.columns:
            return name
    return None


def assign_temporal_bucket(period_end: pd.Timestamp) -> str:
    """Três buckets: 2022, jan–abr/2023 (lacuna), nov/23–abr/24 (evento)."""
    if period_end.year == 2022:
        return "pre_evento_2022"
    if period_end.year == 2023 and period_end.month <= 4:
        return "interregno_2023q1"
    return "evento_nov23_abr24"


def analyze_periods(panel: pd.DataFrame) -> pd.DataFrame:
    period_col = _pick_column(
        panel,
        ("period_end", "period_end_x", "week_end"),
    )
    iti_col = _pick_column(
        panel,
        ("iti_liquido", "iti_liquido_last_x", "iti_liquido_last"),
    )
    ret_col = _pick_column(
        panel,
        (
            "future_log_return_1",
            "future_return_h1_x",
            "future_return_1w",
            "future_log_return_h1",
            "target_return_h1",
        ),
    )
    if not period_col or not iti_col or not ret_col:
        raise ValueError(
            "aligned_panel sem colunas esperadas de período, ITI ou retorno futuro."
        )

    working = panel[[period_col, iti_col, ret_col]].copy()
    working.columns = ["period_end", "iti", "future_return"]
    working["period_end"] = pd.to_datetime(working["period_end"], errors="coerce")
    working = working.dropna(subset=["period_end", "iti", "future_return"])
    working["bucket"] = working["period_end"].apply(assign_temporal_bucket)

    rows: list[dict[str, object]] = []
    for bucket, group in working.groupby("bucket"):
        if len(group) < 3:
            continue
        rows.append(
            {
                "bucket": bucket,
                "weeks": len(group),
                "pearson": group["iti"].corr(group["future_return"], method="pearson"),
                "spearman": group["iti"].corr(group["future_return"], method="spearman"),
            }
        )
    return pd.DataFrame(rows)


def format_markdown(summary: pd.DataFrame, *, panel_path: Path) -> str:
    lines = [
        "# Análise por subperíodo",
        "",
        f"Fonte: `{panel_path.relative_to(PROJECT_ROOT)}`",
        "",
        "| Subperíodo | Semanas | Pearson ITI×retorno h=1 | Spearman |",
        "|------------|---------|------------------------|----------|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['bucket']} | {int(row['weeks'])} | "
            f"{row['pearson']:.3f} | {row['spearman']:.3f} |"
        )
    lines.append("")
    lines.extend(
        [
            "",
            "_Buckets: `pre_evento_2022` (2022), `interregno_2023q1` (jan–abr/2023), "
            "`evento_nov23_abr24` (nov/2023–abr/2024). O bucket antigo "
            "`evento_2023_2024` misturava a lacuna 2023 com o evento._",
            "",
            "_Exploratório: h=1 semana, coluna de retorno futuro disponível no painel._",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ITI×retorno por subperíodo")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", default="finbert_ptbr")
    parser.add_argument("--dataset", required=True)
    parser.add_argument(
        "--output",
        default=str(
            PROJECT_ROOT / "outputs/campaigns/sabesp_marco2/period_breakdown.md"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    panel_path = _resolve_panel_path(args.run_id, args.model, args.dataset)
    if not panel_path.is_file():
        raise SystemExit(f"Painel não encontrado: {panel_path}")

    panel = pd.read_csv(panel_path)
    summary = analyze_periods(panel)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(format_markdown(summary, panel_path=panel_path), encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"\nRelatório: {output}")


if __name__ == "__main__":
    main()
