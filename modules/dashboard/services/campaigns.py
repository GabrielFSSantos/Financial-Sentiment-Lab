"""Campanhas experimentais."""

from __future__ import annotations

import json
from typing import Any

from modules.dashboard.config import CAMPAIGN_MANIFEST, OUTPUTS_DIR


def load_manifest(path=None) -> dict[str, Any] | None:
    target = path or CAMPAIGN_MANIFEST
    if not target.is_file():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def get_campaign_runs(manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = manifest or load_manifest()
    if not payload:
        return []
    return list(payload.get("runs") or [])


def get_run_from_manifest(run_id: str, manifest: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for run in get_campaign_runs(manifest):
        if run.get("run_id") == run_id:
            return run
    return None


def campaign_comparison_table(manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in get_campaign_runs(manifest):
        metrics = run.get("metrics_summary") or {}
        rows.append(
            {
                "run_id": run.get("run_id"),
                "hipotese": run.get("hypothesis"),
                "alpha": run.get("alpha"),
                "equacao": run.get("equation"),
                "modelo": run.get("model"),
                "win_rate": metrics.get("win_rate"),
                "conclusao": metrics.get("conclusion") or run.get("interpretation"),
                "status": run.get("status"),
            }
        )
    return rows


def best_campaign_run(manifest: dict[str, Any] | None = None) -> dict[str, Any] | None:
    runs = get_campaign_runs(manifest)
    scored = [r for r in runs if (r.get("metrics_summary") or {}).get("win_rate") is not None]
    if not scored:
        return None
    return max(scored, key=lambda r: r["metrics_summary"]["win_rate"])
