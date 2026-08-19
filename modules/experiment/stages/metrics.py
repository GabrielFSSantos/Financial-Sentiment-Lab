"""Cálculo de métricas de classificação e desempenho.

Este módulo trabalha sobre o DataFrame padronizado por
``pipeline.output_schema`` e produz os arquivos tabulares esperados por
``pipeline.results``:

- classification_metrics.csv;
- per_class_metrics.csv;
- confusion_matrix.csv;
- class_distribution.csv;
- execution_metrics.csv.

O módulo não salva arquivos em disco. Ele apenas retorna DataFrames e
metadados prontos para o ``ResultsManager``.
"""

from __future__ import annotations

import importlib.metadata
import math
import os
import platform
import socket
import sys
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator, Mapping, Sequence, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from modules.experiment.config.loader import (
    DatasetConfiguration,
    ExperimentCombination,
    ModelConfiguration,
    ResolvedConfiguration,
)
from modules.datasets.loader import LoadedDataset
from modules.experiment.common import CANONICAL_LABELS, resolve_timezone
from modules.experiment.io.output_schema import StandardizedPredictions


IDENTITY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "environment",
    "combination_id",
    "combination_index",
    "model_key",
    "model_name",
    "dataset_key",
    "dataset_name",
)

CLASSIFICATION_METRICS_COLUMNS: tuple[str, ...] = (
    *IDENTITY_COLUMNS,
    "metrics_enabled",
    "classification_available",
    "status",
    "reason",
    "labels",
    "total_rows",
    "evaluated_rows",
    "ignored_unlabeled_rows",
    "correct_predictions",
    "accuracy",
    "precision_macro",
    "recall_macro",
    "f1_macro",
    "precision_weighted",
    "recall_weighted",
    "f1_weighted",
    "precision_micro",
    "recall_micro",
    "f1_micro",
)

PER_CLASS_METRICS_COLUMNS: tuple[str, ...] = (
    *IDENTITY_COLUMNS,
    "label",
    "precision",
    "recall",
    "f1",
    "support",
    "predicted_count",
)

CONFUSION_MATRIX_COLUMNS: tuple[str, ...] = (
    *IDENTITY_COLUMNS,
    "true_label",
    *CANONICAL_LABELS,
)

CLASS_DISTRIBUTION_COLUMNS: tuple[str, ...] = (
    *IDENTITY_COLUMNS,
    "distribution_type",
    "label",
    "count",
    "percentage",
    "total",
)

EXECUTION_METRICS_COLUMNS: tuple[str, ...] = (
    *IDENTITY_COLUMNS,
    "status",
    "error_type",
    "error_message",
    "started_at",
    "finished_at",
    "load_time_seconds",
    "inference_time_seconds",
    "total_time_seconds",
    "texts_per_second",
    "peak_gpu_memory_mb",
    "device_type",
    "device_name",
    "batch_size",
    "max_length",
    "num_rows",
    "num_valid_texts",
    "hostname",
    "process_id",
    "python_version",
    "torch_version",
    "cuda_available",
    "torch_cuda_version",
    "slurm_job_id",
    "slurm_array_job_id",
    "slurm_array_task_id",
)


class MetricsError(RuntimeError):
    """Erro-base durante o cálculo ou monitoramento de métricas."""


class MetricsConfigurationError(MetricsError, ValueError):
    """Configuração de métricas inválida."""


class ClassificationMetricsError(MetricsError, ValueError):
    """Falha no cálculo das métricas supervisionadas."""


class PerformanceMetricsError(MetricsError, RuntimeError):
    """Falha na medição de desempenho."""


@dataclass(frozen=True)
class ClassificationMetricsResult:
    """Conjunto completo de métricas de classificação."""

    summary: pd.DataFrame
    per_class: pd.DataFrame
    confusion_matrix: pd.DataFrame
    class_distribution: pd.DataFrame
    enabled: bool
    available: bool
    evaluated_rows: int
    ignored_unlabeled_rows: int
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def metadata(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "evaluated_rows": self.evaluated_rows,
            "ignored_unlabeled_rows": self.ignored_unlabeled_rows,
            "warnings": list(self.warnings),
            "summary_rows": len(self.summary),
            "per_class_rows": len(self.per_class),
            "confusion_matrix_rows": len(self.confusion_matrix),
            "class_distribution_rows": len(self.class_distribution),
        }


