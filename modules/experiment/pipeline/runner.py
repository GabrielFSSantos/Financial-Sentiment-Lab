"""Orquestração da pipeline de sentimento financeiro."""

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

import numpy as np
import pandas as pd
import torch

from modules.experiment.stages.aggregation import (
    AggregationResult,
    SentimentAggregator,
)
from modules.experiment.common import deduplicate, now_iso
from modules.experiment.config.loader import (
    ConfigurationError,
    DatasetConfiguration,
    ExperimentCombination,
    ModelConfiguration,
    ResolvedConfiguration,
    load_configuration,
)
from modules.datasets.loader import (
    DatasetLoader,
    LoadedDataset,
)
from modules.experiment.stages.metrics import (
    ClassificationMetricsCalculator,
    ClassificationMetricsResult,
    CombinationPerformanceMonitor,
    EXECUTION_METRICS_COLUMNS,
    build_error_execution_metrics,
    collect_runtime_metadata,
)
from modules.experiment.io.output_schema import (
    OutputSchemaBuilder,
    StandardizedPredictions,
)
from modules.experiment.io.results import ResultsManager
from modules.experiment.indexing.temporal_index import (
    TemporalIndexBuilder,
    TemporalIndexError,
    merge_uncertainty_across_models,
)
from modules.experiment.pipeline.errors import (
    ExperimentInterruptedError,
    PreflightError,
    RunnerError,
)
from modules.experiment.pipeline.combination_executor import (
    CombinationRunResult,
    execute_combination,
)
from modules.experiment.pipeline.preflight import PreflightReport, run_preflight
from modules.experiment.pipeline.runner_support import (
    format_combination_progress,
    release_python_and_cuda_memory,
)

if TYPE_CHECKING:
    from modules.models.registry import ModelRegistry, RegisteredModel


