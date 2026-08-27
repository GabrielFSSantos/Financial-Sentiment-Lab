"""Registro estruturado de runs da campanha experimental."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CampaignRunRecord:
    run_id: str
    hypothesis: str
    config_path: str
    model: str
    dataset: str
    alpha: float
    equation: str
    variables_included: list[str] = field(default_factory=list)
    variables_removed: list[str] = field(default_factory=list)
    frequency: str = "weekly"
    metrics_summary: dict[str, Any] = field(default_factory=dict)
    delta_vs_baseline: dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""
    next_hypothesis: str = ""
    status: str = "pending"


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"campaign": "sabesp_2026", "runs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_run(path: Path, record: CampaignRunRecord) -> None:
    payload = load_manifest(path)
    runs = [item for item in payload.get("runs", []) if item.get("run_id") != record.run_id]
    runs.append(asdict(record))
    payload["runs"] = runs
    save_manifest(path, payload)


def update_run_results(
    path: Path,
    *,
    run_id: str,
    metrics_summary: dict[str, Any],
    delta_vs_baseline: dict[str, Any],
    interpretation: str,
    status: str = "completed",
) -> None:
    payload = load_manifest(path)
    for item in payload.get("runs", []):
        if item.get("run_id") == run_id:
            item["metrics_summary"] = metrics_summary
            item["delta_vs_baseline"] = delta_vs_baseline
            item["interpretation"] = interpretation
            item["status"] = status
            break
    save_manifest(path, payload)
