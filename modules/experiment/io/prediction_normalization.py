"""Normalização de ``ModelPrediction`` para o schema tabular do experimento."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import pandas as pd

from modules.experiment.common import column_series, numeric_series, to_serializable
from modules.models.base import ModelPrediction

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


class PredictionFormatError(TypeError):
    """Formato de previsão incompatível com o contrato do experimento."""


class PredictionValidationError(ValueError):
    """Previsão inválida após normalização."""


@dataclass(frozen=True)
class NormalizedPrediction:
    """Previsão normalizada pronta para montagem do DataFrame."""

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


def _metadata_from_prediction(
    prediction: ModelPrediction,
    *,
    preserve_metadata: bool,
) -> dict[str, Any]:
    if not preserve_metadata or not prediction.extra:
        return {}

    return {
        str(key): to_serializable(value)
        for key, value in prediction.extra.items()
    }


def normalize_model_prediction(
    prediction: ModelPrediction,
    *,
    index: int,
    preserve_metadata: bool = True,
) -> NormalizedPrediction:
    """Converte uma ``ModelPrediction`` validada pelo adaptador."""

    if not isinstance(prediction, ModelPrediction):
        raise PredictionFormatError(
            f"Previsão {index}: tipo não suportado "
            f"{type(prediction).__module__}.{type(prediction).__name__}. "
            "Use apenas instâncias de ModelPrediction."
        )

    if (
        prediction.prob_positive is None
        or prediction.prob_negative is None
        or prediction.prob_neutral is None
    ):
        raise PredictionValidationError(
            f"Previsão {index}: probabilidades POSITIVE, NEGATIVE e NEUTRAL "
            "são obrigatórias."
        )

    probabilities = {
        "POSITIVE": float(prediction.prob_positive),
        "NEGATIVE": float(prediction.prob_negative),
        "NEUTRAL": float(prediction.prob_neutral),
    }
    probability_sum = float(sum(probabilities.values()))
    confidence = float(
        prediction.confidence
        if prediction.confidence is not None
        else max(probabilities.values())
    )
    continuous_sentiment = (
        float(prediction.continuous_sentiment)
        if prediction.continuous_sentiment is not None
        else probabilities["POSITIVE"] - probabilities["NEGATIVE"]
    )

    processing_time_ms: float | None = None
    if prediction.processing_time_ms is not None:
        processing_time_ms = float(prediction.processing_time_ms)
        if processing_time_ms < 0:
            raise PredictionValidationError(
                f"Previsão {index}: processing_time_ms não pode ser negativo."
            )

    return NormalizedPrediction(
        predicted_label=prediction.predicted_label,
        confidence=confidence,
        prob_positive=probabilities["POSITIVE"],
        prob_negative=probabilities["NEGATIVE"],
        prob_neutral=probabilities["NEUTRAL"],
        continuous_sentiment=continuous_sentiment,
        probability_sum=probability_sum,
        processing_time_ms=processing_time_ms,
        metadata=_metadata_from_prediction(
            prediction,
            preserve_metadata=preserve_metadata,
        ),
        probability_was_normalized=False,
    )


def normalize_model_predictions(
    predictions: Sequence[ModelPrediction],
    *,
    preserve_metadata: bool = True,
) -> list[NormalizedPrediction]:
    """Normaliza uma sequência de previsões do adaptador."""

    return [
        normalize_model_prediction(
            prediction,
            index=index,
            preserve_metadata=preserve_metadata,
        )
        for index, prediction in enumerate(predictions)
    ]


def build_prediction_dataframe(
    predictions: Sequence[NormalizedPrediction],
) -> pd.DataFrame:
    """Monta o DataFrame de colunas de previsão."""

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
                "predicted_label": prediction.predicted_label,
                "confidence": prediction.confidence,
                "prob_positive": prediction.prob_positive,
                "prob_negative": prediction.prob_negative,
                "prob_neutral": prediction.prob_neutral,
                "continuous_sentiment": prediction.continuous_sentiment,
                "probability_sum": prediction.probability_sum,
                "processing_time_ms": prediction.processing_time_ms,
                "prediction_metadata": metadata_json,
            }
        )

    frame = pd.DataFrame(
        rows,
        columns=pd.Index(PREDICTION_COLUMNS),
    )

    frame["prediction_index"] = frame["prediction_index"].astype("Int64")
    frame["predicted_label"] = frame["predicted_label"].astype("string")
    frame["prediction_metadata"] = frame["prediction_metadata"].astype("string")

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


def coerce_model_predictions(
    predictions: Sequence[ModelPrediction],
) -> tuple[ModelPrediction, ...]:
    """Materializa previsões sem cópia extra quando já for tupla/lista."""

    materialized = tuple(predictions)
    for index, prediction in enumerate(materialized):
        if not isinstance(prediction, ModelPrediction):
            raise PredictionFormatError(
                f"Previsão {index}: tipo não suportado "
                f"{type(prediction).__module__}.{type(prediction).__name__}. "
                "Use apenas instâncias de ModelPrediction."
            )

    return materialized
