"""Catálogo de runs, campanhas e datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from modules.dashboard.config import CONFIGS_DIR, OUTPUTS_DIR


@dataclass
class RunSummary:
    run_id: str
    status: str
    started_at: str | None
    finished_at: str | None
    models: list[str]
    datasets: list[str]
    path: Path
    has_research: bool
    raw: dict[str, Any] = field(repr=False)


@dataclass
class DatasetInfo:
    key: str
    display_name: str
    path: Path
    enabled: bool


def list_runs() -> list[RunSummary]:
    if not OUTPUTS_DIR.is_dir():
        return []

    runs: list[RunSummary] = []
    for child in OUTPUTS_DIR.iterdir():
        if not child.is_dir() or child.name == "campaigns":
            continue
        summary_path = child / "summary.json"
        if not summary_path.is_file():
            continue
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
        runs.append(
            RunSummary(
                run_id=raw.get("run_id", child.name),
                status=raw.get("status", "unknown"),
                started_at=raw.get("started_at"),
                finished_at=raw.get("finished_at"),
                models=list(raw.get("selected_models") or []),
                datasets=list(raw.get("selected_datasets") or []),
                path=child,
                has_research=(child / "research" / "research_summary.json").is_file(),
                raw=raw,
            )
        )

    runs.sort(key=lambda item: item.finished_at or item.started_at or "", reverse=True)
    return runs


def get_run(run_id: str) -> RunSummary | None:
    for run in list_runs():
        if run.run_id == run_id:
            return run
    return None


def get_run_summary(run_id: str) -> dict[str, Any] | None:
    run = get_run(run_id)
    return run.raw if run else None


def get_resolved_config(run_id: str) -> dict[str, Any] | None:
    path = OUTPUTS_DIR / run_id / "resolved_config.yaml"
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def list_campaigns() -> list[dict[str, Any]]:
    campaigns_dir = OUTPUTS_DIR / "campaigns"
    if not campaigns_dir.is_dir():
        return []

    campaigns: list[dict[str, Any]] = []
    for child in campaigns_dir.iterdir():
        manifest = child / "manifest.json"
        if manifest.is_file():
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["_path"] = str(child)
            campaigns.append(payload)
    return campaigns


def list_datasets() -> list[DatasetInfo]:
    config_path = CONFIGS_DIR / "datasets.yaml"
    if not config_path.is_file():
        return []

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    datasets: list[DatasetInfo] = []
    for key, value in (raw.get("datasets") or {}).items():
        if not isinstance(value, dict):
            continue
        rel_path = value.get("path", "")
        datasets.append(
            DatasetInfo(
                key=key,
                display_name=value.get("display_name", key),
                path=CONFIGS_DIR.parent / rel_path,
                enabled=bool(value.get("enabled", True)),
            )
        )
    datasets.sort(key=lambda item: item.key)
    return datasets


def resolve_output_path(run_id: str, relative: str) -> Path:
    return OUTPUTS_DIR / run_id / relative


def get_combination_output_files(run_id: str) -> dict[str, str]:
    summary = get_run_summary(run_id)
    if not summary:
        return {}
    files: dict[str, str] = {}
    for combo in summary.get("combinations") or []:
        for name, rel in (combo.get("output_files") or {}).items():
            files[name] = rel
    return files
