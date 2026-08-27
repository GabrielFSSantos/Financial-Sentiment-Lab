"""Atualiza métricas de uma run no manifest a partir do research summary."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.manifest import update_run_results


def _load_research_summary(run_id: str) -> dict:
    summary_path = PROJECT_ROOT / "outputs" / run_id / "research" / "research_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Research summary não encontrado: {summary_path}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _extract_win_rate(summary: dict) -> float | None:
    combinations = summary.get("combinations") or []
    if not combinations:
        conclusion = summary.get("conclusion", "")
        match = re.search(r"(\d+)/(\d+) vitórias", conclusion)
        if match:
            wins, total = int(match.group(1)), int(match.group(2))
            return wins / total if total else None
        return None

    totals = {"wins": 0, "comparisons": 0}
    for combination in combinations:
        for stats in (combination.get("predictor_stats") or {}).values():
            totals["wins"] += int(stats.get("wins", 0))
            totals["comparisons"] += int(stats.get("comparisons", 0))

    if totals["comparisons"] == 0:
        return None
    return totals["wins"] / totals["comparisons"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)

    summary = _load_research_summary(args.run_id)
    win_rate = _extract_win_rate(summary)
    metrics_summary = {
        "win_rate": win_rate,
        "conclusion": summary.get("conclusion"),
        "combination_count": summary.get("combination_count"),
        "combinations": summary.get("combinations"),
    }

    baseline_id = "sabesp_r0_baseline"
    delta: dict = {}
    if args.run_id != baseline_id:
        try:
            baseline_rate = _extract_win_rate(_load_research_summary(baseline_id))
            if win_rate is not None and baseline_rate is not None:
                delta = {"win_rate_delta_vs_r0": win_rate - baseline_rate}
        except FileNotFoundError:
            delta = {"note": "baseline R0 ainda não executado"}

    update_run_results(
        Path(args.manifest),
        run_id=args.run_id,
        metrics_summary=metrics_summary,
        delta_vs_baseline=delta,
        interpretation=summary.get("conclusion", ""),
        status="completed",
    )
    print(f"Manifest atualizado: {args.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
