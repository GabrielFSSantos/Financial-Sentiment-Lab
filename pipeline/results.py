"""Criação, gravação e resumo dos resultados da pipeline.

Estrutura produzida:

outputs/<run_id>/
├── summary.json
├── resolved_config.yaml
└── models/<modelo>/<dataset>/
    ├── predictions.csv
    ├── classification_metrics.csv
    ├── per_class_metrics.csv
    ├── confusion_matrix.csv
    ├── class_distribution.csv
    ├── execution_metrics.csv
    ├── aggregates.csv
    └── metadata.json
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import tempfile
import threading
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
import yaml

from pipeline.configuration import (
    ExperimentCombination,
    ResolvedConfiguration,
)
from pipeline.temporal_index import (
    RESAMPLE_OUTPUT_NAMES,
    TemporalIndexArtifacts,
    UncertaintyMergeResult,
)


FINAL_STATUSES = {"success", "failed", "skipped"}


class ResultsError(RuntimeError):
    """Erro ao preparar ou salvar resultados."""


@dataclass(frozen=True)
class CombinationOutputPaths:
    """Caminhos dos arquivos de uma combinação modelo × dataset."""

    root: Path
    predictions: Path
    classification_metrics: Path
    per_class_metrics: Path
    confusion_matrix: Path
    class_distribution: Path
    execution_metrics: Path
    aggregates: Path
    metadata: Path

    def to_dict(self) -> dict[str, str]:
        return {
            key: str(value)
            for key, value in asdict(self).items()
        }


@dataclass(frozen=True)
class IndexOutputPaths:
    """Caminhos dos arquivos de índice temporal."""

    root: Path
    news_impact: Path
    iti_daily: Path
    iti_sector_daily: Path
    iti_market_daily: Path

    def to_dict(self) -> dict[str, str]:
        return {
            key: str(value)
            for key, value in asdict(self).items()
        }


@dataclass
class CombinationRecord:
    """Resumo de execução de uma combinação."""

    index: int
    combination_id: str
    model_key: str
    dataset_key: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    row_count: int | None = None
    valid_text_count: int | None = None
    device: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    output_files: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serializable(asdict(self))


class ResultsManager:
    """Gerencia a saída completa de um experimento."""

    def __init__(self, config: ResolvedConfiguration) -> None:
        self.config = config
        self.paths = config.paths
        self.options = dict(config.outputs)
        self.execution = dict(config.execution)
        self._lock = threading.RLock()
        self._prepared = False
        self._finalized = False
        self._started_at = self._now()
        self._finished_at: str | None = None
        self._summary_extra: dict[str, Any] = {}
        self._files: dict[str, dict[str, str]] = {}
        self._records = {
            item.combination_id: CombinationRecord(
                index=item.index,
                combination_id=item.combination_id,
                model_key=item.model_key,
                dataset_key=item.dataset_key,
            )
            for item in config.combinations
        }
        self._validate_options()

    @property
    def write_enabled(self) -> bool:
        """Dry-run valida, mas não cria resultados."""

        return not self.config.dry_run

    @property
    def summary_path(self) -> Path:
        return self.paths.run_root / "summary.json"

    @property
    def resolved_config_path(self) -> Path:
        return self.paths.run_root / "resolved_config.yaml"

    def prepare(self) -> None:
        """Prepara a pasta do run_id e os arquivos gerais."""

        with self._lock:
            if self._prepared:
                return

            if not self.write_enabled:
                self._prepared = True
                return

            run_root = self.paths.run_root
            overwrite = bool(
                self.execution.get("overwrite_existing_run", False)
            )

            if run_root.exists() and any(run_root.iterdir()):
                if not overwrite:
                    raise ResultsError(
                        f"Já existem resultados para {self.config.run_id!r}: "
                        f"{run_root}. Use outro run_id ou habilite "
                        "execution.overwrite_existing_run."
                    )
                shutil.rmtree(run_root)

            self.paths.output_root.mkdir(parents=True, exist_ok=True)
            self.paths.models_output_root.mkdir(
                parents=True,
                exist_ok=True,
            )
            self._prepared = True

            if self._enabled("save_resolved_config"):
                self._write_yaml(
                    self.resolved_config_path,
                    self.config.to_dict(),
                )

            self._save_summary_if_enabled()

    def combination_paths(
        self,
        combination: ExperimentCombination,
    ) -> CombinationOutputPaths:
        """Retorna os caminhos oficiais de uma combinação."""

        self._validate_combination(combination)
        root = self.paths.combination_root(
            combination.model_key,
            combination.dataset_key,
        )
        return CombinationOutputPaths(
            root=root,
            predictions=root / "predictions.csv",
            classification_metrics=root / "classification_metrics.csv",
            per_class_metrics=root / "per_class_metrics.csv",
            confusion_matrix=root / "confusion_matrix.csv",
            class_distribution=root / "class_distribution.csv",
            execution_metrics=root / "execution_metrics.csv",
            aggregates=root / "aggregates.csv",
            metadata=root / "metadata.json",
        )

    def index_paths(
        self,
        combination: ExperimentCombination,
    ) -> IndexOutputPaths:
        self._validate_combination(combination)
        root = self.paths.indices_root(
            combination.model_key,
            combination.dataset_key,
        )
        return IndexOutputPaths(
            root=root,
            news_impact=root / "news_impact.csv",
            iti_daily=root / "iti_daily.csv",
            iti_sector_daily=root / "iti_sector_daily.csv",
            iti_market_daily=root / "iti_market_daily.csv",
        )

    # ================================================================
    # ESTADO DA EXECUÇÃO
    # ================================================================

    def start_combination(
        self,
        combination: ExperimentCombination,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> CombinationRecord:
        """Registra o início da combinação."""

        with self._lock:
            self._ensure_prepared()
            record = self._record(combination)

            if record.status != "pending":
                raise ResultsError(
                    f"A combinação {combination.combination_id} possui "
                    f"status {record.status!r} e não pode ser iniciada."
                )

            record.status = "running"
            record.started_at = self._now()
            if extra:
                record.extra.update(_serializable(dict(extra)))
            self._save_summary_if_enabled()
            return record

    def complete_combination(
        self,
        combination: ExperimentCombination,
        *,
        status: str = "success",
        duration_seconds: float | None = None,
        row_count: int | None = None,
        valid_text_count: int | None = None,
        device: str | None = None,
        error: BaseException | str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> CombinationRecord:
        """Registra sucesso, falha ou descarte da combinação."""

        status = status.strip().lower()
        if status not in FINAL_STATUSES:
            raise ResultsError(
                "status precisa ser success, failed ou skipped."
            )

        with self._lock:
            self._ensure_prepared()
            record = self._record(combination)
            finished_at = self._now()

            if record.started_at is None:
                record.started_at = finished_at

            record.status = status
            record.finished_at = finished_at
            record.duration_seconds = self._duration(
                record.started_at,
                finished_at,
                duration_seconds,
            )
            record.row_count = _non_negative_or_none(
                row_count,
                "row_count",
            )
            record.valid_text_count = _non_negative_or_none(
                valid_text_count,
                "valid_text_count",
            )
            record.device = str(device).strip() if device else None
            record.output_files = dict(
                self._files.get(combination.combination_id, {})
            )

            if error is not None:
                if isinstance(error, BaseException):
                    record.error_type = type(error).__name__
                    record.error_message = str(error)
                else:
                    record.error_type = None
                    record.error_message = str(error)
            elif status != "failed":
                record.error_type = None
                record.error_message = None

            if extra:
                record.extra.update(_serializable(dict(extra)))

            self._save_summary_if_enabled()
            return record

    def fail_combination(
        self,
        combination: ExperimentCombination,
        error: BaseException | str,
        **kwargs: Any,
    ) -> CombinationRecord:
        return self.complete_combination(
            combination,
            status="failed",
            error=error,
            **kwargs,
        )

    def skip_combination(
        self,
        combination: ExperimentCombination,
        reason: str,
        **kwargs: Any,
    ) -> CombinationRecord:
        return self.complete_combination(
            combination,
            status="skipped",
            error=reason,
            **kwargs,
        )

    # ================================================================
    # ARQUIVOS DA COMBINAÇÃO
    # ================================================================

    def save_predictions(
        self,
        combination: ExperimentCombination,
        data: Any,
    ) -> Path | None:
        if not self._enabled("save_predictions"):
            return None
        return self._save_table(
            combination,
            "predictions",
            self.combination_paths(combination).predictions,
            data,
        )

    def save_classification_metrics(
        self,
        combination: ExperimentCombination,
        data: Any,
    ) -> Path | None:
        return self._save_metric_table(
            combination,
            "classification_metrics",
            self.combination_paths(combination).classification_metrics,
            data,
        )

    def save_per_class_metrics(
        self,
        combination: ExperimentCombination,
        data: Any,
    ) -> Path | None:
        return self._save_metric_table(
            combination,
            "per_class_metrics",
            self.combination_paths(combination).per_class_metrics,
            data,
        )

    def save_class_distribution(
        self,
        combination: ExperimentCombination,
        data: Any,
    ) -> Path | None:
        return self._save_metric_table(
            combination,
            "class_distribution",
            self.combination_paths(combination).class_distribution,
            data,
        )

    def save_execution_metrics(
        self,
        combination: ExperimentCombination,
        data: Any,
    ) -> Path | None:
        return self._save_metric_table(
            combination,
            "execution_metrics",
            self.combination_paths(combination).execution_metrics,
            data,
        )

    def save_confusion_matrix(
        self,
        combination: ExperimentCombination,
        data: Any,
        *,
        labels: Sequence[str] | None = None,
    ) -> Path | None:
        if not self._enabled("save_metrics"):
            return None
        frame = self._confusion_frame(data, labels)
        return self._save_table(
            combination,
            "confusion_matrix",
            self.combination_paths(combination).confusion_matrix,
            frame,
        )

    def save_aggregates(
        self,
        combination: ExperimentCombination,
        data: Any,
    ) -> Path | None:
        if not self._enabled("save_aggregates"):
            return None
        return self._save_table(
            combination,
            "aggregates",
            self.combination_paths(combination).aggregates,
            data,
        )

    def save_metadata(
        self,
        combination: ExperimentCombination,
        data: Mapping[str, Any] | None = None,
    ) -> Path | None:
        if not self._enabled("save_metadata"):
            return None

        self._ensure_prepared()
        payload: dict[str, Any] = {
            "run_id": self.config.run_id,
            "environment": self.config.environment,
            "combination_id": combination.combination_id,
            "combination_index": combination.index,
            "model_key": combination.model_key,
            "dataset_key": combination.dataset_key,
        }
        if data:
            payload.update(_serializable(dict(data)))

        path = self.combination_paths(combination).metadata
        if self.write_enabled:
            self._write_json(path, payload)
            self._register_file(combination, "metadata", path)
        return path

    def save_combination_results(
        self,
        combination: ExperimentCombination,
        *,
        predictions: Any | None = None,
        classification_metrics: Any | None = None,
        per_class_metrics: Any | None = None,
        confusion_matrix: Any | None = None,
        class_distribution: Any | None = None,
        execution_metrics: Any | None = None,
        aggregates: Any | None = None,
        metadata: Mapping[str, Any] | None = None,
        confusion_labels: Sequence[str] | None = None,
    ) -> dict[str, str]:
        """Salva todos os resultados disponíveis da combinação."""

        outputs: dict[str, str] = {}
        calls = [
            ("predictions", predictions, self.save_predictions),
            (
                "classification_metrics",
                classification_metrics,
                self.save_classification_metrics,
            ),
            ("per_class_metrics", per_class_metrics, self.save_per_class_metrics),
            ("class_distribution", class_distribution, self.save_class_distribution),
            ("execution_metrics", execution_metrics, self.save_execution_metrics),
            ("aggregates", aggregates, self.save_aggregates),
            ("metadata", metadata, self.save_metadata),
        ]

        for name, value, writer in calls:
            if value is None:
                continue
            path = writer(combination, value)
            if path is not None:
                outputs[name] = str(path)

        if confusion_matrix is not None:
            path = self.save_confusion_matrix(
                combination,
                confusion_matrix,
                labels=confusion_labels,
            )
            if path is not None:
                outputs["confusion_matrix"] = str(path)

        return outputs

    def save_temporal_index(
        self,
        combination: ExperimentCombination,
        artifacts: TemporalIndexArtifacts,
    ) -> dict[str, str]:
        """Salva os artefatos do ITI de uma combinação."""

        if not self.write_enabled:
            return {}

        paths = self.index_paths(combination)
        outputs: dict[str, str] = {}
        mapping = {
            "news_impact": (paths.news_impact, artifacts.news_impact),
            "iti_daily": (paths.iti_daily, artifacts.iti_daily),
            "iti_sector_daily": (
                paths.iti_sector_daily,
                artifacts.iti_sector_daily,
            ),
            "iti_market_daily": (
                paths.iti_market_daily,
                artifacts.iti_market_daily,
            ),
        }

        for name, (path, frame) in mapping.items():
            self._write_csv(path, frame)
            outputs[name] = str(path)
            self._register_file(combination, name, path)

        for frequency, frame in artifacts.resampled.items():
            filename = RESAMPLE_OUTPUT_NAMES[frequency]
            path = paths.root / filename
            self._write_csv(path, frame)
            outputs[filename.removesuffix(".csv")] = str(path)
            self._register_file(combination, filename, path)

        return outputs

    def save_uncertainty_merge(
        self,
        result: UncertaintyMergeResult,
    ) -> dict[str, str]:
        """Salva séries de incerteza consolidadas entre modelos."""

        if not self.write_enabled:
            return {}

        root = self.paths.merged_indices_root(result.dataset_key)
        disagreement_path = root / "disagreement_by_news.csv"
        uncertainty_path = root / "iti_uncertainty_daily.csv"

        self._write_csv(disagreement_path, result.disagreement_daily)
        self._write_csv(uncertainty_path, result.iti_uncertainty_daily)

        return {
            "disagreement_by_news": str(disagreement_path),
            "iti_uncertainty_daily": str(uncertainty_path),
        }

    # ================================================================
    # RESUMO DO EXPERIMENTO
    # ================================================================

    def build_summary(self) -> dict[str, Any]:
        records = sorted(
            self._records.values(),
            key=lambda record: record.index,
        )
        statuses = ("pending", "running", "success", "failed", "skipped")
        counts = {
            status: sum(record.status == status for record in records)
            for status in statuses
        }

        return {
            "schema_version": self.config.schema_version,
            "run_id": self.config.run_id,
            "experiment_name": self.config.experiment.get("name"),
            "description": self.config.experiment.get("description"),
            "environment": self.config.environment,
            "dry_run": self.config.dry_run,
            "status": self._experiment_status(counts),
            "started_at": self._started_at,
            "finished_at": self._finished_at,
            "selected_models": list(self.config.model_keys),
            "selected_datasets": list(self.config.dataset_keys),
            "skipped_combinations": [
                skipped.to_dict()
                for skipped in self.config.skipped_combinations
            ],
            "total_combinations": len(records),
            "combination_counts": counts,
            "combinations": [record.to_dict() for record in records],
            "output_directory": str(self.paths.run_root),
            "resolved_config_file": (
                str(self.resolved_config_path)
                if self._enabled("save_resolved_config")
                else None
            ),
            "extra": _serializable(self._summary_extra),
        }

    def save_summary(self) -> Path | None:
        self._ensure_prepared()
        if self.write_enabled:
            self._write_json(self.summary_path, self.build_summary())
        return self.summary_path

    def finalize(
        self,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Finaliza e devolve o resumo do experimento."""

        with self._lock:
            self._ensure_prepared()
            if extra:
                self._summary_extra.update(_serializable(dict(extra)))
            self._finished_at = self._now()
            self._finalized = True
            summary = self.build_summary()
            self._save_summary_if_enabled()
            return summary

    # ================================================================
    # IMPLEMENTAÇÃO INTERNA
    # ================================================================

    def _validate_options(self) -> None:
        boolean_keys = (
            "save_predictions",
            "save_metrics",
            "save_aggregates",
            "save_metadata",
            "save_experiment_summary",
            "save_resolved_config",
        )
        for key in boolean_keys:
            if not isinstance(self.options.get(key), bool):
                raise ResultsError(f"outputs.{key} precisa ser true ou false.")

        if self.options.get("tabular_format") != "csv":
            raise ResultsError("Somente outputs.tabular_format=csv é suportado.")

        delimiter = self.options.get("delimiter", ",")
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise ResultsError("outputs.delimiter precisa ter um caractere.")

        precision = self.options.get("float_precision", 8)
        if (
            isinstance(precision, bool)
            or not isinstance(precision, int)
            or not 0 <= precision <= 15
        ):
            raise ResultsError(
                "outputs.float_precision precisa ser inteiro entre 0 e 15."
            )

    def _enabled(self, key: str) -> bool:
        return bool(self.options.get(key, False))

    def _ensure_prepared(self) -> None:
        if not self._prepared:
            self.prepare()

    def _validate_combination(
        self,
        combination: ExperimentCombination,
    ) -> None:
        expected = next(
            (
                item
                for item in self.config.combinations
                if item.combination_id == combination.combination_id
            ),
            None,
        )
        if expected != combination:
            raise ResultsError(
                "A combinação não pertence à configuração resolvida: "
                f"{combination.combination_id}"
            )

    def _record(
        self,
        combination: ExperimentCombination,
    ) -> CombinationRecord:
        self._validate_combination(combination)
        return self._records[combination.combination_id]

    def _save_metric_table(
        self,
        combination: ExperimentCombination,
        name: str,
        path: Path,
        data: Any,
    ) -> Path | None:
        if not self._enabled("save_metrics"):
            return None
        return self._save_table(combination, name, path, data)

    def _save_table(
        self,
        combination: ExperimentCombination,
        name: str,
        path: Path,
        data: Any,
    ) -> Path:
        self._ensure_prepared()
        self._validate_combination(combination)
        frame = _dataframe(data)
        if self.write_enabled:
            self._write_csv(path, frame)
            self._register_file(combination, name, path)
        return path

    def _confusion_frame(
        self,
        data: Any,
        labels: Sequence[str] | None,
    ) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            frame = data.copy()
            if "true_label" not in frame.columns:
                frame = frame.reset_index().rename(
                    columns={frame.index.name or "index": "true_label"}
                )
            return frame

        matrix = np.asarray(data)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ResultsError("A matriz de confusão precisa ser quadrada.")

        names = list(
            labels
            or self.config.classification_metrics.get("labels", [])
        )
        if not names:
            names = [str(index) for index in range(matrix.shape[0])]
        if len(names) != matrix.shape[0]:
            raise ResultsError(
                "A quantidade de labels difere do tamanho da matriz."
            )

        frame = pd.DataFrame(matrix, columns=pd.Index(names))
        true_labels = pd.Series(
            names,
            index=frame.index,
            dtype="string",
        )
        frame.insert(0, "true_label", true_labels)
        return frame

    def _register_file(
        self,
        combination: ExperimentCombination,
        name: str,
        path: Path,
    ) -> None:
        try:
            relative = str(
                path.resolve().relative_to(self.paths.run_root.resolve())
            )
        except ValueError as error:
            raise ResultsError(
                f"Arquivo fora da raiz da execução: {path}"
            ) from error

        files = self._files.setdefault(combination.combination_id, {})
        files[name] = relative
        self._records[combination.combination_id].output_files = dict(files)
        self._save_summary_if_enabled()

    def _save_summary_if_enabled(self) -> None:
        if (
            self.write_enabled
            and self._prepared
            and self._enabled("save_experiment_summary")
        ):
            self._write_json(self.summary_path, self.build_summary())

    def _experiment_status(self, counts: Mapping[str, int]) -> str:
        if not self._finalized:
            return "running" if counts["running"] or counts["success"] else "pending"
        if counts["failed"] and counts["success"]:
            return "partial_failure"
        if counts["failed"]:
            return "failed"
        if counts["pending"] or counts["running"]:
            return "incomplete"
        return "success"

    def _duration(
        self,
        started_at: str,
        finished_at: str,
        explicit: float | None,
    ) -> float:
        if explicit is not None:
            value = float(explicit)
            if not math.isfinite(value) or value < 0:
                raise ResultsError("duration_seconds precisa ser não negativo.")
            return value
        return max(
            0.0,
            (
                datetime.fromisoformat(finished_at)
                - datetime.fromisoformat(started_at)
            ).total_seconds(),
        )

    def _timezone(self) -> ZoneInfo:
        name = str(self.config.experiment.get("timezone", "UTC"))
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError as error:
            raise ResultsError(f"Fuso horário inválido: {name}") from error

    def _now(self) -> str:
        return datetime.now(self._timezone()).isoformat()

    def _write_csv(self, path: Path, frame: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = _temporary_file(path)
        try:
            frame.to_csv(
                temporary,
                index=False,
                encoding=str(self.options.get("encoding", "utf-8")),
                sep=str(self.options.get("delimiter", ",")),
                float_format=(
                    f"%.{int(self.options.get('float_precision', 8))}f"
                ),
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )
            os.replace(temporary, path)
        except Exception as error:
            _unlink(temporary)
            raise ResultsError(f"Erro ao salvar {path}: {error}") from error

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = _temporary_file(path)
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(
                    _serializable(data),
                    file,
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
                file.write("\n")
            os.replace(temporary, path)
        except Exception as error:
            _unlink(temporary)
            raise ResultsError(f"Erro ao salvar {path}: {error}") from error

    def _write_yaml(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = _temporary_file(path)
        try:
            with temporary.open("w", encoding="utf-8") as file:
                yaml.safe_dump(
                    _serializable(data),
                    file,
                    allow_unicode=True,
                    sort_keys=False,
                )
            os.replace(temporary, path)
        except Exception as error:
            _unlink(temporary)
            raise ResultsError(f"Erro ao salvar {path}: {error}") from error


def _dataframe(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    elif isinstance(data, pd.Series):
        frame = data.to_frame().T
    elif not isinstance(data, type) and is_dataclass(data):
        frame = pd.DataFrame([asdict(cast(Any, data))])
    elif isinstance(data, Mapping):
        frame = pd.DataFrame([dict(data)])
    elif isinstance(data, np.ndarray):
        if data.ndim not in {1, 2}:
            raise ResultsError("Arrays tabulares precisam ter 1 ou 2 dimensões.")
        frame = pd.DataFrame(data if data.ndim == 2 else {"value": data})
    elif isinstance(data, Sequence) and not isinstance(
        data,
        (str, bytes, bytearray),
    ):
        frame = pd.DataFrame(list(data))
    else:
        raise ResultsError(
            "Resultado tabular inválido. Use DataFrame, Series, mapping, "
            "dataclass, array ou sequência."
        )

    for column in frame.select_dtypes(include=["object"]).columns:
        frame[column] = frame[column].map(_csv_cell)
    return frame


def _csv_cell(value: Any) -> Any:
    if _missing(value):
        return None
    if (
        isinstance(value, (Mapping, list, tuple, set))
        or (not isinstance(value, type) and is_dataclass(value))
    ):
        return json.dumps(
            _serializable(value),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _serializable(value: Any) -> Any:
    if value is None or _missing(value):
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _serializable(value.item())
    if isinstance(value, np.ndarray):
        return _serializable(value.tolist())
    if not isinstance(value, type) and is_dataclass(value):
        return _serializable(asdict(cast(Any, value)))
    if isinstance(value, Mapping):
        return {
            str(key): _serializable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_serializable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _missing(value: object) -> bool:
    """Verifica valores escalares ausentes sem usar ``pandas.isna``.

    Isso evita incompatibilidades com as sobrecargas estritas do
    Pylance 2026.2.1 quando o valor possui tipo ``Any``.
    """

    if value is None or value is pd.NA or value is pd.NaT:
        return True

    if isinstance(value, type):
        return False

    if isinstance(value, float):
        return math.isnan(value)

    if isinstance(value, np.floating):
        return bool(np.isnan(value))

    if isinstance(value, np.datetime64):
        return bool(np.isnat(value))

    if isinstance(value, np.timedelta64):
        return bool(np.isnat(value))

    return False


def _non_negative_or_none(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ResultsError(f"{name} precisa ser inteiro.")
    normalized = int(value)
    if normalized < 0:
        raise ResultsError(f"{name} não pode ser negativo.")
    return normalized


def _temporary_file(destination: Path) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    os.close(descriptor)
    return Path(name)


def _unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


__all__ = [
    "CombinationOutputPaths",
    "CombinationRecord",
    "ResultsError",
    "ResultsManager",
]