@dataclass(frozen=True)
class PhaseMeasurement:
    """Medição de uma fase da execução."""

    name: str
    elapsed_seconds: float
    started_at: str
    finished_at: str
    text_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PerformanceSnapshot:
    """Estado final do monitor de desempenho."""

    started_at: str
    finished_at: str
    total_time_seconds: float
    load_time_seconds: float | None
    inference_time_seconds: float | None
    texts_per_second: float | None
    peak_gpu_memory_mb: float | None
    device_type: str
    device_name: str
    measured_text_count: int | None
    phases: tuple[PhaseMeasurement, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["phases"] = [
            phase.to_dict()
            for phase in self.phases
        ]
        return payload


class ClassificationMetricsCalculator:
    """Calcula métricas para uma única combinação modelo × dataset."""

    def __init__(
        self,
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        self.settings = dict(settings or {})
        self.enabled = bool(
            self.settings.get("enabled", True)
        )
        self.labels = _normalize_labels(
            self.settings.get(
                "labels",
                CANONICAL_LABELS,
            )
        )
        self.zero_division = _normalize_zero_division(
            self.settings.get("zero_division", 0)
        )
        self.allow_unlabeled_datasets = bool(
            self.settings.get(
                "allow_unlabeled_datasets",
                True,
            )
        )
        self.save_per_class_metrics = bool(
            self.settings.get(
                "save_per_class_metrics",
                True,
            )
        )
        self.save_confusion_matrix = bool(
            self.settings.get(
                "save_confusion_matrix",
                True,
            )
        )
        self.save_class_distribution = bool(
            self.settings.get(
                "save_class_distribution",
                True,
            )
        )

    def calculate(
        self,
        predictions: StandardizedPredictions | pd.DataFrame,
    ) -> ClassificationMetricsResult:
        """Calcula métricas gerais, por classe e distribuições."""

        dataframe = _prediction_dataframe(predictions)
        identity = _extract_identity(dataframe)
        total_rows = len(dataframe)

        self._validate_dataframe(dataframe)

        distribution = (
            self._class_distribution(dataframe, identity)
            if self.save_class_distribution
            else empty_class_distribution()
        )

        if not self.enabled:
            summary = self._unavailable_summary(
                identity=identity,
                total_rows=total_rows,
                ignored_unlabeled_rows=int(
                    dataframe["true_label"].isna().sum()
                ),
                reason="classification_metrics_disabled",
                metrics_enabled=False,
            )
            return ClassificationMetricsResult(
                summary=summary,
                per_class=empty_per_class_metrics(),
                confusion_matrix=empty_confusion_matrix(),
                class_distribution=distribution,
                enabled=False,
                available=False,
                evaluated_rows=0,
                ignored_unlabeled_rows=int(
                    dataframe["true_label"].isna().sum()
                ),
            )

        true_labels = dataframe["true_label"].astype("string")
        valid_mask = true_labels.notna()
        evaluated_rows = int(valid_mask.sum())
        ignored_unlabeled_rows = total_rows - evaluated_rows

        if evaluated_rows == 0:
            if not self.allow_unlabeled_datasets:
                raise ClassificationMetricsError(
                    "O dataset não possui rótulos verdadeiros e "
                    "classification_metrics.allow_unlabeled_datasets=false."
                )

            summary = self._unavailable_summary(
                identity=identity,
                total_rows=total_rows,
                ignored_unlabeled_rows=ignored_unlabeled_rows,
                reason="dataset_without_true_labels",
                metrics_enabled=True,
            )
            return ClassificationMetricsResult(
                summary=summary,
                per_class=empty_per_class_metrics(),
                confusion_matrix=empty_confusion_matrix(),
                class_distribution=distribution,
                enabled=True,
                available=False,
                evaluated_rows=0,
                ignored_unlabeled_rows=ignored_unlabeled_rows,
                warnings=(
                    "Métricas supervisionadas não foram calculadas "
                    "porque o dataset não possui true_label.",
                ),
            )

        evaluation = dataframe.loc[
            valid_mask,
            ["true_label", "predicted_label"],
        ].copy()

        evaluation["true_label"] = _normalize_label_series(
            evaluation["true_label"],
            column_name="true_label",
        )
        evaluation["predicted_label"] = _normalize_label_series(
            evaluation["predicted_label"],
            column_name="predicted_label",
        )

        y_true = evaluation["true_label"].to_numpy()
        y_pred = evaluation["predicted_label"].to_numpy()

        accuracy = float(accuracy_score(y_true, y_pred))
        correct_predictions = int(np.sum(y_true == y_pred))

        macro = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=list(self.labels),
            average="macro",
            zero_division=cast(Any, self.zero_division),
        )
        weighted = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=list(self.labels),
            average="weighted",
            zero_division=cast(Any, self.zero_division),
        )
        micro = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=list(self.labels),
            average="micro",
            zero_division=cast(Any, self.zero_division),
        )

        summary_row = {
            **identity,
            "metrics_enabled": True,
            "classification_available": True,
            "status": "success",
            "reason": pd.NA,
            "labels": ",".join(self.labels),
            "total_rows": total_rows,
            "evaluated_rows": evaluated_rows,
            "ignored_unlabeled_rows": ignored_unlabeled_rows,
            "correct_predictions": correct_predictions,
            "accuracy": accuracy,
            "precision_macro": float(macro[0]),
            "recall_macro": float(macro[1]),
            "f1_macro": float(macro[2]),
            "precision_weighted": float(weighted[0]),
            "recall_weighted": float(weighted[1]),
            "f1_weighted": float(weighted[2]),
            "precision_micro": float(micro[0]),
            "recall_micro": float(micro[1]),
            "f1_micro": float(micro[2]),
        }
        summary = pd.DataFrame(
            [summary_row],
            columns=pd.Index(CLASSIFICATION_METRICS_COLUMNS),
        )

        per_class = (
            self._per_class_metrics(
                y_true=y_true,
                y_pred=y_pred,
                identity=identity,
            )
            if self.save_per_class_metrics
            else empty_per_class_metrics()
        )

        confusion = (
            self._confusion_matrix(
                y_true=y_true,
                y_pred=y_pred,
                identity=identity,
            )
            if self.save_confusion_matrix
            else empty_confusion_matrix()
        )

        warnings: list[str] = []
        if ignored_unlabeled_rows:
            warnings.append(
                f"{ignored_unlabeled_rows} linha(s) sem true_label "
                "foram ignoradas nas métricas supervisionadas."
            )

        return ClassificationMetricsResult(
            summary=summary,
            per_class=per_class,
            confusion_matrix=confusion,
            class_distribution=distribution,
            enabled=True,
            available=True,
            evaluated_rows=evaluated_rows,
            ignored_unlabeled_rows=ignored_unlabeled_rows,
            warnings=tuple(warnings),
        )

    def _validate_dataframe(
        self,
        dataframe: pd.DataFrame,
    ) -> None:
        required = {
            *IDENTITY_COLUMNS,
            "true_label",
            "predicted_label",
        }
        missing = sorted(
            required - set(dataframe.columns)
        )
        if missing:
            raise ClassificationMetricsError(
                f"O DataFrame não possui colunas necessárias: {missing}."
            )

        if dataframe.empty:
            raise ClassificationMetricsError(
                "Não é possível calcular métricas para um DataFrame vazio."
            )

        _extract_identity(dataframe)

        predicted = _normalize_label_series(
            cast(pd.Series, dataframe["predicted_label"]),
            column_name="predicted_label",
        )
        invalid = set(predicted.dropna().unique()) - set(self.labels)
        if invalid:
            raise ClassificationMetricsError(
                f"predicted_label possui classes fora da configuração: "
                f"{sorted(invalid)}."
            )

        true_non_null = dataframe["true_label"].dropna()
        if not true_non_null.empty:
            normalized_true = _normalize_label_series(
                cast(pd.Series, true_non_null),
                column_name="true_label",
            )
            invalid_true = (
                set(normalized_true.unique())
                - set(self.labels)
            )
            if invalid_true:
                raise ClassificationMetricsError(
                    f"true_label possui classes fora da configuração: "
                    f"{sorted(invalid_true)}."
                )

    def _per_class_metrics(
        self,
        *,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        identity: Mapping[str, Any],
    ) -> pd.DataFrame:
        metric_values = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=list(self.labels),
            average=None,
            zero_division=cast(Any, self.zero_division),
        )
        precision_values = np.asarray(
            cast(Any, metric_values[0]),
            dtype=float,
        )
        recall_values = np.asarray(
            cast(Any, metric_values[1]),
            dtype=float,
        )
        f1_values = np.asarray(
            cast(Any, metric_values[2]),
            dtype=float,
        )
        support_raw = metric_values[3]
        support_values = (
            np.zeros(len(self.labels), dtype=int)
            if support_raw is None
            else np.asarray(cast(Any, support_raw), dtype=int)
        )
        predicted_counts = {
            label: int(np.sum(y_pred == label))
            for label in self.labels
        }

        rows = []
        for index, label in enumerate(self.labels):
            rows.append(
                {
                    **identity,
                    "label": label,
                    "precision": float(precision_values[index]),
                    "recall": float(recall_values[index]),
                    "f1": float(f1_values[index]),
                    "support": int(support_values[index]),
                    "predicted_count": predicted_counts[label],
                }
            )

        return pd.DataFrame(
            rows,
            columns=pd.Index(PER_CLASS_METRICS_COLUMNS),
        )

    def _confusion_matrix(
        self,
        *,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        identity: Mapping[str, Any],
    ) -> pd.DataFrame:
        matrix = confusion_matrix(
            y_true,
            y_pred,
            labels=list(self.labels),
        )

        rows = []
        for row_index, true_label in enumerate(self.labels):
            row = {
                **identity,
                "true_label": true_label,
            }
            for column_index, predicted_label in enumerate(
                self.labels
            ):
                row[predicted_label] = int(
                    matrix[row_index, column_index]
                )
            rows.append(row)

        columns = (
            *IDENTITY_COLUMNS,
            "true_label",
            *self.labels,
        )
        return pd.DataFrame(rows, columns=pd.Index(columns))

    def _class_distribution(
        self,
        dataframe: pd.DataFrame,
        identity: Mapping[str, Any],
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []

        rows.extend(
            _distribution_rows(
                series=_normalize_label_series(
                    cast(pd.Series, dataframe["predicted_label"]),
                    column_name="predicted_label",
                ),
                identity=identity,
                labels=self.labels,
                distribution_type="predicted",
            )
        )

        true_labels = dataframe["true_label"].dropna()
        if not true_labels.empty:
            rows.extend(
                _distribution_rows(
                    series=_normalize_label_series(
                        cast(pd.Series, true_labels),
                        column_name="true_label",
                    ),
                    identity=identity,
                    labels=self.labels,
                    distribution_type="true",
                )
            )

        return pd.DataFrame(
            rows,
            columns=pd.Index(CLASS_DISTRIBUTION_COLUMNS),
        )

    def _unavailable_summary(
        self,
        *,
        identity: Mapping[str, Any],
        total_rows: int,
        ignored_unlabeled_rows: int,
        reason: str,
        metrics_enabled: bool,
    ) -> pd.DataFrame:
        row = {
            **identity,
            "metrics_enabled": metrics_enabled,
            "classification_available": False,
            "status": "unavailable",
            "reason": reason,
            "labels": ",".join(self.labels),
            "total_rows": total_rows,
            "evaluated_rows": 0,
            "ignored_unlabeled_rows": ignored_unlabeled_rows,
            "correct_predictions": pd.NA,
            "accuracy": pd.NA,
            "precision_macro": pd.NA,
            "recall_macro": pd.NA,
            "f1_macro": pd.NA,
            "precision_weighted": pd.NA,
            "recall_weighted": pd.NA,
            "f1_weighted": pd.NA,
            "precision_micro": pd.NA,
            "recall_micro": pd.NA,
            "f1_micro": pd.NA,
        }
        return pd.DataFrame(
            [row],
            columns=pd.Index(CLASSIFICATION_METRICS_COLUMNS),
        )


class CombinationPerformanceMonitor:
    """Mede carregamento, inferência, tempo total e memória CUDA.

    Uso esperado::

        with CombinationPerformanceMonitor(
            device=registered_model.device_type,
            timezone_name="America/Sao_Paulo",
            settings=config.performance_metrics,
        ) as monitor:
            with monitor.measure_load():
                registered_model.load()

            with monitor.measure_inference(text_count=len(texts)):
                predictions = registered_model.predict(texts)

        execution = monitor.build_execution_metrics(...)
    """

    def __init__(
        self,
        *,
        device: str | torch.device = "cpu",
        timezone_name: str = "UTC",
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        self.settings = dict(settings or {})
        self.enabled = bool(
            self.settings.get("enabled", True)
        )
        self.measure_load_time = bool(
            self.settings.get("measure_load_time", True)
        )
        self.measure_inference_time = bool(
            self.settings.get("measure_inference_time", True)
        )
        self.measure_total_time = bool(
            self.settings.get("measure_total_time", True)
        )
        self.measure_throughput = bool(
            self.settings.get("measure_throughput", True)
        )
        self.measure_gpu_memory = bool(
            self.settings.get("measure_gpu_memory", True)
        )

        self.timezone = resolve_timezone(timezone_name)
        self.device = _normalize_device(device)
        self._phases: list[PhaseMeasurement] = []
        self._active_phase: str | None = None
        self._started = False
        self._finished = False
        self._started_at: datetime | None = None
        self._finished_at: datetime | None = None
        self._start_counter: float | None = None
        self._total_time_seconds: float | None = None
        self._peak_gpu_memory_mb: float | None = None
        self._measured_text_count: int | None = None

    @property
    def snapshot(self) -> PerformanceSnapshot:
        if not self._finished:
            raise PerformanceMetricsError(
                "O monitor ainda não foi finalizado."
            )

        load_time = self._phase_total("load")
        inference_time = self._phase_total("inference")

        texts_per_second: float | None = None
        if (
            self.measure_throughput
            and inference_time is not None
            and inference_time > 0
            and self._measured_text_count is not None
        ):
            texts_per_second = (
                self._measured_text_count
                / inference_time
            )

        started_at = self._started_at
        finished_at = self._finished_at
        total_time = self._total_time_seconds

        if (
            started_at is None
            or finished_at is None
            or total_time is None
        ):
            raise PerformanceMetricsError(
                "Estado interno incompleto no monitor de desempenho."
            )

        return PerformanceSnapshot(
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            total_time_seconds=round(total_time, 6),
            load_time_seconds=(
                round(load_time, 6)
                if load_time is not None
                and self.measure_load_time
                else None
            ),
            inference_time_seconds=(
                round(inference_time, 6)
                if inference_time is not None
                and self.measure_inference_time
                else None
            ),
            texts_per_second=(
                round(texts_per_second, 6)
                if texts_per_second is not None
                else None
            ),
            peak_gpu_memory_mb=(
                round(self._peak_gpu_memory_mb, 4)
                if self._peak_gpu_memory_mb is not None
                else None
            ),
            device_type=self.device.type,
            device_name=_device_name(self.device),
            measured_text_count=self._measured_text_count,
            phases=tuple(self._phases),
        )

    def start(self) -> None:
        if self._started and not self._finished:
            raise PerformanceMetricsError(
                "O monitor já está em execução."
            )

        if self.device.type == "cuda":
            _validate_cuda_device(self.device)
            torch.cuda.synchronize(self.device)
            if self.measure_gpu_memory:
                torch.cuda.reset_peak_memory_stats(self.device)

        self._phases.clear()
        self._active_phase = None
        self._started_at = datetime.now(self.timezone)
        self._start_counter = perf_counter()
        self._finished_at = None
        self._total_time_seconds = None
        self._peak_gpu_memory_mb = None
        self._measured_text_count = None
        self._started = True
        self._finished = False

    def stop(self) -> PerformanceSnapshot:
        if not self._started:
            raise PerformanceMetricsError(
                "O monitor não foi iniciado."
            )

        if self._active_phase is not None:
            raise PerformanceMetricsError(
                f"A fase {self._active_phase!r} ainda está aberta."
            )

        if self._finished:
            return self.snapshot

        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

        now_counter = perf_counter()
        now_datetime = datetime.now(self.timezone)

        if self._start_counter is None:
            raise PerformanceMetricsError(
                "Contador inicial ausente."
            )

        self._total_time_seconds = max(
            0.0,
            now_counter - self._start_counter,
        )
        self._finished_at = now_datetime

        if (
            self.device.type == "cuda"
            and self.measure_gpu_memory
        ):
            peak_bytes = torch.cuda.max_memory_allocated(
                self.device
            )
            self._peak_gpu_memory_mb = (
                float(peak_bytes) / 1024.0 / 1024.0
            )

        self._finished = True
        return self.snapshot

    @contextmanager
    def phase(
        self,
        name: str,
        *,
        text_count: int | None = None,
    ) -> Iterator[None]:
        if not self._started or self._finished:
            raise PerformanceMetricsError(
                "Inicie o monitor antes de medir uma fase."
            )

        normalized_name = str(name).strip().lower()
        if not normalized_name:
            raise PerformanceMetricsError(
                "O nome da fase não pode ser vazio."
            )

        if self._active_phase is not None:
            raise PerformanceMetricsError(
                f"Não é possível iniciar {normalized_name!r}; "
                f"a fase {self._active_phase!r} ainda está ativa."
            )

        normalized_text_count: int | None = None
        if text_count is not None:
            normalized_text_count = _non_negative_integer(
                text_count,
                "text_count",
            )

        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

        started_at = datetime.now(self.timezone)
        started_counter = perf_counter()
        self._active_phase = normalized_name

        try:
            yield
        finally:
            if self.device.type == "cuda":
                torch.cuda.synchronize(self.device)

            finished_counter = perf_counter()
            finished_at = datetime.now(self.timezone)
            elapsed = max(
                0.0,
                finished_counter - started_counter,
            )

            self._phases.append(
                PhaseMeasurement(
                    name=normalized_name,
                    elapsed_seconds=round(elapsed, 6),
                    started_at=started_at.isoformat(),
                    finished_at=finished_at.isoformat(),
                    text_count=normalized_text_count,
                )
            )

            if (
                normalized_name == "inference"
                and normalized_text_count is not None
            ):
                self._measured_text_count = (
                    normalized_text_count
                )

            self._active_phase = None

    def measure_load(self) -> AbstractContextManager[None]:
        return self.phase("load")

    def measure_inference(
        self,
        *,
        text_count: int,
    ) -> AbstractContextManager[None]:
        return self.phase(
            "inference",
            text_count=text_count,
        )

    def __enter__(self) -> "CombinationPerformanceMonitor":
        self.start()
        return self

    def __exit__(
        self,
        exception_type: Any,
        exception_value: Any,
        traceback: Any,
    ) -> None:
        self.stop()

    def build_execution_metrics(
        self,
        *,
        configuration: ResolvedConfiguration,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        loaded_dataset: LoadedDataset,
        status: str = "success",
        error: BaseException | str | None = None,
        device_type: str | None = None,
        device_name: str | None = None,
        num_valid_texts: int | None = None,
    ) -> pd.DataFrame:
        """Cria uma linha de métricas computacionais."""

        if not self._finished:
            self.stop()

        snapshot = self.snapshot
        normalized_status = _normalize_execution_status(status)

        error_type: Any = pd.NA
        error_message: Any = pd.NA

        if error is not None:
            if isinstance(error, BaseException):
                error_type = type(error).__name__
                error_message = str(error)
            else:
                error_type = "Error"
                error_message = str(error)

        if normalized_status == "failed" and error is None:
            error_type = "Error"
            error_message = "Erro não especificado."

        valid_texts = (
            loaded_dataset.statistics.valid_row_count
            if num_valid_texts is None
            else _non_negative_integer(
                num_valid_texts,
                "num_valid_texts",
            )
        )
        num_rows = loaded_dataset.statistics.original_row_count

        actual_device_type = (
            str(device_type).strip().lower()
            if device_type is not None
            else snapshot.device_type
        )
        actual_device_name = (
            str(device_name).strip()
            if device_name is not None
            and str(device_name).strip()
            else snapshot.device_name
        )

        if actual_device_type == "cpu":
            peak_gpu_memory_mb: float | None = None
        else:
            peak_gpu_memory_mb = snapshot.peak_gpu_memory_mb

        row = {
            **_identity_from_context(
                configuration=configuration,
                combination=combination,
                model_configuration=model_configuration,
                dataset_configuration=loaded_dataset.configuration,
            ),
            "status": normalized_status,
            "error_type": error_type,
            "error_message": error_message,
            "started_at": snapshot.started_at,
            "finished_at": snapshot.finished_at,
            "load_time_seconds": snapshot.load_time_seconds,
            "inference_time_seconds": snapshot.inference_time_seconds,
            "total_time_seconds": (
                snapshot.total_time_seconds
                if self.measure_total_time
                else pd.NA
            ),
            "texts_per_second": snapshot.texts_per_second,
            "peak_gpu_memory_mb": peak_gpu_memory_mb,
            "device_type": actual_device_type,
            "device_name": actual_device_name,
            "batch_size": int(
                model_configuration.parameters["batch_size"]
            ),
            "max_length": int(
                model_configuration.parameters["max_length"]
            ),
            "num_rows": int(num_rows),
            "num_valid_texts": int(valid_texts),
            "hostname": socket.gethostname(),
            "process_id": os.getpid(),
            "python_version": platform.python_version(),
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

    def _phase_total(self, name: str) -> float | None:
        values = [
            phase.elapsed_seconds
            for phase in self._phases
            if phase.name == name
        ]
        if not values:
            return None
        return float(sum(values))


def build_error_execution_metrics(
    *,
    configuration: ResolvedConfiguration,
    combination: ExperimentCombination,
    model_configuration: ModelConfiguration,
    loaded_dataset: LoadedDataset,
    error: BaseException | str,
    performance_monitor: CombinationPerformanceMonitor | None = None,
    device_type: str | None = None,
    device_name: str | None = None,
) -> pd.DataFrame:
    """Cria execution_metrics.csv mesmo quando a combinação falha."""

    monitor = performance_monitor

    if monitor is None:
        monitor = CombinationPerformanceMonitor(
            device=device_type or "cpu",
            timezone_name=str(
                configuration.experiment.get(
                    "timezone",
                    "UTC",
                )
            ),
            settings=configuration.performance_metrics,
        )
        monitor.start()
        monitor.stop()

    return monitor.build_execution_metrics(
        configuration=configuration,
        combination=combination,
        model_configuration=model_configuration,
        loaded_dataset=loaded_dataset,
        status="failed",
        error=error,
        device_type=device_type,
        device_name=device_name,
        num_valid_texts=(
            loaded_dataset.statistics.valid_row_count
        ),
    )


def empty_classification_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        columns=pd.Index(CLASSIFICATION_METRICS_COLUMNS)
    )


def empty_per_class_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        columns=pd.Index(PER_CLASS_METRICS_COLUMNS)
    )


def empty_confusion_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        columns=pd.Index(CONFUSION_MATRIX_COLUMNS)
    )