LOGGER_NAME = "financial_sentiment_lab"
DEFAULT_EXPERIMENT_CONFIG = "configs/experiment.yaml"
EXIT_SUCCESS = 0
EXIT_CONFIGURATION_ERROR = 1
EXIT_EXECUTION_ERROR = 2
EXIT_INTERRUPTED = 130


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
        self.temporal_index_builder = TemporalIndexBuilder(
            configuration
        )

        self._registry: ModelRegistry | None = None
        self._interrupted = False
        self._original_signal_handlers: dict[int, Any] = {}
        self._combination_results: list[CombinationRunResult] = []

    @property
    def registry(self) -> ModelRegistry:
        """Cria o registry de forma tardia.

        O import tardio permite que ``python -m modules.experiment --help``
        funcione sem carregar adaptadores de modelo.
        """

        if self._registry is None:
            from modules.models.registry import create_model_registry

            self._registry = create_model_registry(
                self.configuration
            )
        return self._registry

    def run(self) -> RunnerOutcome:
        """Executa preflight, dry-run ou todas as combinações."""

        self._install_signal_handlers()
        runtime_metadata: dict[str, Any] = {}
        repository_metadata: dict[str, Any] = {}

        try:
            self.results.prepare()
            runtime_metadata = collect_runtime_metadata()
            repository_metadata = _collect_git_metadata(
                self.configuration.paths.project_root
            )
            if repository_metadata.get("dirty"):
                self.logger.warning(
                    "O repositório Git possui alterações não commitadas. "
                    "Para reprodutibilidade, execute com working tree limpa "
                    "antes de rodadas de produção ou publicação."
                )

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
            if self.configuration.skipped_combinations:
                self.logger.info(
                    "Combinações ignoradas por idioma: %d",
                    len(self.configuration.skipped_combinations),
                )
                for skipped in self.configuration.skipped_combinations:
                    self.logger.info(
                        "  %s × %s (%s ≠ %s)",
                        skipped.model_key,
                        skipped.dataset_key,
                        skipped.model_language,
                        skipped.dataset_language,
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
            uncertainty_outputs = self._merge_uncertainty_indices()

            failed = sum(
                result.status == "failed"
                for result in self._combination_results
            )
            successful = sum(
                result.status == "success"
                for result in self._combination_results
            )
            skipped = sum(
                result.status == "skipped"
                for result in self._combination_results
            )
            total_combinations = len(self.configuration.combinations)
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
                    "uncertainty_indices": uncertainty_outputs,
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
                    "Experimento concluído: %s, %d sucesso, %d falha(s), "
                    "%d ignorada(s).",
                    format_combination_progress(
                        total_combinations,
                        total_combinations,
                    ),
                    successful,
                    failed,
                    skipped,
                )
            else:
                self.logger.info(
                    "Experimento concluído: %s, %d sucesso, %d falha(s), "
                    "%d ignorada(s).",
                    format_combination_progress(
                        total_combinations,
                        total_combinations,
                    ),
                    successful,
                    failed,
                    skipped,
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
            try:
                self.results.finalize(
                    extra={
                        "runtime": runtime_metadata,
                        "repository": repository_metadata,
                        "interrupted": True,
                    }
                )
            except Exception:
                self.logger.debug(
                    "Não foi possível finalizar o summary após interrupção.",
                    exc_info=True,
                )
            self.logger.error("Experimento interrompido.")
            raise
        except Exception as error:
            self._skip_pending_combinations(
                "experiment_aborted_before_execution"
            )
            try:
                self.results.finalize(
                    extra={
                        "runtime": runtime_metadata,
                        "repository": repository_metadata,
                        "fatal_error": _error_payload(error),
                    }
                )
            except Exception:
                self.logger.debug(
                    "Não foi possível finalizar o summary após erro fatal.",
                    exc_info=True,
                )
            raise
        finally:
            self._release_all_models()
            self._restore_signal_handlers()

    def run_preflight(self) -> PreflightReport:
        """Valida adaptadores, arquivos e colunas dos datasets."""

        return run_preflight(
            self.configuration,
            self.registry,
            self.dataset_loader,
            self.logger,
        )

    def _execute_combinations(self) -> None:
        fail_fast = bool(
            self.configuration.execution.get(
                "fail_fast",
                True,
            )
        )

        combinations = self.configuration.combinations
        for position, combination in enumerate(combinations):
            self._raise_if_interrupted()
            next_model_key = (
                combinations[position + 1].model_key
                if position + 1 < len(combinations)
                else None
            )

            result = self._execute_combination(
                combination,
                next_model_key=next_model_key,
            )
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

    def _merge_uncertainty_indices(self) -> dict[str, dict[str, str]]:
        if not self.temporal_index_builder.enabled:
            return {}

        files_by_dataset: dict[str, list[Path]] = {}

        for result in self._combination_results:
            if result.status != "success":
                continue

            news_impact_path = (
                self.configuration.paths.indices_root(
                    result.model_key,
                    result.dataset_key,
                )
                / "news_impact.csv"
            )
            if not news_impact_path.is_file():
                continue

            files_by_dataset.setdefault(
                result.dataset_key,
                [],
            ).append(news_impact_path)

        merge_results = merge_uncertainty_across_models(
            configuration=self.configuration,
            news_impact_files=files_by_dataset,
        )

        outputs: dict[str, dict[str, str]] = {}
        for merge_result in merge_results:
            saved = self.results.save_uncertainty_merge(merge_result)
            outputs[merge_result.dataset_key] = saved
            self.logger.info(
                "Incerteza consolidada para dataset %s em %s.",
                merge_result.dataset_key,
                saved.get("iti_uncertainty_daily"),
            )

        return outputs

    def _execute_combination(
        self,
        combination: ExperimentCombination,
        *,
        next_model_key: str | None = None,
    ) -> CombinationRunResult:
        return execute_combination(
            self,
            combination,
            next_model_key=next_model_key,
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
        save_artifacts = bool(
            self.configuration.execution.get(
                "save_failure_artifacts",
                self.configuration.execution.get(
                    "save_partial_results",
                    True,
                ),
            )
        )
        if not save_artifacts:
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
        if loaded_dataset is not None:
            return build_error_execution_metrics(
                configuration=self.configuration,
                combination=combination,
                model_configuration=model_configuration,
                loaded_dataset=loaded_dataset,
                error=error,
                performance_monitor=monitor,
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
            )

        timestamp = _experiment_now_iso(self.configuration)
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
            "started_at": timestamp,
            "finished_at": timestamp,
            "device_type": str(
                model_configuration.parameters.get(
                    "device",
                    "unknown",
                )
            ),
            "batch_size": int(
                model_configuration.parameters["batch_size"]
            ),
            "max_length": int(
                model_configuration.parameters["max_length"]
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
        *,
        next_model_key: str | None = None,
    ) -> None:
        unload = bool(
            self.configuration.execution.get(
                "unload_model_after_combination",
                True,
            )
        )
        if not unload or self._registry is None:
            return
        if next_model_key == model_key:
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
            release_python_and_cuda_memory()

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
        release_python_and_cuda_memory()

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
        prog="python -m modules.experiment",
        description=(
            "Executa a matriz de modelos e datasets configurada no "
            "financial-sentiment-lab."
        ),
    )
    parser.add_argument(
        "--model",
        dest="model_keys",
        action="append",
        default=None,
        help="Seleciona temporariamente um modelo.",
    )
    parser.add_argument(
        "--dataset",
        dest="dataset_keys",
        action="append",
        default=None,
        help="Seleciona temporariamente um dataset.",
    )
    parser.add_argument(
        "--environment",
        choices=("local", "sdumont"),
        default=None,
        help="Sobrescreve execution.environment.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Valida tudo sem executar inferência (uso interno do audit).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Sobrescreve experiment.run_id.",
    )
    parser.add_argument(
        "--experiment-config",
        default=None,
        help="Caminho alternativo para configs/experiment.yaml.",
    )
    parser.set_defaults(dry_run=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)

    try:
        outcome = run_experiment(
            model_keys=arguments.model_keys,
            dataset_keys=arguments.dataset_keys,
            environment=arguments.environment,
            dry_run=arguments.dry_run,
            run_id=arguments.run_id,
            experiment_config=arguments.experiment_config or DEFAULT_EXPERIMENT_CONFIG,
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
        return EXIT_CONFIGURATION_ERROR
    except Exception as error:
        print(
            f"Erro durante a execução: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
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


def _experiment_now_iso(
    configuration: ResolvedConfiguration,
) -> str:
    return now_iso(
        timezone_name=str(
            configuration.experiment.get(
                "timezone",
                "UTC",
            )
        )
    )


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
