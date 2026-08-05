"""Padronização e validação das previsões produzidas pelos modelos.

Este módulo combina:

- o dataset já padronizado por ``pipeline.dataset_loader``;
- as previsões retornadas por um adaptador de modelo;
- os identificadores do experimento, modelo e dataset.

O resultado é um DataFrame único e comparável entre todos os modelos.

Este módulo não:

- carrega arquivos YAML;
- carrega datasets;
- cria modelos;
- calcula métricas;
- salva arquivos.

Essas responsabilidades pertencem, respectivamente, a:

- ``pipeline.configuration``;
- ``pipeline.dataset_loader``;
- ``pipeline.registry``;
- ``pipeline.metrics``;
- ``pipeline.results``.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence, cast

import numpy as np
import pandas as pd

from pipeline.common import (
    CANONICAL_LABELS,
    column_series,
    is_missing_scalar,
    numeric_series,
    to_serializable,
)
from pipeline.configuration import (
    ExperimentCombination,
    ModelConfiguration,
    ResolvedConfiguration,
)
from pipeline.dataset_loader import LoadedDataset
from models.sentiment import (
    LABEL_ALIASES,
    calculate_continuous_sentiment,
    normalize_sentiment_label,
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
    "date",
    "company",
    "sector",
    "ticker",
    "title",
    "text",
    "true_label",
    "source",
    "url",
    "source_row_number",
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

DIRECT_PROBABILITY_ALIASES: dict[str, tuple[str, ...]] = {
    "POSITIVE": (
        "prob_positive",
        "positive_probability",
        "probability_positive",
        "positive_score",
        "score_positive",
    ),
    "NEGATIVE": (
        "prob_negative",
        "negative_probability",
        "probability_negative",
        "negative_score",
        "score_negative",
    ),
    "NEUTRAL": (
        "prob_neutral",
        "neutral_probability",
        "probability_neutral",
        "neutral_score",
        "score_neutral",
    ),
}

LABEL_FIELD_ALIASES: tuple[str, ...] = (
    "predicted_label",
    "label",
    "class_label",
    "prediction",
    "sentiment",
)

CONFIDENCE_FIELD_ALIASES: tuple[str, ...] = (
    "confidence",
    "score",
    "max_probability",
)

PROBABILITY_CONTAINER_ALIASES: tuple[str, ...] = (
    "probabilities",
    "scores",
    "class_probabilities",
    "label_scores",
)

PROCESSING_TIME_FIELD_ALIASES: tuple[str, ...] = (
    "processing_time_ms",
    "elapsed_time_ms",
    "inference_time_ms",
)

METADATA_FIELD_ALIASES: tuple[str, ...] = (
    "metadata",
    "extra",
    "details",
)

_SAFE_COLUMN_PATTERN = re.compile(r"[^A-Za-z0-9_]+")


class OutputSchemaError(RuntimeError):
    """Erro-base relacionado à padronização das previsões."""


class PredictionCountError(OutputSchemaError, ValueError):
    """A quantidade de previsões não corresponde ao dataset."""


class PredictionFormatError(OutputSchemaError, TypeError):
    """Uma previsão possui estrutura incompatível."""


class PredictionValidationError(OutputSchemaError, ValueError):
    """Uma previsão possui valores inválidos."""


class OutputDataFrameValidationError(OutputSchemaError, ValueError):
    """O DataFrame final não atende ao schema esperado."""


@dataclass(frozen=True)
class PredictionSchemaStatistics:
    """Resumo da padronização das previsões."""

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
        return asdict(self)


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
        return bool(self.dataframe["true_label"].notna().any())

    def metadata(self) -> dict[str, Any]:
        return {
            "run_id": (
                str(self.dataframe["run_id"].iloc[0])
                if not self.dataframe.empty
                else None
            ),
            "combination": self.combination.to_dict(),
            "model_key": self.model_configuration.key,
            "model_name": self.model_configuration.model_name,
            "dataset_key": self.dataset.key,
            "dataset_name": self.dataset.dataset_name,
            "row_count": self.row_count,
            "has_true_labels": self.has_true_labels,
            "statistics": self.statistics.to_dict(),
            "warnings": list(self.warnings),
            "columns": list(self.dataframe.columns),
        }


@dataclass(frozen=True)
class _NormalizedPrediction:
    predicted_label: str
    confidence: float
    prob_positive: float
    prob_negative: float
    prob_neutral: float
    continuous_sentiment: float
    probability_sum: float
    processing_time_ms: float | None
    metadata: dict[str, Any]
    probability_was_normalized: bool


class OutputSchemaBuilder:
    """Converte previsões heterogêneas para o schema oficial da pipeline."""

    def __init__(
        self,
        *,
        probability_tolerance: float = 1e-6,
        probability_sum_tolerance: float = 1e-4,
        normalize_probability_sum: bool = True,
        maximum_normalization_deviation: float = 1e-2,
        validate_predicted_label: bool = True,
        preserve_prediction_metadata: bool = True,
        copy_dataset: bool = True,
    ) -> None:
        if probability_tolerance < 0:
            raise ValueError(
                "probability_tolerance não pode ser negativo."
            )

        if probability_sum_tolerance < 0:
            raise ValueError(
                "probability_sum_tolerance não pode ser negativo."
            )

        if maximum_normalization_deviation < probability_sum_tolerance:
            raise ValueError(
                "maximum_normalization_deviation precisa ser maior ou "
                "igual a probability_sum_tolerance."
            )

        self.probability_tolerance = float(probability_tolerance)
        self.probability_sum_tolerance = float(
            probability_sum_tolerance
        )
        self.normalize_probability_sum = bool(
            normalize_probability_sum
        )
        self.maximum_normalization_deviation = float(
            maximum_normalization_deviation
        )
        self.validate_predicted_label = bool(
            validate_predicted_label
        )
        self.preserve_prediction_metadata = bool(
            preserve_prediction_metadata
        )
        self.copy_dataset = bool(copy_dataset)

    def build(
        self,
        *,
        run_id: str,
        environment: str,
        combination: ExperimentCombination,
        model_configuration: ModelConfiguration,
        loaded_dataset: LoadedDataset,
        predictions: Iterable[Any],
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

        prediction_list = list(predictions)
        expected_count = len(loaded_dataset.dataframe)

        if len(prediction_list) != expected_count:
            raise PredictionCountError(
                f"A combinação {combination.combination_id!r} recebeu "
                f"{len(prediction_list)} previsão(ões), mas o dataset "
                f"possui {expected_count} linha(s) válida(s)."
            )

        label_aliases = self._build_label_aliases(
            model_configuration
        )
        sequence_order = self._build_probability_sequence_order(
            model_configuration,
            label_aliases,
        )

        normalized_predictions: list[_NormalizedPrediction] = []
        normalized_probability_rows = 0
        metadata_rows = 0
        warnings: list[str] = []

        for index, prediction in enumerate(prediction_list):
            normalized = self._normalize_prediction(
                prediction=prediction,
                index=index,
                model_configuration=model_configuration,
                label_aliases=label_aliases,
                sequence_order=sequence_order,
            )
            normalized_predictions.append(normalized)

            if normalized.probability_was_normalized:
                normalized_probability_rows += 1

            if normalized.metadata:
                metadata_rows += 1

        if normalized_probability_rows:
            warnings.append(
                f"{normalized_probability_rows} linha(s) tiveram a soma "
                "das probabilidades normalizada para 1."
            )

        prediction_frame = self._prediction_frame(
            normalized_predictions
        )
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
        predictions: Iterable[Any],
        device_used: str | None = None,
    ) -> StandardizedPredictions:
        """Atalho que obtém o modelo e o contexto da configuração resolvida."""

        model_configuration = configuration.get_model(
            combination.model_key
        )

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

    def _normalize_prediction(
        self,
        *,
        prediction: Any,
        index: int,
        model_configuration: ModelConfiguration,
        label_aliases: Mapping[str, str],
        sequence_order: Sequence[str],
    ) -> _NormalizedPrediction:
        raw = self._prediction_to_mapping(
            prediction,
            index=index,
        )

        raw_label = self._first_present(
            raw,
            LABEL_FIELD_ALIASES,
        )
        probabilities = self._extract_probabilities(
            raw=raw,
            sequence_order=sequence_order,
            label_aliases=label_aliases,
            index=index,
        )

        (
            probabilities,
            probability_was_normalized,
        ) = self._validate_and_normalize_probabilities(
            probabilities,
            index=index,
        )

        predicted_label = self._normalize_label(
            raw_label,
            label_aliases=label_aliases,
            index=index,
        )

        argmax_label = self._argmax_label(
            probabilities
        )
        if self.validate_predicted_label:
            maximum = max(probabilities.values())
            predicted_probability = probabilities[
                predicted_label
            ]

            if (
                maximum - predicted_probability
                > self.probability_tolerance
            ):
                raise PredictionValidationError(
                    f"Previsão {index}: predicted_label="
                    f"{predicted_label!r} não corresponde à maior "
                    f"probabilidade, que pertence a "
                    f"{argmax_label!r}."
                )

        supplied_confidence = self._first_present(
            raw,
            CONFIDENCE_FIELD_ALIASES,
        )
        confidence = max(probabilities.values())

        if supplied_confidence is not None:
            supplied_value = self._to_finite_float(
                supplied_confidence,
                field_name="confidence",
                index=index,
            )
            if not math.isclose(
                supplied_value,
                confidence,
                abs_tol=max(
                    self.probability_sum_tolerance,
                    1e-4,
                ),
                rel_tol=0.0,
            ):
                raise PredictionValidationError(
                    f"Previsão {index}: confidence={supplied_value} "
                    f"não corresponde à maior probabilidade "
                    f"({confidence})."
                )

        processing_time = self._first_present(
            raw,
            PROCESSING_TIME_FIELD_ALIASES,
        )
        processing_time_ms: float | None = None

        if processing_time is not None:
            processing_time_ms = self._to_finite_float(
                processing_time,
                field_name="processing_time_ms",
                index=index,
            )
            if processing_time_ms < 0:
                raise PredictionValidationError(
                    f"Previsão {index}: processing_time_ms não pode "
                    "ser negativo."
                )

        metadata = self._extract_metadata(raw)
        continuous_sentiment = (
            probabilities["POSITIVE"]
            - probabilities["NEGATIVE"]
        )

        return _NormalizedPrediction(
            predicted_label=predicted_label,
            confidence=float(confidence),
            prob_positive=float(
                probabilities["POSITIVE"]
            ),
            prob_negative=float(
                probabilities["NEGATIVE"]
            ),
            prob_neutral=float(
                probabilities["NEUTRAL"]
            ),
            continuous_sentiment=float(
                continuous_sentiment
            ),
            probability_sum=float(
                sum(probabilities.values())
            ),
            processing_time_ms=processing_time_ms,
            metadata=metadata,
            probability_was_normalized=(
                probability_was_normalized
            ),
        )

    def _prediction_to_mapping(
        self,
        prediction: Any,
        *,
        index: int,
    ) -> dict[str, Any]:
        if isinstance(prediction, Mapping):
            return dict(prediction)

        if (
            not isinstance(prediction, type)
            and is_dataclass(prediction)
        ):
            value = asdict(cast(Any, prediction))
            if isinstance(value, dict):
                return value

        to_dict_method = getattr(prediction, "to_dict", None)
        if callable(to_dict_method):
            try:
                value = to_dict_method()
            except Exception as error:
                raise PredictionFormatError(
                    f"Previsão {index}: falha ao executar to_dict(): "
                    f"{error}"
                ) from error

            if isinstance(value, Mapping):
                return dict(value)

        if hasattr(prediction, "__dict__"):
            value = {
                key: item
                for key, item in vars(prediction).items()
                if not key.startswith("_")
            }
            if value:
                return value

        extracted: dict[str, Any] = {}
        known_names = {
            *LABEL_FIELD_ALIASES,
            *CONFIDENCE_FIELD_ALIASES,
            *PROBABILITY_CONTAINER_ALIASES,
            *PROCESSING_TIME_FIELD_ALIASES,
            *METADATA_FIELD_ALIASES,
        }
        for aliases in DIRECT_PROBABILITY_ALIASES.values():
            known_names.update(aliases)

        for name in known_names:
            if not hasattr(prediction, name):
                continue

            try:
                extracted[name] = getattr(prediction, name)
            except Exception:
                continue

        if extracted:
            return extracted

        raise PredictionFormatError(
            f"Previsão {index}: tipo não suportado "
            f"{type(prediction).__module__}."
            f"{type(prediction).__name__}. Use um mapping, dataclass, "
            "objeto com to_dict() ou objeto com atributos de previsão."
        )

    def _extract_probabilities(
        self,
        *,
        raw: Mapping[str, Any],
        sequence_order: Sequence[str],
        label_aliases: Mapping[str, str],
        index: int,
    ) -> dict[str, float]:
        direct: dict[str, float] = {}

        for canonical_label, aliases in (
            DIRECT_PROBABILITY_ALIASES.items()
        ):
            value = self._first_present(raw, aliases)
            if value is not None:
                direct[canonical_label] = (
                    self._to_finite_float(
                        value,
                        field_name=(
                            f"prob_{canonical_label.lower()}"
                        ),
                        index=index,
                    )
                )

        if direct:
            missing = set(CANONICAL_LABELS) - set(direct)
            if missing:
                raise PredictionFormatError(
                    f"Previsão {index}: probabilidades diretas "
                    f"incompletas. Classes ausentes: "
                    f"{sorted(missing)}."
                )
            return direct

        container = self._first_present(
            raw,
            PROBABILITY_CONTAINER_ALIASES,
        )
        if container is None:
            raise PredictionFormatError(
                f"Previsão {index}: nenhuma probabilidade foi "
                "encontrada."
            )

        if isinstance(container, Mapping):
            probabilities: dict[str, float] = {}

            for raw_label, value in container.items():
                canonical_label = self._normalize_label(
                    raw_label,
                    label_aliases=label_aliases,
                    index=index,
                )
                if canonical_label in probabilities:
                    raise PredictionFormatError(
                        f"Previsão {index}: a classe "
                        f"{canonical_label!r} apareceu mais de uma vez "
                        "nas probabilidades."
                    )
                probabilities[canonical_label] = (
                    self._to_finite_float(
                        value,
                        field_name=(
                            f"prob_{canonical_label.lower()}"
                        ),
                        index=index,
                    )
                )

            missing = (
                set(CANONICAL_LABELS)
                - set(probabilities)
            )
            if missing:
                raise PredictionFormatError(
                    f"Previsão {index}: o mapeamento de "
                    f"probabilidades não possui as classes "
                    f"{sorted(missing)}."
                )
            return probabilities

        if isinstance(
            container,
            (str, bytes, bytearray),
        ):
            raise PredictionFormatError(
                f"Previsão {index}: o campo de probabilidades não "
                "pode ser texto."
            )

        try:
            values = list(container)
        except TypeError as error:
            raise PredictionFormatError(
                f"Previsão {index}: probabilidades precisam ser um "
                "mapeamento ou sequência."
            ) from error

        if len(values) != len(sequence_order):
            raise PredictionFormatError(
                f"Previsão {index}: foram recebidas {len(values)} "
                f"probabilidades, mas eram esperadas "
                f"{len(sequence_order)}."
            )

        return {
            canonical_label: self._to_finite_float(
                value,
                field_name=(
                    f"prob_{canonical_label.lower()}"
                ),
                index=index,
            )
            for canonical_label, value in zip(
                sequence_order,
                values,
                strict=True,
            )
        }

    def _validate_and_normalize_probabilities(
        self,
        probabilities: Mapping[str, float],
        *,
        index: int,
    ) -> tuple[dict[str, float], bool]:
        normalized = {
            label: float(probabilities[label])
            for label in CANONICAL_LABELS
        }

        for label, value in normalized.items():
            if value < -self.probability_tolerance:
                raise PredictionValidationError(
                    f"Previsão {index}: probabilidade de {label} "
                    f"é negativa ({value})."
                )

            if value > 1.0 + self.probability_tolerance:
                raise PredictionValidationError(
                    f"Previsão {index}: probabilidade de {label} "
                    f"é maior que 1 ({value})."
                )

            normalized[label] = min(
                1.0,
                max(0.0, value),
            )

        probability_sum = sum(normalized.values())
        if probability_sum <= 0:
            raise PredictionValidationError(
                f"Previsão {index}: a soma das probabilidades "
                "precisa ser maior que zero."
            )

        deviation = abs(probability_sum - 1.0)
        if deviation <= self.probability_sum_tolerance:
            if probability_sum != 1.0:
                normalized = {
                    label: value / probability_sum
                    for label, value in normalized.items()
                }
                return normalized, True
            return normalized, False

        if (
            not self.normalize_probability_sum
            or deviation
            > self.maximum_normalization_deviation
        ):
            raise PredictionValidationError(
                f"Previsão {index}: a soma das probabilidades é "
                f"{probability_sum}, com desvio de {deviation}. "
                f"O máximo permitido para normalização é "
                f"{self.maximum_normalization_deviation}."
            )

        normalized = {
            label: value / probability_sum
            for label, value in normalized.items()
        }
        return normalized, True

    def _build_label_aliases(
        self,
        model_configuration: ModelConfiguration,
    ) -> dict[str, str]:
        aliases = dict(LABEL_ALIASES)
        labels_config = model_configuration.labels

        id2label = labels_config.get("id2label", {})
        if isinstance(id2label, Mapping):
            for raw_id, raw_label in id2label.items():
                canonical = self._canonical_from_known_alias(
                    raw_label,
                    aliases,
                )
                aliases[str(raw_id).strip().upper()] = canonical
                aliases[
                    f"LABEL_{str(raw_id).strip()}".upper()
                ] = canonical
                aliases[
                    str(raw_label).strip().upper()
                ] = canonical

        canonical_config = labels_config.get(
            "canonical",
            {},
        )
        if isinstance(canonical_config, Mapping):
            for logical_name, configured_label in (
                canonical_config.items()
            ):
                logical = str(logical_name).strip().upper()
                configured = (
                    str(configured_label).strip().upper()
                )
                canonical = self._canonical_from_known_alias(
                    logical,
                    aliases,
                )
                aliases[configured] = canonical

        return aliases

    def _build_probability_sequence_order(
        self,
        model_configuration: ModelConfiguration,
        label_aliases: Mapping[str, str],
    ) -> tuple[str, ...]:
        id2label = model_configuration.labels.get(
            "id2label",
            {},
        )

        if isinstance(id2label, Mapping) and id2label:
            indexed: list[tuple[int, str]] = []
            for raw_id, raw_label in id2label.items():
                try:
                    numeric_id = int(raw_id)
                except (TypeError, ValueError) as error:
                    raise PredictionFormatError(
                        f"O modelo {model_configuration.key!r} possui "
                        f"id2label não numérico: {raw_id!r}."
                    ) from error

                canonical = self._normalize_label(
                    raw_label,
                    label_aliases=label_aliases,
                    index=-1,
                )
                indexed.append((numeric_id, canonical))

            indexed.sort(key=lambda item: item[0])
            order = tuple(
                label
                for _, label in indexed
            )

            if (
                len(order) != 3
                or set(order) != set(CANONICAL_LABELS)
            ):
                raise PredictionFormatError(
                    f"O modelo {model_configuration.key!r} precisa "
                    "mapear exatamente NEGATIVE, NEUTRAL e POSITIVE "
                    "em labels.id2label."
                )

            return order

        return CANONICAL_LABELS

    def _normalize_label(
        self,
        value: Any,
        *,
        label_aliases: Mapping[str, str],
        index: int,
    ) -> str:
        if value is None:
            raise PredictionFormatError(
                f"Previsão {index}: predicted_label ausente."
            )

        if isinstance(value, bool):
            raise PredictionFormatError(
                f"Previsão {index}: rótulo booleano não é válido."
            )

        if isinstance(value, (int, np.integer)):
            key = str(int(value)).upper()
        else:
            key = str(value).strip().upper()

        if not key:
            raise PredictionFormatError(
                f"Previsão {index}: predicted_label vazio."
            )

        canonical = label_aliases.get(key)
        if canonical is None:
            available = sorted(
                set(label_aliases.values())
            )
            raise PredictionValidationError(
                f"Previsão {index}: rótulo não reconhecido "
                f"{value!r}. Classes oficiais: {available}."
            )

        return canonical

    @staticmethod
    def _canonical_from_known_alias(
        value: Any,
        aliases: Mapping[str, str],
    ) -> str:
        key = str(value).strip().upper()
        canonical = aliases.get(key)

        if canonical is None:
            raise PredictionValidationError(
                f"Classe configurada não reconhecida: {value!r}."
            )

        return canonical

    def _extract_metadata(
        self,
        raw: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not self.preserve_prediction_metadata:
            return {}

        value = self._first_present(
            raw,
            METADATA_FIELD_ALIASES,
        )
        if value is None:
            return {}

        if isinstance(value, Mapping):
            return {
                str(key): to_serializable(item)
                for key, item in value.items()
            }

        return {
            "value": to_serializable(value)
        }

    def _prediction_frame(
        self,
        predictions: Sequence[_NormalizedPrediction],
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []

        for index, prediction in enumerate(predictions):
            metadata_json: str | None
            if prediction.metadata:
                metadata_json = json.dumps(
                    prediction.metadata,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            else:
                metadata_json = None

            rows.append(
                {
                    "prediction_index": index,
                    "predicted_label": (
                        prediction.predicted_label
                    ),
                    "confidence": prediction.confidence,
                    "prob_positive": (
                        prediction.prob_positive
                    ),
                    "prob_negative": (
                        prediction.prob_negative
                    ),
                    "prob_neutral": (
                        prediction.prob_neutral
                    ),
                    "continuous_sentiment": (
                        prediction.continuous_sentiment
                    ),
                    "probability_sum": (
                        prediction.probability_sum
                    ),
                    "processing_time_ms": (
                        prediction.processing_time_ms
                    ),
                    "prediction_metadata": metadata_json,
                }
            )

        frame = pd.DataFrame(
            rows,
            columns=pd.Index(PREDICTION_COLUMNS),
        )

        frame["prediction_index"] = frame[
            "prediction_index"
        ].astype("Int64")
        frame["predicted_label"] = frame[
            "predicted_label"
        ].astype("string")
        frame["prediction_metadata"] = frame[
            "prediction_metadata"
        ].astype("string")

        numeric_columns = [
            "confidence",
            "prob_positive",
            "prob_negative",
            "prob_neutral",
            "continuous_sentiment",
            "probability_sum",
            "processing_time_ms",
        ]
        for column in numeric_columns:
            frame[column] = numeric_series(
                column_series(frame, column),
                errors="coerce",
            ).astype("Float64")

        return frame

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
    def _argmax_label(
        probabilities: Mapping[str, float],
    ) -> str:
        # A ordem canônica torna o desempate determinístico.
        return max(
            CANONICAL_LABELS,
            key=lambda label: probabilities[label],
        )

    @staticmethod
    def _first_present(
        mapping: Mapping[str, Any],
        names: Sequence[str],
    ) -> Any:
        for name in names:
            if name in mapping:
                value = mapping[name]
                if value is not None:
                    return value
        return None

    @staticmethod
    def _to_finite_float(
        value: Any,
        *,
        field_name: str,
        index: int,
    ) -> float:
        if isinstance(value, bool):
            raise PredictionValidationError(
                f"Previsão {index}: {field_name} não pode ser booleano."
            )

        try:
            converted = float(value)
        except (TypeError, ValueError) as error:
            raise PredictionValidationError(
                f"Previsão {index}: {field_name} precisa ser numérico; "
                f"recebido {value!r}."
            ) from error

        if not math.isfinite(converted):
            raise PredictionValidationError(
                f"Previsão {index}: {field_name} precisa ser finito; "
                f"recebido {converted!r}."
            )

        return converted

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
