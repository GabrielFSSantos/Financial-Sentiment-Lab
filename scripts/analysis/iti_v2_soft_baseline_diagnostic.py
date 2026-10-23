#!/usr/bin/env python3
"""Diagnóstico exploratório do baseline Soft (campanha ITI-v2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def run(run_dir: Path) -> dict[str, object]:
    daily_path = run_dir / "iti_daily.csv"
    weekly_path = run_dir / "aligned_panel.csv"
    if not daily_path.is_file():
        raise FileNotFoundError(daily_path)
    daily = pd.read_csv(daily_path)
    eligible = daily.loc[daily["coverage_status"] == "eligible"].copy()
    n_days = len(eligible)
    no_news = int((eligible["n_articles"].fillna(0) == 0).sum())
    soft_zero = int((eligible["soft_input"].fillna(0).abs() < 1e-12).sum())
    report: dict[str, object] = {
        "run_dir": str(run_dir),
        "eligible_days": n_days,
        "days_without_articles": no_news,
        "fraction_days_without_articles": round(no_news / n_days, 4) if n_days else None,
        "days_soft_input_near_zero": soft_zero,
        "fraction_soft_near_zero": round(soft_zero / n_days, 4) if n_days else None,
    }
    if weekly_path.is_file():
        weekly = pd.read_csv(weekly_path)
        if "soft" in weekly.columns:
            wzero = int((weekly["soft"].fillna(0).abs() < 1e-12).sum())
            report["weekly_rows"] = int(len(weekly))
            report["weekly_soft_near_zero"] = wzero
            report["fraction_weekly_soft_near_zero"] = (
                round(wzero / len(weekly), 4) if len(weekly) else None
            )
    articles = eligible["n_articles"].fillna(0)
    report["articles_per_day_mean"] = round(float(articles.mean()), 3)
    report["articles_per_day_median"] = float(articles.median())
    report["articles_per_day_p90"] = float(articles.quantile(0.9))
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