def empty_class_distribution() -> pd.DataFrame:
    return pd.DataFrame(
        columns=pd.Index(CLASS_DISTRIBUTION_COLUMNS)
    )


def empty_execution_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        columns=pd.Index(EXECUTION_METRICS_COLUMNS)
    )


def collect_runtime_metadata() -> dict[str, Any]:
    """Coleta versões, hardware, CUDA e variáveis do Slurm."""

    cuda_available = bool(torch.cuda.is_available())
    devices: list[dict[str, Any]] = []

    if cuda_available:
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            devices.append(
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "total_memory_mb": round(
                        float(properties.total_memory)
                        / 1024.0
                        / 1024.0,
                        2,
                    ),
                    "compute_capability": (
                        f"{int(properties.major)}."
                        f"{int(properties.minor)}"
                    ),
                    "multi_processor_count": int(
                        properties.multi_processor_count
                    ),
                }
            )

    return {
        "hostname": socket.gethostname(),
        "process_id": os.getpid(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python": {
            "version": platform.python_version(),
            "implementation": (
                platform.python_implementation()
            ),
            "executable": sys.executable,
        },
        "libraries": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "torch": torch.__version__,
            "scikit_learn": _package_version(
                "scikit-learn"
            ),
        },
        "cuda": {
            "available": cuda_available,
            "torch_cuda_version": torch.version.cuda,
            "cudnn_version": (
                torch.backends.cudnn.version()
                if cuda_available
                else None
            ),
            "device_count": (
                torch.cuda.device_count()
                if cuda_available
                else 0
            ),
            "devices": devices,
        },
        "slurm": collect_slurm_metadata(),
    }


