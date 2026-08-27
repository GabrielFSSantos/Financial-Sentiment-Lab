"""Comparação entre runs."""

from __future__ import annotations

from typing import Any

import pandas as pd

from modules.dashboard.services.campaigns import get_run_from_manifest, load_manifest
from modules.dashboard.services.catalog import get_resolved_config
from modules.dashboard.services.models import load_aggregates, sentiment_by_company
from modules.dashboard.services.research import extract_win_rate, load_research_summary
from modules.dashboard.services.runs import diff_configs, extract_run_params


def compare_runs(run_ids: list[str]) -> dict[str, Any]:
    if len(run_ids) < 2:
        return {"error": "Selecione pelo menos 2 runs."}

    configs = {rid: get_resolved_config(rid) or {} for rid in run_ids}
    summaries = {rid: load_research_summary(rid) for rid in run_ids}
    win_rates = {rid: extract_win_rate(summaries[rid]) for rid in run_ids}

    manifest = load_manifest()
    manifest_entries = {rid: get_run_from_manifest(rid, manifest) for rid in run_ids}

    param_rows: list[dict[str, Any]] = []
    base_id = run_ids[0]
    for rid in run_ids[1:]:
        for row in diff_configs(configs[base_id], configs[rid]):
            param_rows.append({"comparacao": f"{base_id} vs {rid}", **row})

    metrics_rows = [
        {
            "run_id": rid,
            "win_rate": win_rates.get(rid),
            "hipotese": (manifest_entries.get(rid) or {}).get("hypothesis"),
            "alpha": extract_run_params(configs[rid]).get("alpha"),
        }
        for rid in run_ids
    ]

    return {
        "run_ids": run_ids,
        "param_diffs": param_rows,
        "metrics": metrics_rows,
        "win_rates": win_rates,
    }


def compare_sentiment_by_company(
    run_ids: list[str],
    model_key: str,
    dataset_key: str,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for run_id in run_ids:
        agg = load_aggregates(run_id, model_key, dataset_key)
        by_company = sentiment_by_company(agg)
        if by_company.empty:
            continue
        by_company["run_id"] = run_id
        frames.append(by_company)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def delta_win_rate(run_a: str, run_b: str) -> float | None:
    rate_a = extract_win_rate(load_research_summary(run_a))
    rate_b = extract_win_rate(load_research_summary(run_b))
    if rate_a is None or rate_b is None:
        return None
    return rate_b - rate_a
