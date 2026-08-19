"""Resolução de paths e leitura dos índices produzidos pelo experimento."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from modules.research.config.loader import ResearchConfiguration


class ExperimentIOError(RuntimeError):
    """Erro ao localizar ou ler saídas do experimento."""


@dataclass(frozen=True)
class IndexCombination:
    """Combinação modelo × dataset disponível em um run."""

    model_key: str
    dataset_key: str
    root: Path
    iti_daily: Path
    baselines_daily: Path
    uncertainty_daily: Path | None


def resolve_run_directory(configuration: ResearchConfiguration) -> Path:
    """Resolve ``outputs/{run_id}``; se run_id for null, usa o run mais recente."""

    if configuration.run_id is not None:
        run_dir = configuration.experiment_output_root / configuration.run_id
        if not run_dir.is_dir():
            raise ExperimentIOError(
                f"Run não encontrado: {run_dir}"
            )
        return run_dir

    candidates: list[tuple[float, Path]] = []
    root = configuration.experiment_output_root
    if not root.is_dir():
        raise ExperimentIOError(
            f"Diretório de outputs ausente: {root}"
        )

    for child in root.iterdir():
        if not child.is_dir():
            continue
        summary = child / "summary.json"
        if summary.is_file():
            candidates.append((summary.stat().st_mtime, child))

    if not candidates:
        raise ExperimentIOError(
            f"Nenhum run com summary.json em {root}"
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def list_index_combinations(
    configuration: ResearchConfiguration,
    *,
    run_dir: Path | None = None,
) -> list[IndexCombination]:
    """Lista combinações com ``iti_daily.csv`` e ``baselines_daily.csv``."""

    resolved_run = run_dir or resolve_run_directory(configuration)
    indices_root = resolved_run / "indices"
    if not indices_root.is_dir():
        raise ExperimentIOError(
            f"Diretório indices ausente: {indices_root}"
        )

    combinations: list[IndexCombination] = []

    for model_dir in sorted(indices_root.iterdir()):
        if not model_dir.is_dir() or model_dir.name == "merged":
            continue
        if (
            configuration.model_key is not None
            and model_dir.name != configuration.model_key
        ):
            continue

        for dataset_dir in sorted(model_dir.iterdir()):
            if not dataset_dir.is_dir():
                continue
            if (
                configuration.dataset_key is not None
                and dataset_dir.name != configuration.dataset_key
            ):
                continue

            iti_path = dataset_dir / "iti_daily.csv"
            baselines_path = dataset_dir / "baselines_daily.csv"
            if not iti_path.is_file() or not baselines_path.is_file():
                continue

            uncertainty_path = (
                indices_root
                / "merged"
                / dataset_dir.name
                / "iti_uncertainty_daily.csv"
            )
            combinations.append(
                IndexCombination(
                    model_key=model_dir.name,
                    dataset_key=dataset_dir.name,
                    root=dataset_dir,
                    iti_daily=iti_path,
                    baselines_daily=baselines_path,
                    uncertainty_daily=(
                        uncertainty_path if uncertainty_path.is_file() else None
                    ),
                )
            )

    if not combinations:
        raise ExperimentIOError(
            f"Nenhuma combinação com índices em {indices_root}"
        )

    return combinations


def load_iti_daily(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype(str)
    return frame


def load_baselines_daily(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype(str)
    return frame


def load_uncertainty_daily(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype(str)
    return frame


def read_run_summary(run_dir: Path) -> dict[str, object]:
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        return {}
    with summary_path.open("r", encoding="utf-8") as file:
        return json.load(file)


__all__ = [
    "ExperimentIOError",
    "IndexCombination",
    "list_index_combinations",
    "load_baselines_daily",
    "load_iti_daily",
    "load_uncertainty_daily",
    "read_run_summary",
    "resolve_run_directory",
]
