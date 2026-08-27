"""Detalhes e diff de runs."""

from __future__ import annotations

from typing import Any

import yaml

from modules.dashboard.config import OUTPUTS_DIR
from modules.dashboard.services.catalog import get_resolved_config, get_run, get_run_summary


def get_run_detail(run_id: str) -> dict[str, Any] | None:
    summary = get_run_summary(run_id)
    if not summary:
        return None

    config = get_resolved_config(run_id) or {}
    temporal = config.get("temporal_index") or {}
    combinations = summary.get("combinations") or []

    return {
        "run_id": run_id,
        "status": summary.get("status"),
        "started_at": summary.get("started_at"),
        "finished_at": summary.get("finished_at"),
        "models": summary.get("selected_models") or [],
        "datasets": summary.get("selected_datasets") or [],
        "combinations": combinations,
        "alpha": temporal.get("alpha"),
        "equation_mode": temporal.get("equation_mode", "full"),
        "disabled_dimensions": temporal.get("disabled_dimensions") or [],
        "iti_enabled": temporal.get("enabled", True),
        "config": config,
        "has_research": (OUTPUTS_DIR / run_id / "research" / "research_summary.json").exists(),
    }


def extract_run_params(config: dict[str, Any]) -> dict[str, Any]:
    temporal = config.get("temporal_index") or {}
    return {
        "alpha": temporal.get("alpha"),
        "equation_mode": temporal.get("equation_mode", "full"),
        "disabled_dimensions": temporal.get("disabled_dimensions") or [],
        "horizon_mode": (temporal.get("horizon") or {}).get("mode", "adaptive"),
        "models": [
            key
            for key, value in (config.get("models") or {}).items()
            if isinstance(value, dict) and value.get("enabled", True)
        ]
        if "models" in config
        else [],
    }


def diff_configs(config_a: dict[str, Any], config_b: dict[str, Any]) -> list[dict[str, Any]]:
    params_a = extract_run_params(config_a)
    params_b = extract_run_params(config_b)
    rows: list[dict[str, Any]] = []
    keys = sorted(set(params_a) | set(params_b))
    for key in keys:
        val_a = params_a.get(key)
        val_b = params_b.get(key)
        if val_a != val_b:
            rows.append({"parametro": key, "run_a": val_a, "run_b": val_b})
    return rows


def get_campaign_hypothesis(run_id: str) -> str | None:
    from modules.dashboard.services.campaigns import get_run_from_manifest

    entry = get_run_from_manifest(run_id)
    return entry.get("hypothesis") if entry else None
