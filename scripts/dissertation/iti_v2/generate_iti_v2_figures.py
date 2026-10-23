#!/usr/bin/env python3
"""Figuras ITI-v2 a partir do painel alinhado (Parte IV §13)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: E402
except ImportError:  # pragma: no cover - ambiente mínimo sem figuras
    plt = None  # type: ignore[assignment]
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]


def _run_dir(run_id: str) -> Path:
    return ROOT / "outputs/campaigns/iti_v2" / run_id


def figure_daily_signal(run_dir: Path, out_dir: Path) -> Path | None:
    daily_path = run_dir / "iti_daily.csv"
    if not daily_path.is_file():
        return None
    daily = pd.read_csv(daily_path)
    if daily.empty or "iti_v2_h7" not in daily.columns:
        return None
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(daily["date"], daily["soft_input"], label="Soft (diário)", alpha=0.8)
    axes[0].plot(daily["date"], daily["iti_v2_h7"], label="ITI-H7 (diário)", alpha=0.8)
    axes[0].set_ylabel("Sinal")
    axes[0].legend(loc="upper right")
    axes[0].set_title(f"Sinal diário — {run_dir.name}")
    if "n_articles" in daily.columns:
        axes[1].bar(daily["date"], daily["n_articles"], width=1.0, color="#4c72b0", alpha=0.6)
        axes[1].set_ylabel("Nº notícias")
    fig.autofmt_xdate()
    fig.tight_layout()
    path = out_dir / "figure_daily_signal.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def figure_h_sensitivity(run_dir: Path, out_dir: Path) -> Path | None:
    weekly_path = run_dir / "iti_weekly_signals.csv"
    if not weekly_path.is_file():
        return None
    weekly = pd.read_csv(weekly_path)
    cols = [c for c in ("iti_v2_h2", "iti_v2_h7", "iti_v2_h14") if c in weekly.columns]
    if not cols:
        return None
    weekly["week_end"] = pd.to_datetime(weekly.get("week_end", weekly.get("date")), errors="coerce")
    fig, ax = plt.subplots(figsize=(10, 4))
    for col in cols:
        ax.plot(weekly["week_end"], weekly[col], label=col, alpha=0.85)
    ax.set_ylabel("ITI semanal")
    ax.legend()
    ax.set_title("Sensibilidade H (mesmas predições)")
    fig.autofmt_xdate()
    fig.tight_layout()
    path = out_dir / "figure_h_sensitivity.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def figure_delta_intervals(run_dir: Path, out_dir: Path) -> Path | None:
    sec_path = run_dir / "table_secondary.json"
    if not sec_path.is_file():
        return None
    rows = json.loads(sec_path.read_text(encoding="utf-8"))
    usable = [
        r
        for r in rows
        if r.get("delta") is not None and r.get("ci_low") is not None and r.get("ci_high") is not None
    ]
    if not usable:
        return None
    labels = [r["contrast_id"] for r in usable]
    deltas = [float(r["delta"]) for r in usable]
    lows = [float(r["ci_low"]) for r in usable]
    highs = [float(r["ci_high"]) for r in usable]
    yerr = [
        [d - lo for d, lo in zip(deltas, lows, strict=True)],
        [hi - d for d, hi in zip(deltas, highs, strict=True)],
    ]
    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.35)))
    y_pos = range(len(labels))
    ax.errorbar(deltas, list(y_pos), xerr=yerr, fmt="o", capsize=4)
    ax.axvline(0.0, color="gray", linestyle="--", linewidth=1)
    ax.set_yticks(list(y_pos), labels)
    ax.set_xlabel("Δ (bootstrap IC 95%)")
    ax.set_title("Família secundária pré-registrada")
    fig.tight_layout()
    path = out_dir / "figure_delta_intervals.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> int:
    if plt is None:
        print("matplotlib ausente; figuras ITI-v2 ignoradas", file=sys.stderr)
        return 0
    run_id = sys.argv[1] if len(sys.argv) > 1 else "iti_v2_prod_20261022"
    run_dir = _run_dir(run_id)
    if not run_dir.is_dir():
        print(f"Run ausente: {run_dir}", file=sys.stderr)
        return 1
    out_dir = run_dir / "generated_figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    thesis_fig = ROOT / "docs/Dissertacao_PPGCC/generated/figures/iti_v2"
    thesis_fig.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for fn in (figure_daily_signal, figure_h_sensitivity, figure_delta_intervals):
        path = fn(run_dir, out_dir)
        if path is not None:
            created.append(path)
            (thesis_fig / path.name).write_bytes(path.read_bytes())
    print("\n".join(str(p) for p in created))
    return 0 if created else 1


if __name__ == "__main__":
    raise SystemExit(main())
