"""Execução de uma combinação modelo × dataset na pipeline."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any

from modules.datasets.loader import LoadedDataset
from modules.experiment.common import deduplicate
from modules.experiment.config.loader import ExperimentCombination
from modules.experiment.indexing.temporal_index import TemporalIndexError
from modules.experiment.io.output_schema import StandardizedPredictions
from modules.experiment.pipeline.errors import ExperimentInterruptedError
from modules.experiment.pipeline.runner_support import (
    format_combination_progress,
    release_python_and_cuda_memory,
)
from modules.experiment.stages.aggregation import AggregationResult
from modules.experiment.stages.metrics import (
    ClassificationMetricsResult,
    CombinationPerformanceMonitor,
)

if TYPE_CHECKING:
    from modules.experiment.pipeline.runner import ExperimentRunner
    from modules.models.registry import RegisteredModel

from dataclasses import asdict, dataclass, field


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


def execute_combination(
    runner,
    combination: ExperimentCombination,
    *,
    next_model_key: str | None = None,
) -> CombinationRunResult:
        model_configuration = runner.configuration.get_model(
            combination.model_key
        )
        dataset_configuration = runner.configuration.get_dataset(
            combination.dataset_key
        )

        runner.results.start_combination(
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

        total_combinations = len(runner.configuration.combinations)
        combination_number = combination.index + 1

        runner.logger.info(
            "Progresso geral: %s — iniciando %s × %s.",
            format_combination_progress(
                combination_number,
                total_combinations,
            ),
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
                    runner.configuration.experiment.get(
                        "timezone",
                        "UTC",
                    )
                ),
                settings=runner.configuration.performance_metrics,
            )
            monitor.start()

            runner._raise_if_interrupted()
            loaded_dataset = runner.dataset_loader.load(
                dataset_configuration
            )

            runner._raise_if_interrupted()
            # Arquivos já validados no preflight; evita I/O repetida.
            registered_model = runner.registry.create(
                model_configuration,
                load=False,
                validate_declared_files=False,
                validate_adapter_files=False,
            )

            with monitor.measure_load():
                registered_model.load(skip_file_validation=True)

            runner._raise_if_interrupted()
            texts = loaded_dataset.texts
            with monitor.measure_inference(
                text_count=len(texts)
            ):
                raw_predictions = registered_model.predict(texts)

            runner._raise_if_interrupted()
            standardized = runner.output_builder.build(
                run_id=runner.configuration.run_id,
                environment=runner.configuration.environment,
                combination=combination,
                model_configuration=model_configuration,
                loaded_dataset=loaded_dataset,
                predictions=raw_predictions,
                device_used=registered_model.device_type,
            )

            classification = runner.classification_calculator.calculate(
                standardized
            )
            aggregation = runner.aggregator.aggregate(
                standardized
            )

            monitor.stop()
            execution_metrics = monitor.build_execution_metrics(
                configuration=runner.configuration,
                combination=combination,
                model_configuration=model_configuration,
                loaded_dataset=loaded_dataset,
                status="success",
                device_type=registered_model.device_type,
                device_name=registered_model.device_name,
                num_valid_texts=standardized.row_count,
            )

            metadata = runner._success_metadata(
                combination=combination,
                model=registered_model,
                dataset=loaded_dataset,
                standardized=standardized,
                classification=classification,
                aggregation=aggregation,
                monitor=monitor,
            )

            runner.results.save_combination_results(
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
                    runner.classification_calculator.labels
                ),
            )

            if runner.temporal_index_builder.enabled:
                try:
                    index_artifacts = runner.temporal_index_builder.build(
                        combination=combination,
                        predictions=standardized.dataframe,
                    )
                    runner.results.save_temporal_index(
                        combination,
                        index_artifacts,
                    )
                except TemporalIndexError as error:
                    if runner.temporal_index_builder.fail_on_error:
                        raise
                    runner.logger.warning(
                        "ITI não gerado para %s: %s",
                        combination.combination_id,
                        error,
                    )

            duration = perf_counter() - started_counter
            warnings = deduplicate(
                [
                    *loaded_dataset.warnings,
                    *standardized.warnings,
                    *classification.warnings,
                    *aggregation.warnings,
                ]
            )
            valid_text_count = (
                loaded_dataset.statistics.valid_row_count
            )

            runner.results.complete_combination(
                combination,
                duration_seconds=duration,
                row_count=standardized.row_count,
                valid_text_count=valid_text_count,
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

            del raw_predictions, loaded_dataset, texts
            release_python_and_cuda_memory()

            runner.logger.info(
                "Progresso geral: %s — %s × %s concluída em %.3f s "
                "(%d linha(s)).",
                format_combination_progress(
                    combination_number,
                    total_combinations,
                ),
                combination.model_key,
                combination.dataset_key,
                duration,
                standardized.row_count,
            )

            return CombinationRunResult(
                combination_id=combination.combination_id,
                model_key=combination.model_key,
                dataset_key=combination.dataset_key,
                status="success",
                duration_seconds=round(duration, 6),
                row_count=standardized.row_count,
                valid_text_count=valid_text_count,
                device=registered_model.device_type,
                warnings=tuple(warnings),
            )

        except ExperimentInterruptedError:
            raise
        except Exception as error:
            duration = perf_counter() - started_counter
            runner._log_combination_error(combination, error)

            if monitor is not None:
                try:
                    monitor.stop()
                except Exception:
                    runner.logger.debug(
                        "Não foi possível finalizar o monitor após erro.",
                        exc_info=True,
                    )

            runner._save_failure_artifacts(
                combination=combination,
                model_configuration=model_configuration,
                dataset_configuration=dataset_configuration,
                loaded_dataset=loaded_dataset,
                registered_model=registered_model,
                monitor=monitor,
                error=error,
            )

            runner.results.fail_combination(
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

            runner.logger.error(
                "Progresso geral: %s — %s × %s falhou em %.3f s.",
                format_combination_progress(
                    combination_number,
                    total_combinations,
                ),
                combination.model_key,
                combination.dataset_key,
                duration,
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
            runner._release_model_after_combination(
                combination.model_key,
                next_model_key=next_model_key,
            )
