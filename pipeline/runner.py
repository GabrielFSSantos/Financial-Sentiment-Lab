"""Orquestração central da pipeline de sentimento financeiro.

Este módulo é o ponto de entrada Python do experimento. Ele coordena:

1. carregamento e resolução das configurações;
2. validações de preflight;
3. execução da matriz modelo × dataset;
4. carregamento dos datasets;
5. criação, carregamento e inferência dos modelos;
6. padronização das previsões;
7. métricas de classificação e desempenho;
8. agregações temporais;
9. gravação dos resultados e do resumo final;
10. liberação de memória entre combinações.

O comando público do projeto continuará sendo ``scripts/run_experiment.sh``.
Esse script chamará internamente:

    python -m pipeline.runner

Quando ``execution.environment`` for ``sdumont``, este módulo representa a
execução que ocorre dentro do job Slurm. Sincronização, SSH e submissão ficam
sob responsabilidade dos scripts da pasta ``scripts/``.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import random
import shutil
import signal
import subprocess
import sys
import traceback as traceback_module
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
import torch

from pipeline.aggregation import (
    AggregationResult,
    SentimentAggregator,
)
from pipeline.configuration import (
    ConfigurationError,
    DatasetConfiguration,
    ExperimentCombination,
    ModelConfiguration,
    ResolvedConfiguration,
    load_configuration,
)
from pipeline.dataset_loader import (
    DatasetLoader,
    LoadedDataset,
)
from pipeline.metrics import (
    ClassificationMetricsCalculator,
    ClassificationMetricsResult,
    CombinationPerformanceMonitor,
    EXECUTION_METRICS_COLUMNS,
    collect_runtime_metadata,
)
from pipeline.output_schema import (
    OutputSchemaBuilder,
    StandardizedPredictions,
)
from pipeline.results import ResultsManager

if TYPE_CHECKING:
    from pipeline.registry import ModelRegistry, RegisteredModel


LOGGER_NAME = "financial_sentiment_lab"
DEFAULT_EXPERIMENT_CONFIG = "configs/experiment.yaml"
EXIT_SUCCESS = 0
EXIT_CONFIGURATION_ERROR = 1
EXIT_EXECUTION_ERROR = 2
EXIT_INTERRUPTED = 130


class RunnerError(RuntimeError):
    """Erro-base da orquestração do experimento."""


class PreflightError(RunnerError):
    """Uma validação anterior à inferência falhou."""


class ExperimentInterruptedError(RunnerError):
    """A execução foi interrompida por sinal ou pelo usuário."""


@dataclass(frozen=True)
class PreflightReport:
    """Resultado das verificações anteriores à inferência."""

    model_reports: tuple[dict[str, Any], ...]
    dataset_reports: tuple[dict[str, Any], ...]
    combination_count: int
    started_at: str
    finished_at: str
    duration_seconds: float
    valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CombinationRunResult:
    """Resumo interno de uma combinação executada."""

    combination_id: str
    model_key: str
    dataset_key: str
    status: str
    duration_seconds: float
    row_count: int | None
    valid_text_count: int | None
    device: str | None
    error_type: str | None = None
    error_message: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunnerOutcome:
    """Resultado final devolvido por ``ExperimentRunner.run``."""

    exit_code: int
    summary: dict[str, Any]
    preflight: PreflightReport
    combinations: tuple[CombinationRunResult, ...]

    @property
    def succeeded(self) -> bool:
        return self.exit_code == EXIT_SUCCESS


class ExperimentRunner:
    """Executa um experimento completamente resolvido."""

    def __init__(
        self,
        configuration: ResolvedConfiguration,
        *,
        logger: logging.Logger | None = None,
        show_tracebacks: bool = False,
    ) -> None:
        self.configuration = configuration
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.show_tracebacks = bool(show_tracebacks)

        self.results = ResultsManager(configuration)
        self.dataset_loader = DatasetLoader()
        self.output_builder = OutputSchemaBuilder()
        self.classification_calculator = (
            ClassificationMetricsCalculator(
                configuration.classification_metrics
            )
        )
        self.aggregator = SentimentAggregator(
            configuration.aggregation
        )

        self._registry: ModelRegistry | None = None
        self._interrupted = False
        self._original_signal_handlers: dict[int, Any] = {}
        self._combination_results: list[CombinationRunResult] = []

    @property
    def registry(self) -> ModelRegistry:
        """Cria o registry de forma tardia.

        O import tardio permite que ``python -m pipeline.runner --help`` e a
        validação sintática do arquivo funcionem mesmo durante a refatoração
        intermediária dos adaptadores em ``models/``.
        """

        if self._registry is None:
            from pipeline.registry import create_model_registry

            self._registry = create_model_registry(
                self.configuration
            )
        return self._registry

    def run(self) -> RunnerOutcome:
        """Executa preflight, dry-run ou todas as combinações."""

        self._install_signal_handlers()
        self.results.prepare()

        runtime_metadata = collect_runtime_metadata()
        repository_metadata = _collect_git_metadata(
            self.configuration.paths.project_root
        )

        try:
            self.logger.info(
                "Iniciando experimento %s em %s.",
                self.configuration.run_id,
                self.configuration.environment,
            )
            self.logger.info(
                "Modelos selecionados: %s",
                ", ".join(self.configuration.model_keys),
            )
            self.logger.info(
                "Datasets selecionados: %s",
                ", ".join(self.configuration.dataset_keys),
            )
            self.logger.info(
                "Combinações: %d",
                len(self.configuration.combinations),
            )

            _configure_reproducibility(
                self.configuration,
                self.logger,
            )

            preflight = self.run_preflight()

            if self.configuration.dry_run:
                self._register_dry_run_combinations(preflight)
                summary = self.results.finalize(
                    extra={
                        "preflight": preflight.to_dict(),
                        "runtime": runtime_metadata,
                        "repository": repository_metadata,
                        "dry_run_validated": True,
                    }
                )
                self.logger.info(
                    "Dry-run concluído com sucesso. Nenhuma inferência "
                    "foi executada."
                )
                return RunnerOutcome(
                    exit_code=EXIT_SUCCESS,
                    summary=summary,
                    preflight=preflight,
                    combinations=tuple(self._combination_results),
                )

            self._execute_combinations()

            failed = sum(
                result.status == "failed"
                for result in self._combination_results
            )
            exit_code = (
                EXIT_EXECUTION_ERROR
                if failed
                else EXIT_SUCCESS
            )

            summary = self.results.finalize(
                extra={
                    "preflight": preflight.to_dict(),
                    "runtime": runtime_metadata,
                    "repository": repository_metadata,
                    "runner": {
                        "exit_code": exit_code,
                        "successful_combinations": sum(
                            item.status == "success"
                            for item in self._combination_results
                        ),
                        "failed_combinations": failed,
                        "skipped_combinations": sum(
                            item.status == "skipped"
                            for item in self._combination_results
                        ),
                    },
                }
            )

            if failed:
                self.logger.error(
                    "Experimento finalizado com %d combinação(ões) "
                    "com falha.",
                    failed,
                )
            else:
                self.logger.info(
                    "Experimento finalizado com sucesso."
                )

            return RunnerOutcome(
                exit_code=exit_code,
                summary=summary,
                preflight=preflight,
                combinations=tuple(self._combination_results),
            )

        except ExperimentInterruptedError:
            self._skip_pending_combinations(
                "execution_interrupted"
            )
            summary = self.results.finalize(
                extra={
                    "runtime": runtime_metadata,
                    "repository": repository_metadata,
                    "interrupted": True,
                }
            )
            self.logger.error("Experimento interrompido.")
            raise
        except Exception as error:
            self._skip_pending_combinations(
                "experiment_aborted_before_execution"
            )
            self.results.finalize(
                extra={
                    "runtime": runtime_metadata,
                    "repository": repository_metadata,
                    "fatal_error": _error_payload(error),
                }
            )
            raise
        finally:
            self._release_all_models()
            self._restore_signal_handlers()

    def run_preflight(self) -> PreflightReport:
        """Valida configurações, adaptadores, arquivos e datasets."""

        started_counter = perf_counter()
        started_at = _now_iso(self.configuration)
        self.logger.info("Executando verificações de preflight.")

        try:
            model_reports = self.registry.validate_all(
                validate_declared_files=bool(
                    self.configuration.preflight_checks.get(
                        "validate_model_files",
                        True,
                    )
                ),
                validate_adapter_files=True,
            )

            dataset_reports: list[dict[str, Any]] = []
            for dataset in self.configuration.datasets:
                columns = self.dataset_loader.inspect_columns(
                    dataset
                )
                dataset_report: dict[str, Any] = {
                    "dataset_key": dataset.key,
                    "dataset_name": dataset.dataset_name,
                    "path": str(dataset.path),
                    "columns": list(columns),
                    "valid": True,
                }

                # Dry-run faz uma validação completa do conteúdo, sem
                # executar inferência nem criar outputs.
                if self.configuration.dry_run:
                    loaded = self.dataset_loader.load(dataset)
                    dataset_report["load"] = loaded.metadata()

                dataset_reports.append(dataset_report)

            # A criação dessas classes já valida níveis, estatísticas,
            # labels e opções das seções correspondentes.
            ClassificationMetricsCalculator(
                self.configuration.classification_metrics
            )
            SentimentAggregator(
                self.configuration.aggregation
            )
            OutputSchemaBuilder()

        except Exception as error:
            raise PreflightError(
                f"Falha nas verificações de preflight: {error}"
            ) from error

        finished_at = _now_iso(self.configuration)
        duration = perf_counter() - started_counter
        preflight_report = PreflightReport(
            model_reports=tuple(model_reports),
            dataset_reports=tuple(dataset_reports),
            combination_count=len(
                self.configuration.combinations
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=round(duration, 6),
            valid=True,
        )

        self.logger.info(
            "Preflight concluído em %.3f s.",
            duration,
        )
        return preflight_report

    def _execute_combinations(self) -> None:
        fail_fast = bool(
            self.configuration.execution.get(
                "fail_fast",
                True,
            )
        )

        for combination in self.configuration.combinations:
            self._raise_if_interrupted()

            result = self._execute_combination(combination)
            self._combination_results.append(result)

            if result.status == "failed" and fail_fast:
                self.logger.error(
                    "fail_fast=true: interrompendo após a falha de %s.",
                    combination.combination_id,
                )
                self._skip_pending_combinations(
                    "not_executed_due_to_fail_fast"
                )
                break

    def _execute_combination(
        self,
        combination: ExperimentCombination,
    ) -> CombinationRunResult:
        model_configuration = self.configuration.get_model(
            combination.model_key
        )
        dataset_configuration = self.configuration.get_dataset(
            combination.dataset_key
        )

        self.results.start_combination(
            combination,
            extra={
                "model_name": model_configuration.model_name,
                "dataset_name": dataset_configuration.dataset_name,
            },
        )

        started_counter = perf_counter()
        loaded_dataset: LoadedDataset | None = None
        registered_model: RegisteredModel | None = None
        monitor: CombinationPerformanceMonitor | None = None
        standardized: StandardizedPredictions | None = None
        classification: ClassificationMetricsResult | None = None
        aggregation: AggregationResult | None = None

        self.logger.info(
            "[%d/%d] Executando %s × %s.",
            combination.index + 1,
            len(self.configuration.combinations),
            combination.model_key,
            combination.dataset_key,
        )

        try:
            monitor = CombinationPerformanceMonitor(
                device=str(
                    model_configuration.parameters.get(
                        "device",
                        "auto",
                    )
                ),
                timezone_name=str(
                    self.configuration.experiment.get(
                        "timezone",
                        "UTC",
                    )
                ),
                settings=self.configuration.performance_metrics,
            )
            monitor.start()

            self._raise_if_interrupted()
            loaded_dataset = self.dataset_loader.load(
                dataset_configuration
            )

            self._raise_if_interrupted()
            registered_model = self.registry.create(
                model_configuration,
                load=False,
                validate_declared_files=False,
                validate_adapter_files=False,
            )

            with monitor.measure_load():
                registered_model.load()

            self._raise_if_interrupted()
            with monitor.measure_inference(
                text_count=len(loaded_dataset.texts)
            ):
                raw_predictions = registered_model.predict(
                    loaded_dataset.texts
                )

            self._raise_if_interrupted()
            standardized = self.output_builder.build(
                run_id=self.configuration.run_id,
                environment=self.configuration.environment,
                combination=combination,
                model_configuration=model_configuration,
                loaded_dataset=loaded_dataset,
                predictions=raw_predictions,
                device_used=registered_model.device_type,
            )

            classification = self.classification_calculator.calculate(
                standardized
            )
            aggregation = self.aggregator.aggregate(
                standardized
            )

            monitor.stop()
            execution_metrics = monitor.build_execution_metrics(
                configuration=self.configuration,
                combination=combination,
                model_configuration=model_configuration,
                loaded_dataset=loaded_dataset,
                status="success",
                device_type=registered_model.device_type,
                device_name=registered_model.device_name,
                num_valid_texts=standardized.row_count,
            )

            metadata = self._success_metadata(
                combination=combination,
                model=registered_model,
                dataset=loaded_dataset,
                standardized=standardized,
                classification=classification,
                aggregation=aggregation,
                monitor=monitor,
            )

            self.results.save_combination_results(
                combination,
                predictions=standardized.dataframe,
                classification_metrics=classification.summary,
                per_class_metrics=classification.per_class,
                confusion_matrix=classification.confusion_matrix,
                class_distribution=(
                    classification.class_distribution
                ),
                execution_metrics=execution_metrics,
                aggregates=aggregation.dataframe,
                metadata=metadata,
                confusion_labels=tuple(
                    self.classification_calculator.labels
                ),
            )

            duration = perf_counter() - started_counter
            warnings = _deduplicate(
                [
                    *loaded_dataset.warnings,
                    *standardized.warnings,
                    *classification.warnings,
                    *aggregation.warnings,
                ]
            )

            self.results.complete_combination(
                combination,
                duration_seconds=duration,
                row_count=standardized.row_count,
                valid_text_count=(
                    loaded_dataset.statistics.valid_row_count
                ),
                device=registered_model.device_type,
                extra={
                    "model_display_name": (
                        model_configuration.display_name
                    ),
                    "dataset_display_name": (
                        dataset_configuration.display_name
                    ),
                    "classification_available": (
                        classification.available
                    ),
                    "aggregate_rows": aggregation.row_count,
                    "texts_per_second": (
                        monitor.snapshot.texts_per_second
                    ),
                    "warnings": list(warnings),
                },
            )

            self.logger.info(
                "Combinação %s concluída: %d linha(s), %.3f s.",
                combination.combination_id,
                standardized.row_count,
                duration,
            )

            return CombinationRunResult(
                combination_id=combination.combination_id,
                model_key=combination.model_key,
                dataset_key=combination.dataset_key,
                status="success",
                duration_seconds=round(duration, 6),
                row_count=standardized.row_count,
                valid_text_count=(
                    loaded_dataset.statistics.valid_row_count
                ),
                device=registered_model.device_type,
                warnings=tuple(warnings),
            )

        except ExperimentInterruptedError:
            raise
        except Exception as error:
            duration = perf_counter() - started_counter
            self._log_combination_error(combination, error)

            if monitor is not None:
                try:
                    monitor.stop()
                except Exception:
                    self.logger.debug(
                        "Não foi possível finalizar o monitor após erro.",
                        exc_info=True,
                    )

            self._save_failure_artifacts(
                combination=combination,
                model_configuration=model_configuration,
                dataset_configuration=dataset_configuration,
                loaded_dataset=loaded_dataset,
                registered_model=registered_model,
                monitor=monitor,
                error=error,
            )

            self.results.fail_combination(
                combination,
                error,
                duration_seconds=duration,
                row_count=(
                    standardized.row_count
                    if standardized is not None
                    else None
                ),
                valid_text_count=(
                    loaded_dataset.statistics.valid_row_count
                    if loaded_dataset is not None
                    else None
                ),
                device=(
                    registered_model.device_type
                    if registered_model is not None
                    else None
                ),
            )

            return CombinationRunResult(
                combination_id=combination.combination_id,
                model_key=combination.model_key,
                dataset_key=combination.dataset_key,
                status="failed",
                duration_seconds=round(duration, 6),
                row_count=(
                    standardized.row_count
                    if standardized is not None
                    else None
                ),
                valid_text_count=(
                    loaded_dataset.statistics.valid_row_count
                    if loaded_dataset is not None
                    else None
                ),
                device=(
                    registered_model.device_type
                    if registered_model is not None
                    else None
                ),
                error_type=type(error).__name__,
                error_message=str(error),
            )

        finally:
            self._release_model_after_combination(
                combination.model_key
            )

    def _success_metadata(
        self,
        *,
        combination: ExperimentCombination,
        model: RegisteredModel,
        dataset: LoadedDataset,
        standardized: StandardizedPredictions,
        classification: ClassificationMetricsResult,
        aggregation: AggregationResult,
        monitor: CombinationPerformanceMonitor,
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "combination": combination.to_dict(),
            "model": model.metadata(),
            "dataset": dataset.metadata(),
            "output_schema": standardized.metadata(),
            "classification_metrics": classification.metadata(),
            "aggregation": aggregation.metadata(),
            "performance": monitor.snapshot.to_dict(),
            "runtime": collect_runtime_metadata(),
        }

    def _save_failure_artifacts(
        self,
        *,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        dataset_configuration: DatasetConfiguration,
        loaded_dataset: LoadedDataset | None,
        registered_model: RegisteredModel | None,
        monitor: CombinationPerformanceMonitor | None,
        error: BaseException,
    ) -> None:
        save_partial = bool(
            self.configuration.execution.get(
                "save_partial_results",
                True,
            )
        )
        if not save_partial:
            return

        metadata = {
            "status": "failed",
            "combination": combination.to_dict(),
            "model": (
                registered_model.metadata()
                if registered_model is not None
                else model_configuration.to_dict()
            ),
            "dataset": (
                loaded_dataset.metadata()
                if loaded_dataset is not None
                else dataset_configuration.to_dict()
            ),
            "error": _error_payload(
                error,
                include_traceback=self.show_tracebacks,
            ),
            "performance": (
                monitor.snapshot.to_dict()
                if monitor is not None
                and _monitor_has_snapshot(monitor)
                else None
            ),
            "runtime": collect_runtime_metadata(),
        }

        execution_metrics = self._failure_execution_metrics(
            combination=combination,
            model_configuration=model_configuration,
            dataset_configuration=dataset_configuration,
            loaded_dataset=loaded_dataset,
            registered_model=registered_model,
            monitor=monitor,
            error=error,
        )

        try:
            self.results.save_combination_results(
                combination,
                execution_metrics=execution_metrics,
                metadata=metadata,
            )
        except Exception:
            self.logger.exception(
                "Falha ao salvar artefatos parciais de %s.",
                combination.combination_id,
            )

    def _failure_execution_metrics(
        self,
        *,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        dataset_configuration: DatasetConfiguration,
        loaded_dataset: LoadedDataset | None,
        registered_model: RegisteredModel | None,
        monitor: CombinationPerformanceMonitor | None,
        error: BaseException,
    ) -> pd.DataFrame:
        if (
            loaded_dataset is not None
            and monitor is not None
            and _monitor_has_snapshot(monitor)
        ):
            return monitor.build_execution_metrics(
                configuration=self.configuration,
                combination=combination,
                model_configuration=model_configuration,
                loaded_dataset=loaded_dataset,
                status="failed",
                error=error,
                device_type=(
                    registered_model.device_type
                    if registered_model is not None
                    else None
                ),
                device_name=(
                    registered_model.device_name
                    if registered_model is not None
                    else None
                ),
                num_valid_texts=(
                    loaded_dataset.statistics.valid_row_count
                ),
            )

        snapshot = (
            monitor.snapshot
            if monitor is not None
            and _monitor_has_snapshot(monitor)
            else None
        )
        now = _now_iso(self.configuration)

        row = {
            "run_id": self.configuration.run_id,
            "environment": self.configuration.environment,
            "combination_id": combination.combination_id,
            "combination_index": combination.index,
            "model_key": model_configuration.key,
            "model_name": model_configuration.model_name,
            "dataset_key": dataset_configuration.key,
            "dataset_name": dataset_configuration.dataset_name,
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "started_at": (
                snapshot.started_at if snapshot else now
            ),
            "finished_at": (
                snapshot.finished_at if snapshot else now
            ),
            "load_time_seconds": (
                snapshot.load_time_seconds if snapshot else pd.NA
            ),
            "inference_time_seconds": (
                snapshot.inference_time_seconds
                if snapshot
                else pd.NA
            ),
            "total_time_seconds": (
                snapshot.total_time_seconds if snapshot else pd.NA
            ),
            "texts_per_second": (
                snapshot.texts_per_second if snapshot else pd.NA
            ),
            "peak_gpu_memory_mb": (
                snapshot.peak_gpu_memory_mb if snapshot else pd.NA
            ),
            "device_type": (
                registered_model.device_type
                if registered_model is not None
                else str(
                    model_configuration.parameters.get(
                        "device",
                        "unknown",
                    )
                )
            ),
            "device_name": (
                registered_model.device_name
                if registered_model is not None
                else pd.NA
            ),
            "batch_size": int(
                model_configuration.parameters["batch_size"]
            ),
            "max_length": int(
                model_configuration.parameters["max_length"]
            ),
            "num_rows": (
                loaded_dataset.statistics.original_row_count
                if loaded_dataset is not None
                else pd.NA
            ),
            "num_valid_texts": (
                loaded_dataset.statistics.valid_row_count
                if loaded_dataset is not None
                else pd.NA
            ),
            "hostname": os.uname().nodename
            if hasattr(os, "uname")
            else os.getenv("COMPUTERNAME", "unknown"),
            "process_id": os.getpid(),
            "python_version": (
                f"{sys.version_info.major}."
                f"{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
            "torch_version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "torch_cuda_version": torch.version.cuda,
            "slurm_job_id": os.getenv("SLURM_JOB_ID", pd.NA),
            "slurm_array_job_id": os.getenv(
                "SLURM_ARRAY_JOB_ID",
                pd.NA,
            ),
            "slurm_array_task_id": os.getenv(
                "SLURM_ARRAY_TASK_ID",
                pd.NA,
            ),
        }

        return pd.DataFrame(
            [row],
            columns=pd.Index(EXECUTION_METRICS_COLUMNS),
        )

    def _register_dry_run_combinations(
        self,
        preflight: PreflightReport,
    ) -> None:
        dataset_reports = {
            report["dataset_key"]: report
            for report in preflight.dataset_reports
        }

        for combination in self.configuration.combinations:
            report = dataset_reports.get(
                combination.dataset_key,
                {},
            )
            load_metadata = report.get("load", {})
            statistics = load_metadata.get("statistics", {})
            valid_rows = statistics.get("valid_row_count")

            self.results.skip_combination(
                combination,
                "dry_run_validation_only",
                row_count=valid_rows,
                valid_text_count=valid_rows,
                extra={
                    "validated": True,
                    "model_key": combination.model_key,
                    "dataset_key": combination.dataset_key,
                },
            )
            self._combination_results.append(
                CombinationRunResult(
                    combination_id=combination.combination_id,
                    model_key=combination.model_key,
                    dataset_key=combination.dataset_key,
                    status="skipped",
                    duration_seconds=0.0,
                    row_count=valid_rows,
                    valid_text_count=valid_rows,
                    device=None,
                    error_message="dry_run_validation_only",
                )
            )

    def _skip_pending_combinations(self, reason: str) -> None:
        completed_ids = {
            result.combination_id
            for result in self._combination_results
        }

        for combination in self.configuration.combinations:
            if combination.combination_id in completed_ids:
                continue

            try:
                self.results.skip_combination(
                    combination,
                    reason,
                )
            except Exception:
                self.logger.debug(
                    "Não foi possível marcar %s como skipped.",
                    combination.combination_id,
                    exc_info=True,
                )
                continue

            self._combination_results.append(
                CombinationRunResult(
                    combination_id=combination.combination_id,
                    model_key=combination.model_key,
                    dataset_key=combination.dataset_key,
                    status="skipped",
                    duration_seconds=0.0,
                    row_count=None,
                    valid_text_count=None,
                    device=None,
                    error_message=reason,
                )
            )

    def _release_model_after_combination(
        self,
        model_key: str,
    ) -> None:
        unload = bool(
            self.configuration.execution.get(
                "unload_model_after_combination",
                True,
            )
        )
        if not unload or self._registry is None:
            return

        try:
            if model_key in self._registry.instantiated_keys:
                self._registry.unload(
                    model_key,
                    remove_instance=True,
                )
        except Exception:
            self.logger.warning(
                "Não foi possível liberar o modelo %s.",
                model_key,
                exc_info=self.show_tracebacks,
            )
        finally:
            _release_python_and_cuda_memory()

    def _release_all_models(self) -> None:
        if self._registry is not None:
            try:
                self._registry.unload_all(
                    remove_instances=True
                )
            except Exception:
                self.logger.warning(
                    "Falha ao liberar todos os modelos.",
                    exc_info=self.show_tracebacks,
                )
        _release_python_and_cuda_memory()

    def _raise_if_interrupted(self) -> None:
        if self._interrupted:
            raise ExperimentInterruptedError(
                "Execução interrompida por sinal."
            )

    def _install_signal_handlers(self) -> None:
        for signal_number in (
            signal.SIGINT,
            signal.SIGTERM,
        ):
            try:
                self._original_signal_handlers[
                    signal_number
                ] = signal.getsignal(signal_number)
                signal.signal(
                    signal_number,
                    self._handle_signal,
                )
            except (ValueError, OSError):
                # Threads secundárias e alguns ambientes não permitem
                # alterar handlers. A execução continua normalmente.
                continue

    def _restore_signal_handlers(self) -> None:
        for signal_number, handler in (
            self._original_signal_handlers.items()
        ):
            try:
                signal.signal(signal_number, handler)
            except (ValueError, OSError):
                continue
        self._original_signal_handlers.clear()

    def _handle_signal(
        self,
        signal_number: int,
        frame: Any,
    ) -> None:
        del frame
        self._interrupted = True
        self.logger.warning(
            "Sinal %s recebido; a execução será encerrada de forma "
            "controlada.",
            signal_number,
        )

    def _log_combination_error(
        self,
        combination: ExperimentCombination,
        error: BaseException,
    ) -> None:
        if self.show_tracebacks:
            self.logger.exception(
                "Falha na combinação %s.",
                combination.combination_id,
            )
        else:
            self.logger.error(
                "Falha na combinação %s: %s: %s",
                combination.combination_id,
                type(error).__name__,
                error,
            )


def run_experiment(
    *,
    project_root: str | Path | None = None,
    experiment_config: str | Path = DEFAULT_EXPERIMENT_CONFIG,
    model_keys: Sequence[str] | None = None,
    dataset_keys: Sequence[str] | None = None,
    environment: str | None = None,
    dry_run: bool | None = None,
    run_id: str | None = None,
    log_level: str | None = None,
    show_tracebacks: bool = False,
) -> RunnerOutcome:
    """Carrega a configuração e executa o experimento."""

    configuration = load_configuration(
        project_root=project_root,
        experiment_config=experiment_config,
        model_keys=model_keys,
        dataset_keys=dataset_keys,
        environment=environment,
        dry_run=dry_run,
        run_id=run_id,
    )

    logger = configure_logging(
        configuration,
        level_override=log_level,
    )
    runner = ExperimentRunner(
        configuration,
        logger=logger,
        show_tracebacks=show_tracebacks,
    )
    return runner.run()


def configure_logging(
    configuration: ResolvedConfiguration,
    *,
    level_override: str | None = None,
) -> logging.Logger:
    """Configura console e arquivo de log da execução."""

    configured_level = (
        level_override
        if level_override is not None
        else configuration.execution.get(
            "log_level",
            "INFO",
        )
    )
    level_name = str(configured_level).strip().upper()
    level = getattr(logging, level_name, None)

    if not isinstance(level, int):
        raise RunnerError(
            f"Nível de log inválido: {configured_level!r}."
        )

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Dry-run não cria outputs nem arquivos auxiliares.
    if not configuration.dry_run:
        configuration.paths.log_root.mkdir(
            parents=True,
            exist_ok=True,
        )
        log_path = (
            configuration.paths.log_root
            / f"{configuration.run_id}.log"
        )
        file_handler = logging.FileHandler(
            log_path,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.runner",
        description=(
            "Executa a matriz de modelos e datasets configurada no "
            "financial-sentiment-lab."
        ),
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=(
            "Raiz do projeto. Por padrão, é inferida a partir do "
            "pacote pipeline."
        ),
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path(DEFAULT_EXPERIMENT_CONFIG),
        help="Caminho de configs/experiment.yaml.",
    )
    parser.add_argument(
        "--model",
        dest="model_keys",
        action="append",
        default=None,
        help=(
            "Seleciona temporariamente um modelo. Pode ser usado "
            "várias vezes."
        ),
    )
    parser.add_argument(
        "--dataset",
        dest="dataset_keys",
        action="append",
        default=None,
        help=(
            "Seleciona temporariamente um dataset. Pode ser usado "
            "várias vezes."
        ),
    )
    parser.add_argument(
        "--environment",
        choices=("local", "sdumont"),
        default=None,
        help=(
            "Sobrescreve temporariamente execution.environment. "
            "Normalmente o ambiente vem do YAML."
        ),
    )

    dry_run_group = parser.add_mutually_exclusive_group()
    dry_run_group.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Valida tudo sem executar inferência.",
    )
    dry_run_group.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Força a execução real, sobrescrevendo o YAML.",
    )
    parser.set_defaults(dry_run=None)

    parser.add_argument(
        "--run-id",
        default=None,
        help="Sobrescreve temporariamente experiment.run_id.",
    )
    parser.add_argument(
        "--log-level",
        choices=(
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ),
        default=None,
        help="Sobrescreve temporariamente execution.log_level.",
    )
    parser.add_argument(
        "--traceback",
        action="store_true",
        help="Exibe tracebacks completos nos erros.",
    )
    parser.add_argument(
        "--print-summary-json",
        action="store_true",
        help="Imprime o resumo final em JSON no stdout.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)

    try:
        outcome = run_experiment(
            project_root=arguments.project_root,
            experiment_config=arguments.experiment_config,
            model_keys=arguments.model_keys,
            dataset_keys=arguments.dataset_keys,
            environment=arguments.environment,
            dry_run=arguments.dry_run,
            run_id=arguments.run_id,
            log_level=arguments.log_level,
            show_tracebacks=arguments.traceback,
        )

        if arguments.print_summary_json:
            print(
                json.dumps(
                    outcome.summary,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )

        return outcome.exit_code

    except KeyboardInterrupt:
        print(
            "Execução interrompida pelo usuário.",
            file=sys.stderr,
        )
        return EXIT_INTERRUPTED
    except ExperimentInterruptedError as error:
        print(str(error), file=sys.stderr)
        return EXIT_INTERRUPTED
    except (ConfigurationError, PreflightError) as error:
        print(
            f"Erro de configuração/preflight: {error}",
            file=sys.stderr,
        )
        if arguments.traceback:
            traceback_module.print_exc()
        return EXIT_CONFIGURATION_ERROR
    except Exception as error:
        print(
            f"Erro durante a execução: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        if arguments.traceback:
            traceback_module.print_exc()
        return EXIT_EXECUTION_ERROR


def _configure_reproducibility(
    configuration: ResolvedConfiguration,
    logger: logging.Logger,
) -> None:
    settings = configuration.reproducibility
    seed = int(
        configuration.experiment.get(
            "random_seed",
            42,
        )
    )

    if bool(settings.get("set_python_hash_seed", True)):
        configured_hash_seed = os.environ.get(
            "PYTHONHASHSEED"
        )
        if configured_hash_seed is None:
            os.environ["PYTHONHASHSEED"] = str(seed)
            logger.debug(
                "PYTHONHASHSEED definido para %d. O efeito completo "
                "ocorre em processos Python iniciados posteriormente.",
                seed,
            )
        elif configured_hash_seed != str(seed):
            logger.warning(
                "PYTHONHASHSEED já estava definido como %s; a semente "
                "do experimento é %d.",
                configured_hash_seed,
                seed,
            )

    random.seed(seed)

    if bool(settings.get("seed_numpy", True)):
        np.random.seed(seed)

    if bool(settings.get("seed_torch", True)):
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    deterministic = bool(
        settings.get("deterministic_torch", False)
    )
    benchmark = bool(
        settings.get("cudnn_benchmark", True)
    )

    if deterministic and benchmark:
        logger.warning(
            "deterministic_torch=true e cudnn_benchmark=true são "
            "objetivos conflitantes. cudnn_benchmark será desativado."
        )
        benchmark = False

    try:
        torch.use_deterministic_algorithms(
            deterministic,
            warn_only=True,
        )
    except TypeError:
        torch.use_deterministic_algorithms(
            deterministic
        )

    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = benchmark

    logger.info(
        "Reprodutibilidade configurada com seed=%d.",
        seed,
    )


def _collect_git_metadata(
    project_root: Path,
) -> dict[str, Any]:
    git_directory = project_root / ".git"
    if not git_directory.exists():
        return {
            "available": False,
            "reason": "git_repository_not_found",
        }

    if shutil.which("git") is None:
        return {
            "available": False,
            "reason": "git_command_not_found",
        }

    def run_git(*arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return None
        return completed.stdout.strip() or None

    commit = run_git("rev-parse", "HEAD")
    branch = run_git(
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    )
    status = run_git("status", "--porcelain")

    return {
        "available": commit is not None,
        "commit": commit,
        "branch": branch,
        "dirty": bool(status),
    }


def _error_payload(
    error: BaseException,
    *,
    include_traceback: bool = False,
) -> dict[str, Any]:
    payload = {
        "type": type(error).__name__,
        "message": str(error),
    }
    if include_traceback:
        payload["traceback"] = "".join(
            traceback_module.format_exception(
                type(error),
                error,
                error.__traceback__,
            )
        )
    return payload


def _monitor_has_snapshot(
    monitor: CombinationPerformanceMonitor,
) -> bool:
    try:
        monitor.snapshot
    except Exception:
        return False
    return True


def _release_python_and_cuda_memory() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except RuntimeError:
            pass


def _now_iso(
    configuration: ResolvedConfiguration,
) -> str:
    timezone_name = str(
        configuration.experiment.get(
            "timezone",
            "UTC",
        )
    )
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("UTC")
    return datetime.now(timezone).isoformat()


def _deduplicate(
    values: Sequence[str],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


__all__ = [
    "DEFAULT_EXPERIMENT_CONFIG",
    "EXIT_CONFIGURATION_ERROR",
    "EXIT_EXECUTION_ERROR",
    "EXIT_INTERRUPTED",
    "EXIT_SUCCESS",
    "CombinationRunResult",
    "ExperimentInterruptedError",
    "ExperimentRunner",
    "PreflightError",
    "PreflightReport",
    "RunnerError",
    "RunnerOutcome",
    "build_argument_parser",
    "configure_logging",
    "main",
    "run_experiment",
]


if __name__ == "__main__":
    raise SystemExit(main())
