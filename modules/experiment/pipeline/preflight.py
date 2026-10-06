"""Preflight checks before model inference."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Any

from modules.datasets.loader import DatasetLoader
from modules.experiment.common import now_iso
from modules.experiment.pipeline.errors import PreflightError

if TYPE_CHECKING:
    from modules.experiment.config.loader import ResolvedConfiguration
    from modules.models.registry import ModelRegistry


@dataclass(frozen=True)
class PreflightReport:
    """Result of pre-inference validation."""

    model_reports: tuple[dict[str, Any], ...]
    dataset_reports: tuple[dict[str, Any], ...]
    combination_count: int
    started_at: str
    finished_at: str
    duration_seconds: float
    valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_iso(configuration: ResolvedConfiguration) -> str:
    return now_iso(
        timezone_name=str(configuration.experiment.get("timezone", "UTC"))
    )


def run_preflight(
    configuration: ResolvedConfiguration,
    registry: ModelRegistry,
    dataset_loader: DatasetLoader,
    logger: logging.Logger,
) -> PreflightReport:
    """Validate adapters, dataset files, and columns."""

    started_counter = perf_counter()
    started_at = _now_iso(configuration)
    checks = configuration.preflight_checks
    if not bool(checks.get("enabled", True)):
        finished_at = _now_iso(configuration)
        duration = perf_counter() - started_counter
        logger.info(
            "Preflight de I/O desativado (preflight_checks.enabled=false)."
        )
        return PreflightReport(
            model_reports=(),
            dataset_reports=(),
            combination_count=len(configuration.combinations),
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=round(duration, 6),
            valid=True,
        )

    logger.info("Executando verificações de preflight.")

    try:
        model_reports = registry.validate_all(
            validate_declared_files=bool(
                configuration.preflight_checks.get(
                    "validate_model_files",
                    True,
                )
            ),
            validate_adapter_files=True,
        )

        dataset_reports: list[dict[str, Any]] = []
        for dataset in configuration.datasets:
            columns = dataset_loader.inspect_columns(dataset)
            dataset_report: dict[str, Any] = {
                "dataset_key": dataset.key,
                "dataset_name": dataset.dataset_name,
                "path": str(dataset.path),
                "columns": list(columns),
                "valid": True,
            }

            if configuration.dry_run:
                loaded = dataset_loader.load(dataset)
                dataset_report["load"] = loaded.metadata()

            dataset_reports.append(dataset_report)

    except Exception as error:
        raise PreflightError(
            f"Falha nas verificações de preflight: {error}"
        ) from error

    finished_at = _now_iso(configuration)
    duration = perf_counter() - started_counter
    logger.info("Preflight concluído em %.3f s.", duration)
    return PreflightReport(
        model_reports=tuple(model_reports),
        dataset_reports=tuple(dataset_reports),
        combination_count=len(configuration.combinations),
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=round(duration, 6),
        valid=True,
    )
