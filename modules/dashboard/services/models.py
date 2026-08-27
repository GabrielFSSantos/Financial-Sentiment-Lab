"""Dados de modelos e previsões."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from modules.dashboard.config import OUTPUTS_DIR
from modules.dashboard.services.catalog import get_run_summary, resolve_output_path


def _combo_paths(run_id: str, model_key: str | None = None, dataset_key: str | None = None) -> dict[str, Path]:
    summary = get_run_summary(run_id)
    if not summary:
        return {}
    paths: dict[str, Path] = {}
    for combo in summary.get("combinations") or []:
        mk = combo.get("model_key")
        dk = combo.get("dataset_key")
        if model_key and mk != model_key:
            continue
        if dataset_key and dk != dataset_key:
            continue
        for name, rel in (combo.get("output_files") or {}).items():
            paths[name] = resolve_output_path(run_id, rel)
    return paths


def list_combinations(run_id: str) -> list[dict[str, str]]:
    summary = get_run_summary(run_id)
    if not summary:
        return []
    return [
        {
            "model_key": c.get("model_key", ""),
            "dataset_key": c.get("dataset_key", ""),
            "combination_id": c.get("combination_id", ""),
        }
        for c in summary.get("combinations") or []
    ]


def load_predictions(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    paths = _combo_paths(run_id, model_key, dataset_key)
    path = paths.get("predictions")
    if not path or not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_aggregates(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    paths = _combo_paths(run_id, model_key, dataset_key)
    path = paths.get("aggregates")
    if not path or not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_class_distribution(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    paths = _combo_paths(run_id, model_key, dataset_key)
    path = paths.get("class_distribution")
    if not path or not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_execution_metrics(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    paths = _combo_paths(run_id, model_key, dataset_key)
    path = paths.get("execution_metrics")
    if not path or not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_per_class_metrics(run_id: str, model_key: str, dataset_key: str) -> pd.DataFrame:
    paths = _combo_paths(run_id, model_key, dataset_key)
    path = paths.get("per_class_metrics")
    if not path or not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def has_supervised_labels(run_id: str, model_key: str, dataset_key: str) -> bool:
    preds = load_predictions(run_id, model_key, dataset_key)
    if preds.empty or "true_label" not in preds.columns:
        return False
    return preds["true_label"].notna().any() and (preds["true_label"].astype(str).str.strip() != "").any()


def class_distribution_columns(frame: pd.DataFrame) -> tuple[str, str]:
    if "label" in frame.columns:
        label_col = "label"
    elif "predicted_label" in frame.columns:
        label_col = "predicted_label"
    else:
        label_col = str(frame.columns[0])
    count_col = "count" if "count" in frame.columns else str(frame.columns[-1])
    return label_col, count_col


def sentiment_by_company(aggregates: pd.DataFrame) -> pd.DataFrame:
    if aggregates.empty:
        return pd.DataFrame()
    company = aggregates[aggregates["aggregation_level"] == "company_day"].copy()
    if company.empty:
        return pd.DataFrame()
    return (
        company.groupby("company", dropna=False)
        .agg(
            sentiment_mean=("sentiment_mean", "mean"),
            news_count=("news_count", "sum"),
        )
        .reset_index()
        .sort_values("news_count", ascending=False)
    )