def collect_slurm_metadata() -> dict[str, str]:
    """Coleta somente variáveis do Slurm presentes no ambiente."""

    names = (
        "SLURM_JOB_ID",
        "SLURM_JOB_NAME",
        "SLURM_JOB_PARTITION",
        "SLURM_JOB_ACCOUNT",
        "SLURM_NODELIST",
        "SLURM_NNODES",
        "SLURM_NTASKS",
        "SLURM_CPUS_PER_TASK",
        "SLURM_GPUS",
        "SLURM_JOB_GPUS",
        "SLURM_ARRAY_JOB_ID",
        "SLURM_ARRAY_TASK_ID",
        "SLURM_SUBMIT_DIR",
    )

    return {
        name: value
        for name in names
        if (value := os.getenv(name)) is not None
    }


def _prediction_dataframe(
    value: StandardizedPredictions | pd.DataFrame,
) -> pd.DataFrame:
    if isinstance(value, StandardizedPredictions):
        dataframe = value.dataframe
        if not isinstance(dataframe, pd.DataFrame):
            raise ClassificationMetricsError(
                "StandardizedPredictions.dataframe precisa ser um "
                "pandas.DataFrame."
            )
    elif isinstance(value, pd.DataFrame):
        dataframe = value
    else:
        raise ClassificationMetricsError(
            "predictions precisa ser StandardizedPredictions "
            "ou pandas.DataFrame."
        )

    return dataframe.copy()


