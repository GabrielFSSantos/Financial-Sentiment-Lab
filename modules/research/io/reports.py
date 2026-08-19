"""Gravação de relatórios de research."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from modules.research.common import to_serializable


@dataclass(frozen=True)
class CombinationReports:
    """Arquivos gerados para uma combinação modelo × dataset."""

    output_dir: Path
    aligned_panel: Path
    incremental: Path
    market_metrics: Path


def combination_output_dir(
    *,
    research_output_root: Path,
    run_id: str,
    model_key: str,
    dataset_key: str,
) -> Path:
    return (
        research_output_root
        / run_id
        / "research"
        / model_key
        / dataset_key
    )


def write_combination_reports(
    *,
    output_dir: Path,
    aligned_panel: pd.DataFrame,
    incremental: pd.DataFrame,
    market_metrics: pd.DataFrame,
) -> CombinationReports:
    output_dir.mkdir(parents=True, exist_ok=True)

    aligned_path = output_dir / "aligned_panel.csv"
    incremental_path = output_dir / "incremental.csv"
    market_path = output_dir / "market_metrics.csv"

    aligned_panel.to_csv(aligned_path, index=False)
    incremental.to_csv(incremental_path, index=False)
    market_metrics.to_csv(market_path, index=False)

    return CombinationReports(
        output_dir=output_dir,
        aligned_panel=aligned_path,
        incremental=incremental_path,
        market_metrics=market_path,
    )


def write_research_summary(
    *,
    summary_path: Path,
    payload: dict[str, Any],
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(to_serializable(payload), file, indent=2, ensure_ascii=False)
        file.write("\n")


__all__ = [
    "CombinationReports",
    "combination_output_dir",
    "write_combination_reports",
    "write_research_summary",
]
