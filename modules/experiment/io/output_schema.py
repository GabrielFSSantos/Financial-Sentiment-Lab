"""Padronização e validação das previsões produzidas pelos modelos.

Este módulo combina o dataset padronizado, previsões ``ModelPrediction`` dos
adaptadores e metadados do experimento em um DataFrame único.

Responsabilidades de outros módulos:

- ``modules.experiment.config.loader`` — YAML;
- ``modules.datasets.loader`` — datasets;
- ``modules.models.registry`` — modelos;
- ``modules.experiment.stages.metrics`` — métricas;
- ``modules.experiment.io.results`` — gravação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence, cast

import numpy as np
import pandas as pd

from modules.experiment.common import (
    CANONICAL_LABELS,
    column_series,
    numeric_series,
)
from modules.experiment.config.loader import (
    ExperimentCombination,
    ModelConfiguration,
    ResolvedConfiguration,
)
from modules.datasets.loader import LoadedDataset
from modules.models.base import ModelPrediction
from modules.models.sentiment import (
    calculate_continuous_sentiment,
    normalize_sentiment_label,
)

from .prediction_normalization import (
    PredictionFormatError,
    PredictionValidationError,
    build_prediction_dataframe,
    coerce_model_predictions,
    normalize_model_predictions,
)


PROBABILITY_COLUMNS: tuple[str, ...] = (
    "prob_negative",
    "prob_neutral",
    "prob_positive",
)

PREDICTION_COLUMNS: tuple[str, ...] = (
    "prediction_index",
    "predicted_label",
    "confidence",
    "prob_positive",
    "prob_negative",
    "prob_neutral",
    "continuous_sentiment",
    "probability_sum",
    "processing_time_ms",
    "prediction_metadata",
)

IDENTIFICATION_COLUMNS: tuple[str, ...] = (
    "run_id",
    "environment",
    "combination_id",
    "combination_index",
    "model_key",
    "model_name",
    "model_display_name",
    "dataset_key",
    "dataset_name",
    "dataset_display_name",
)

DATASET_CORE_COLUMNS: tuple[str, ...] = (
    "news_id",
    "text",
    "date",
    "company",
    "sector",
    "ticker",
    "language",
    "source",
    "url",
    "title",
)

MODEL_EXECUTION_COLUMNS: tuple[str, ...] = (
    "batch_size",
    "max_length",
    "device_used",
)

OUTPUT_COLUMNS: tuple[str, ...] = (
    *IDENTIFICATION_COLUMNS,
    *DATASET_CORE_COLUMNS,
    *PREDICTION_COLUMNS,
    *MODEL_EXECUTION_COLUMNS,
)


class OutputSchemaError(RuntimeError):
    """Erro base do schema de saída."""


class PredictionCountError(OutputSchemaError, ValueError):
    """Quantidade de previsões incompatível com o dataset."""


class OutputDataFrameValidationError(OutputSchemaError, ValueError):
    """DataFrame final fora do schema esperado."""


@dataclass(frozen=True)
class PredictionSchemaStatistics:
    """Estatísticas resumidas das previsões padronizadas."""

    row_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    mean_confidence: float
    mean_continuous_sentiment: float
    minimum_continuous_sentiment: float
    maximum_continuous_sentiment: float
    probability_rows_normalized: int
    prediction_metadata_rows: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "mean_confidence": self.mean_confidence,
            "mean_continuous_sentiment": self.mean_continuous_sentiment,
            "minimum_continuous_sentiment": self.minimum_continuous_sentiment,
            "maximum_continuous_sentiment": self.maximum_continuous_sentiment,
            "probability_rows_normalized": self.probability_rows_normalized,
            "prediction_metadata_rows": self.prediction_metadata_rows,
        }


@dataclass
class StandardizedPredictions:
    """Resultado completo produzido pelo ``OutputSchemaBuilder``."""

    dataframe: pd.DataFrame
    statistics: PredictionSchemaStatistics
    combination: ExperimentCombination
    model_configuration: ModelConfiguration
    dataset: LoadedDataset
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def row_count(self) -> int:
        return len(self.dataframe)

    @property
    def has_true_labels(self) -> bool:
        return "label" in self.dataframe.columns

    def metadata(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "has_true_labels": self.has_true_labels,
            "statistics": self.statistics.to_dict(),
            "warnings": list(self.warnings),
            "combination": self.combination.to_dict(),
            "model_key": self.model_configuration.key,
            "dataset_key": self.dataset.key,
        }


class OutputSchemaBuilder:
    """Monta o schema oficial a partir de ``ModelPrediction`` dos adaptadores."""

    def __init__(
        self,
        *,
        probability_tolerance: float = 1e-6,
        probability_sum_tolerance: float = 1e-4,
        validate_predicted_label: bool = True,
        preserve_prediction_metadata: bool = True,
        copy_dataset: bool = True,
    ) -> None:
        if probability_tolerance < 0:
            raise ValueError("probability_tolerance não pode ser negativo.")
        if probability_sum_tolerance < 0:
            raise ValueError("probability_sum_tolerance não pode ser negativo.")

        self.probability_tolerance = float(probability_tolerance)
        self.probability_sum_tolerance = float(probability_sum_tolerance)
        self.validate_predicted_label = bool(validate_predicted_label)
        self.preserve_prediction_metadata = bool(preserve_prediction_metadata)
        self.copy_dataset = bool(copy_dataset)

    def build(
        self,
        *,
        run_id: str,
        environment: str,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        loaded_dataset: LoadedDataset,
        predictions: Sequence[ModelPrediction],
        device_used: str | None = None,
    ) -> StandardizedPredictions:
        """Monta e valida o DataFrame final de uma combinação."""

        self._validate_context(
            run_id=run_id,
            environment=environment,
            combination=combination,
            model_configuration=model_configuration,
            loaded_dataset=loaded_dataset,
        )

        prediction_tuple = coerce_model_predictions(predictions)
        expected_count = len(loaded_dataset.dataframe)

        if len(prediction_tuple) != expected_count:
            raise PredictionCountError(
                f"A combinação {combination.combination_id!r} recebeu "
                f"{len(prediction_tuple)} previsão(ões), mas o dataset "
                f"possui {expected_count} linha(s) válida(s)."
            )

        normalized_predictions = normalize_model_predictions(
            prediction_tuple,
            preserve_metadata=self.preserve_prediction_metadata,
        )

        normalized_probability_rows = sum(
            1
            for item in normalized_predictions
            if item.probability_was_normalized
        )
        metadata_rows = sum(
            1 for item in normalized_predictions if item.metadata
        )
        warnings: list[str] = []

        if normalized_probability_rows:
            warnings.append(
                f"{normalized_probability_rows} linha(s) tiveram a soma "
                "das probabilidades normalizada para 1."
            )

        prediction_frame = build_prediction_dataframe(normalized_predictions)
        output = self._combine_frames(
            run_id=run_id,
            environment=environment,
            combination=combination,
            model_configuration=model_configuration,
            loaded_dataset=loaded_dataset,
            prediction_frame=prediction_frame,
            device_used=device_used,
        )

        self.validate_output_dataframe(
            output,
            expected_row_count=expected_count,
            expected_run_id=run_id,
            expected_environment=environment,
            expected_combination=combination,
            expected_model=model_configuration,
            expected_dataset=loaded_dataset,
        )

        statistics = self._build_statistics(
            output,
            probability_rows_normalized=normalized_probability_rows,
            prediction_metadata_rows=metadata_rows,
        )

        return StandardizedPredictions(
            dataframe=output,
            statistics=statistics,
            combination=combination,
            model_configuration=model_configuration,
            dataset=loaded_dataset,
            warnings=tuple(warnings),
        )

    def build_from_resolved_configuration(
        self,
        *,
        configuration: ResolvedConfiguration,
        combination: ExperimentCombination,
        loaded_dataset: LoadedDataset,
        predictions: Sequence[ModelPrediction],
        device_used: str | None = None,
    ) -> StandardizedPredictions:
        """Atalho que obtém o modelo e o contexto da configuração resolvida."""

        model_configuration = configuration.get_model(combination.model_key)

        return self.build(
            run_id=configuration.run_id,
            environment=configuration.environment,
            combination=combination,
            model_configuration=model_configuration,
            loaded_dataset=loaded_dataset,
            predictions=predictions,
            device_used=device_used,
        )
    def validate_output_dataframe(
        self,
        dataframe: pd.DataFrame,
        *,
        expected_row_count: int | None = None,
        expected_run_id: str | None = None,
        expected_environment: str | None = None,
        expected_combination: ExperimentCombination | None = None,
        expected_model: ModelConfiguration | None = None,
        expected_dataset: LoadedDataset | None = None,
    ) -> None:
        """Valida um DataFrame já montado no schema oficial."""

        if not isinstance(dataframe, pd.DataFrame):
            raise OutputDataFrameValidationError(
                "A saída precisa ser um pandas.DataFrame."
            )

        duplicated_columns = dataframe.columns[
            dataframe.columns.duplicated()
        ].tolist()
        if duplicated_columns:
            raise OutputDataFrameValidationError(
                f"A saída possui colunas duplicadas: "
                f"{duplicated_columns}."
            )

        missing_columns = [
            column
            for column in OUTPUT_COLUMNS
            if column not in dataframe.columns
        ]
        if missing_columns:
            raise OutputDataFrameValidationError(
                f"A saída não possui colunas obrigatórias: "
                f"{missing_columns}."
            )

        if expected_row_count is not None:
            if len(dataframe) != expected_row_count:
                raise OutputDataFrameValidationError(
                    f"A saída possui {len(dataframe)} linha(s), mas "
                    f"eram esperadas {expected_row_count}."
                )

        if dataframe.empty:
            return

        self._validate_constant_column(
            dataframe,
            "run_id",
            expected_run_id,
        )
        self._validate_constant_column(
            dataframe,
            "environment",
            expected_environment,
        )

        if expected_combination is not None:
            self._validate_constant_column(
                dataframe,
                "combination_id",
                expected_combination.combination_id,
            )
            self._validate_constant_column(
                dataframe,
                "combination_index",
                expected_combination.index,
            )

        if expected_model is not None:
            self._validate_constant_column(
                dataframe,
                "model_key",
                expected_model.key,
            )
            self._validate_constant_column(
                dataframe,
                "model_name",
                expected_model.model_name,
            )

        if expected_dataset is not None:
            self._validate_constant_column(
                dataframe,
                "dataset_key",
                expected_dataset.key,
            )
            self._validate_constant_column(
                dataframe,
                "dataset_name",
                expected_dataset.dataset_name,
            )

        labels = set(
            dataframe["predicted_label"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
        )
        invalid_labels = labels - set(CANONICAL_LABELS)
        if invalid_labels:
            raise OutputDataFrameValidationError(
                f"A saída possui predicted_label inválido: "
                f"{sorted(invalid_labels)}."
            )

        probability_frame = dataframe.loc[
            :,
            list(PROBABILITY_COLUMNS),
        ].apply(pd.to_numeric, errors="coerce")
        probability_values = cast(
            pd.DataFrame,
            probability_frame,
        )
        probability_array = probability_values.to_numpy(
            dtype=np.float64
        )

        if not np.isfinite(probability_array).all():
            raise OutputDataFrameValidationError(
                "A saída possui probabilidades ausentes, não numéricas "
                "ou não finitas."
            )

        minimum = float(np.min(probability_array))
        maximum = float(np.max(probability_array))
        tolerance = self.probability_tolerance

        if minimum < -tolerance or maximum > 1.0 + tolerance:
            raise OutputDataFrameValidationError(
                "As probabilidades precisam estar no intervalo [0, 1]. "
                f"Intervalo encontrado: [{minimum}, {maximum}]."
            )

        probability_sums = probability_array.sum(axis=1)
        deviations = np.abs(probability_sums - 1.0)

        if bool(
            (
                deviations
                > self.probability_sum_tolerance
            ).any()
        ):
            worst = float(np.max(deviations))
            raise OutputDataFrameValidationError(
                "A soma das probabilidades precisa ser igual a 1. "
                f"Maior desvio encontrado: {worst}."
            )

        negative_index = PROBABILITY_COLUMNS.index(
            "prob_negative"
        )
        positive_index = PROBABILITY_COLUMNS.index(
            "prob_positive"
        )
        expected_continuous = (
            probability_array[:, positive_index]
            - probability_array[:, negative_index]
        )

        actual_continuous_series = numeric_series(
            column_series(
                dataframe,
                "continuous_sentiment",
            ),
            errors="coerce",
        )
        actual_continuous = (
            actual_continuous_series.to_numpy(
                dtype=np.float64
            )
        )

        if not np.isfinite(actual_continuous).all():
            raise OutputDataFrameValidationError(
                "continuous_sentiment possui valores inválidos."
            )

        if not np.allclose(
            actual_continuous,
            expected_continuous,
            atol=self.probability_tolerance,
            rtol=0.0,
        ):
            raise OutputDataFrameValidationError(
                "continuous_sentiment precisa ser calculado por "
                "prob_positive - prob_negative."
            )

        expected_confidence = probability_array.max(axis=1)
        actual_confidence_series = numeric_series(
            column_series(dataframe, "confidence"),
            errors="coerce",
        )
        actual_confidence = (
            actual_confidence_series.to_numpy(
                dtype=np.float64
            )
        )

        if not np.isfinite(actual_confidence).all():
            raise OutputDataFrameValidationError(
                "confidence possui valores inválidos."
            )

        if not np.allclose(
            actual_confidence,
            expected_confidence,
            atol=self.probability_tolerance,
            rtol=0.0,
        ):
            raise OutputDataFrameValidationError(
                "confidence precisa ser a maior probabilidade da linha."
            )

        duplicate_key = dataframe.duplicated(
            subset=[
                "run_id",
                "model_key",
                "dataset_key",
                "news_id",
            ],
            keep=False,
        )
        if bool(duplicate_key.any()):
            duplicate_frame = dataframe.loc[duplicate_key]
            duplicate_ids = (
                column_series(
                    cast(pd.DataFrame, duplicate_frame),
                    "news_id",
                )
                .astype(str)
                .drop_duplicates()
                .tolist()
            )
            raise OutputDataFrameValidationError(
                "A saída possui notícias duplicadas na mesma combinação: "
                f"{duplicate_ids[:20]}."
            )

        expected_indices = np.arange(
            len(dataframe),
            dtype=np.float64,
        )
        actual_indices = numeric_series(
            column_series(dataframe, "prediction_index"),
            errors="coerce",
        ).to_numpy(dtype=np.float64)

        if not np.array_equal(
            actual_indices,
            expected_indices.astype(float),
        ):
            raise OutputDataFrameValidationError(
                "prediction_index precisa ser sequencial e começar em 0."
            )

    def _validate_context(
        self,
        *,
        run_id: str,
        environment: str,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        loaded_dataset: LoadedDataset,
    ) -> None:
        if not str(run_id).strip():
            raise OutputSchemaError(
                "run_id não pode ser vazio."
            )

        normalized_environment = str(environment).strip().lower()
        if normalized_environment not in {"local", "sdumont"}:
            raise OutputSchemaError(
                "environment precisa ser 'local' ou 'sdumont'."
            )

        if combination.model_key != model_configuration.key:
            raise OutputSchemaError(
                f"A combinação usa o modelo "
                f"{combination.model_key!r}, mas foi recebida a "
                f"configuração {model_configuration.key!r}."
            )

        if combination.dataset_key != loaded_dataset.key:
            raise OutputSchemaError(
                f"A combinação usa o dataset "
                f"{combination.dataset_key!r}, mas foi recebido "
                f"{loaded_dataset.key!r}."
            )

        dataframe = loaded_dataset.dataframe
        required_dataset_columns = {
            "dataset_key",
            "dataset_name",
            *DATASET_CORE_COLUMNS,
        }
        missing = sorted(
            required_dataset_columns - set(dataframe.columns)
        )
        if missing:
            raise OutputSchemaError(
                f"O LoadedDataset não possui colunas necessárias: "
                f"{missing}."
            )

    def _combine_frames(
        self,
        *,
        run_id: str,
        environment: str,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        loaded_dataset: LoadedDataset,
        prediction_frame: pd.DataFrame,
        device_used: str | None,
    ) -> pd.DataFrame:
        dataset_frame = loaded_dataset.dataframe.copy(
            deep=self.copy_dataset
        )
        dataset_frame.reset_index(drop=True, inplace=True)
        prediction_frame = prediction_frame.reset_index(
            drop=True
        )

        output = pd.concat(
            [dataset_frame, prediction_frame],
            axis=1,
        )

        # As colunas dataset_key e dataset_name já vêm do loader.
        # Elas são validadas antes da inclusão das demais identificações.
        output.insert(0, "run_id", str(run_id).strip())
        output.insert(
            1,
            "environment",
            str(environment).strip().lower(),
        )
        output.insert(
            2,
            "combination_id",
            combination.combination_id,
        )
        output.insert(
            3,
            "combination_index",
            combination.index,
        )
        output.insert(
            4,
            "model_key",
            model_configuration.key,
        )
        output.insert(
            5,
            "model_name",
            model_configuration.model_name,
        )
        output.insert(
            6,
            "model_display_name",
            model_configuration.display_name,
        )

        dataset_key_position = list(output.columns).index(
            "dataset_key"
        )
        output.insert(
            dataset_key_position + 2,
            "dataset_display_name",
            loaded_dataset.display_name,
        )

        parameters = model_configuration.parameters
        output["batch_size"] = int(
            parameters["batch_size"]
        )
        output["max_length"] = int(
            parameters["max_length"]
        )
        output["device_used"] = (
            str(device_used).strip()
            if device_used is not None
            and str(device_used).strip()
            else str(parameters["device"]).strip().lower()
        )

        output = self._order_output_columns(output)
        output.reset_index(drop=True, inplace=True)
        return output

    @staticmethod
    def _order_output_columns(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        preferred = [
            column
            for column in OUTPUT_COLUMNS
            if column in dataframe.columns
        ]
        extras = [
            column
            for column in dataframe.columns
            if column not in preferred
        ]
        return dataframe.reindex(
            columns=preferred + extras
        ).copy()

    @staticmethod
    def _build_statistics(
        dataframe: pd.DataFrame,
        *,
        probability_rows_normalized: int,
        prediction_metadata_rows: int,
    ) -> PredictionSchemaStatistics:
        counts = column_series(
            dataframe,
            "predicted_label",
        ).value_counts()

        sentiment = numeric_series(
            column_series(
                dataframe,
                "continuous_sentiment",
            ),
            errors="raise",
        ).to_numpy(dtype=np.float64)
        confidence = numeric_series(
            column_series(dataframe, "confidence"),
            errors="raise",
        ).to_numpy(dtype=np.float64)

        return PredictionSchemaStatistics(
            row_count=len(dataframe),
            positive_count=_series_count(
                counts,
                "POSITIVE",
            ),
            negative_count=_series_count(
                counts,
                "NEGATIVE",
            ),
            neutral_count=_series_count(
                counts,
                "NEUTRAL",
            ),
            mean_confidence=float(
                np.mean(confidence)
            ),
            mean_continuous_sentiment=float(
                np.mean(sentiment)
            ),
            minimum_continuous_sentiment=float(
                np.min(sentiment)
            ),
            maximum_continuous_sentiment=float(
                np.max(sentiment)
            ),
            probability_rows_normalized=int(
                probability_rows_normalized
            ),
            prediction_metadata_rows=int(
                prediction_metadata_rows
            ),
        )

    @staticmethod
    def _validate_constant_column(
        dataframe: pd.DataFrame,
        column: str,
        expected: Any | None,
    ) -> None:
        if expected is None:
            return

        values = dataframe[column].drop_duplicates().tolist()
        if len(values) != 1 or values[0] != expected:
            raise OutputDataFrameValidationError(
                f"A coluna {column!r} deveria conter somente "
                f"{expected!r}, mas contém {values[:20]}."
            )


def _series_count(
    counts: pd.Series,
    label: str,
) -> int:
    value = counts.get(label, 0)
    return int(0 if value is None else value)


__all__ = [
    "CANONICAL_LABELS",
    "DATASET_CORE_COLUMNS",
    "IDENTIFICATION_COLUMNS",
    "MODEL_EXECUTION_COLUMNS",
    "OUTPUT_COLUMNS",
    "OutputDataFrameValidationError",
    "OutputSchemaBuilder",
    "OutputSchemaError",
    "PREDICTION_COLUMNS",
    "PROBABILITY_COLUMNS",
    "PredictionCountError",
    "PredictionFormatError",
    "PredictionSchemaStatistics",
    "PredictionValidationError",
    "StandardizedPredictions",
    "calculate_continuous_sentiment",
    "normalize_sentiment_label",
]
