"""Dados de research."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from modules.dashboard.config import OUTPUTS_DIR


def _research_dir(run_id: str, model_key: str, dataset_key: str) -> Path:
    return OUTPUTS_DIR / run_id / "research" / model_key / dataset_key


def load_research_summary(run_id: str) -> dict | None:
    path = OUTPUTS_DIR / run_id / "research" / "research_summary.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_incremental_deltas(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    path = _research_dir(run_id, model_key, dataset_key) / "incremental_deltas.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_market_metrics(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    path = _research_dir(run_id, model_key, dataset_key) / "market_metrics.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_aligned_panel(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    path = _research_dir(run_id, model_key, dataset_key) / "aligned_panel.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_incremental(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    path = _research_dir(run_id, model_key, dataset_key) / "incremental.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def extract_win_rate(summary: dict | None) -> float | None:
    if not summary:
        return None
    totals = {"wins": 0, "comparisons": 0}
    for combo in summary.get("combinations") or []:
        for stats in (combo.get("predictor_stats") or {}).values():
            totals["wins"] += int(stats.get("wins", 0))
            totals["comparisons"] += int(stats.get("comparisons", 0))
    if totals["comparisons"] == 0:
        return None
    return totals["wins"] / totals["comparisons"]


def load_iti_daily(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    path = OUTPUTS_DIR / run_id / "indices" / model_key / dataset_key / "iti_daily.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_baselines_daily(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    path = OUTPUTS_DIR / run_id / "indices" / model_key / dataset_key / "baselines_daily.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)
