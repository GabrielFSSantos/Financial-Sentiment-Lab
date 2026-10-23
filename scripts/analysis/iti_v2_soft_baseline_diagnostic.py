#!/usr/bin/env python3
"""Diagnóstico exploratório do baseline Soft (campanha ITI-v2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

PRIMARY_CANDIDATE = "iti_v2_h7"
PRIMARY_BASELINE = "soft_input"
PRIMARY_TARGET = "future_log_return_1"


def _primary_paired_mask(panel: pd.DataFrame) -> pd.DataFrame:
    work = panel[[PRIMARY_CANDIDATE, PRIMARY_BASELINE, PRIMARY_TARGET]]
    masked = panel.loc[work.notna().all(axis=1)].copy()
    if "warmup" in masked.columns:
        masked = masked.loc[masked["warmup"] != True].copy()
    if "period_end" in masked.columns:
        masked = masked.sort_values("period_end").reset_index(drop=True)
    return masked


def run(run_dir: Path) -> dict[str, object]:
    daily_path = run_dir / "iti_daily.csv"
    panel_path = run_dir / "aligned_panel.csv"
    if not daily_path.is_file():
        raise FileNotFoundError(daily_path)
    daily = pd.read_csv(daily_path)
    eligible = daily.loc[daily["coverage_status"] == "eligible"].copy()
    n_days = len(eligible)
    no_news = int((eligible["n_articles"].fillna(0) == 0).sum())
    soft_zero_daily = int((eligible["soft_input"].fillna(0).abs() < 1e-12).sum())
    report: dict[str, object] = {
        "run_dir": str(run_dir),
        "eligible_days": n_days,
        "days_without_articles": no_news,
        "fraction_days_without_articles": round(no_news / n_days, 4) if n_days else None,
        "days_soft_input_near_zero": soft_zero_daily,
        "fraction_soft_near_zero_daily": round(soft_zero_daily / n_days, 4) if n_days else None,
        "articles_per_day_mean": round(float(eligible["n_articles"].fillna(0).mean()), 3),
        "articles_per_day_median": float(eligible["n_articles"].fillna(0).median()),
        "articles_per_day_p90": float(eligible["n_articles"].fillna(0).quantile(0.9)),
    }
    if panel_path.is_file():
        panel = pd.read_csv(panel_path)
        paired = _primary_paired_mask(panel)
        soft = paired[PRIMARY_BASELINE].astype(float)
        n_paired = int(len(paired))
        soft_zero_weeks = int((soft.abs() < 1e-12).sum())
        report["primary_paired_n"] = n_paired
        report["primary_paired_soft_zero_weeks"] = soft_zero_weeks
        report["primary_paired_fraction_soft_zero"] = (
            round(soft_zero_weeks / n_paired, 4) if n_paired else None
        )
        report["primary_paired_weeks_without_articles_at_cutoff"] = int(
            (paired["n_articles"].fillna(0) == 0).sum()
        )
        report["primary_paired_unique_soft_values"] = int(soft.nunique())
        report["primary_paired_unique_iti_h7_values"] = int(
            paired[PRIMARY_CANDIDATE].astype(float).nunique()
        )
        report["primary_paired_spearman_tie_slots_soft"] = n_paired - int(soft.nunique())
        report["primary_paired_spearman_tie_slots_iti"] = n_paired - int(
            paired[PRIMARY_CANDIDATE].astype(float).nunique()
        )
        if "future_log_return_1" in panel.columns:
            full = panel.loc[panel[PRIMARY_TARGET].notna()].copy()
            if "warmup" in full.columns:
                full = full.loc[full["warmup"] != True]
            if len(full):
                wsoft = full[PRIMARY_BASELINE].astype(float)
                wz = int((wsoft.abs() < 1e-12).sum())
                report["weekly_aligned_n_excl_warmup"] = int(len(full))
                report["weekly_aligned_soft_zero"] = wz
                report["weekly_aligned_fraction_soft_zero"] = round(wz / len(full), 4)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", nargs="?", default="iti_v2_prod_20261022")
    parser.add_argument(
        "--out",
        type=Path,
        help="JSON de saída (opcional)",
    )
    args = parser.parse_args(argv)
    run_dir = ROOT / "outputs/campaigns/iti_v2" / args.run_id
    payload = run(run_dir)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