def _extract_identity(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    missing = [
        column
        for column in IDENTITY_COLUMNS
        if column not in dataframe.columns
    ]
    if missing:
        raise ClassificationMetricsError(
            f"Colunas de identidade ausentes: {missing}."
        )

    identity: dict[str, Any] = {}
    for column in IDENTITY_COLUMNS:
        values = dataframe[column].drop_duplicates().tolist()
        if len(values) != 1:
            raise ClassificationMetricsError(
                f"A coluna {column!r} precisa conter um único valor; "
                f"foram encontrados {values[:20]}."
            )
        identity[column] = values[0]

    return identity


def _identity_from_context(
    *,
    configuration: ResolvedConfiguration,
    combination: ExperimentCombination,
    model_configuration: ModelConfiguration,
    dataset_configuration: DatasetConfiguration,
) -> dict[str, Any]:
    if combination.model_key != model_configuration.key:
        raise MetricsConfigurationError(
            "A combinação e o ModelConfiguration possuem chaves "
            "de modelo diferentes."
        )

    if combination.dataset_key != dataset_configuration.key:
        raise MetricsConfigurationError(
            "A combinação e o DatasetConfiguration possuem chaves "
            "de dataset diferentes."
        )

    return {
        "run_id": configuration.run_id,
        "environment": configuration.environment,
        "combination_id": combination.combination_id,
        "combination_index": combination.index,
        "model_key": model_configuration.key,
        "model_name": model_configuration.model_name,
        "dataset_key": dataset_configuration.key,
        "dataset_name": dataset_configuration.dataset_name,
    }


def _distribution_rows(
    *,
    series: pd.Series,
    identity: Mapping[str, Any],
    labels: Sequence[str],
    distribution_type: str,
) -> list[dict[str, Any]]:
    total = int(len(series))
    counts = series.value_counts()

    rows = []
    for label in labels:
        raw_count = counts.get(label, 0)
        count = int(0 if raw_count is None else raw_count)
        percentage = (
            (count / total) * 100.0
            if total > 0
            else 0.0
        )
        rows.append(
            {
                **identity,
                "distribution_type": distribution_type,
                "label": label,
                "count": count,
                "percentage": float(percentage),
                "total": total,
            }
        )
    return rows


def _normalize_label_series(
    series: pd.Series,
    *,
    column_name: str,
) -> pd.Series:
    normalized = series.astype("string").str.strip().str.upper()
    invalid = (
        set(normalized.dropna().unique())
        - set(CANONICAL_LABELS)
    )
    if invalid:
        raise ClassificationMetricsError(
            f"A coluna {column_name!r} possui classes inválidas: "
            f"{sorted(invalid)}."
        )
    return normalized


def _normalize_labels(
    labels: Any,
) -> tuple[str, ...]:
    if isinstance(labels, (str, bytes)):
        raise MetricsConfigurationError(
            "classification_metrics.labels precisa ser uma lista."
        )

    try:
        values = tuple(
            str(label).strip().upper()
            for label in labels
        )
    except TypeError as error:
        raise MetricsConfigurationError(
            "classification_metrics.labels precisa ser iterável."
        ) from error

    if not values:
        raise MetricsConfigurationError(
            "classification_metrics.labels não pode ficar vazio."
        )

    if len(values) != len(set(values)):
        raise MetricsConfigurationError(
            "classification_metrics.labels possui valores duplicados."
        )

    if set(values) != set(CANONICAL_LABELS):
        raise MetricsConfigurationError(
            "classification_metrics.labels precisa conter exatamente "
            "NEGATIVE, NEUTRAL e POSITIVE."
        )

    return values


def _normalize_zero_division(value: Any) -> int:
    if isinstance(value, bool):
        raise MetricsConfigurationError(
            "zero_division precisa ser 0 ou 1."
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as error:
        raise MetricsConfigurationError(
            "zero_division precisa ser 0 ou 1."
        ) from error

    if normalized not in {0, 1}:
        raise MetricsConfigurationError(
            "zero_division precisa ser 0 ou 1."
        )

    return normalized


def _normalize_execution_status(value: Any) -> str:
    normalized = str(value).strip().lower()
    aliases = {
        "success": "success",
        "successful": "success",
        "ok": "success",
        "failed": "failed",
        "failure": "failed",
        "error": "failed",
        "skipped": "skipped",
    }
    if normalized not in aliases:
        raise MetricsConfigurationError(
            "status precisa ser success, failed ou skipped."
        )
    return aliases[normalized]


def _normalize_device(
    device: str | torch.device,
) -> torch.device:
    if isinstance(device, str) and device.strip().lower() == "auto":
        return torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

    try:
        normalized = torch.device(device)
    except Exception as error:
        raise PerformanceMetricsError(
            f"Dispositivo inválido: {device!r}."
        ) from error

    if normalized.type not in {"cpu", "cuda"}:
        raise PerformanceMetricsError(
            "Somente dispositivos CPU ou CUDA são suportados."
        )

    if normalized.type == "cuda":
        _validate_cuda_device(normalized)

    return normalized


def _validate_cuda_device(
    device: torch.device,
) -> None:
    if not torch.cuda.is_available():
        raise PerformanceMetricsError(
            "CUDA foi solicitado, mas não está disponível."
        )

    index = (
        torch.cuda.current_device()
        if device.index is None
        else device.index
    )
    if index < 0 or index >= torch.cuda.device_count():
        raise PerformanceMetricsError(
            f"Índice CUDA inválido: {index}."
        )


def _device_name(device: torch.device) -> str:
    if device.type == "cuda":
        return str(torch.cuda.get_device_name(device))

    return (
        platform.processor()
        or platform.machine()
        or "CPU"
    )


def _non_negative_integer(
    value: Any,
    field_name: str,
) -> int:
    if isinstance(value, bool):
        raise MetricsConfigurationError(
            f"{field_name} precisa ser um inteiro não negativo."
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as error:
        raise MetricsConfigurationError(
            f"{field_name} precisa ser um inteiro não negativo."
        ) from error

    if normalized < 0:
        raise MetricsConfigurationError(
            f"{field_name} precisa ser um inteiro não negativo."
        )

    return normalized


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


__all__ = [
    "CLASSIFICATION_METRICS_COLUMNS",
    "CLASS_DISTRIBUTION_COLUMNS",
    "CONFUSION_MATRIX_COLUMNS",
    "EXECUTION_METRICS_COLUMNS",
    "IDENTITY_COLUMNS",
    "PER_CLASS_METRICS_COLUMNS",
    "ClassificationMetricsCalculator",
    "ClassificationMetricsError",
    "ClassificationMetricsResult",
    "CombinationPerformanceMonitor",
    "MetricsConfigurationError",
    "MetricsError",
    "PerformanceMetricsError",
    "PerformanceSnapshot",
    "PhaseMeasurement",
    "build_error_execution_metrics",
    "collect_runtime_metadata",
    "collect_slurm_metadata",
    "empty_class_distribution",
    "empty_classification_metrics",
    "empty_confusion_matrix",
    "empty_execution_metrics",
    "empty_per_class_metrics",
]
