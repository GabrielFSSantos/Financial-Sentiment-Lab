"""Contrato de schema de previsões (output_schema + normalização)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from modules.datasets.loader import DatasetLoader
from modules.experiment.config.loader import load_configuration
from modules.experiment.io.output_schema import (
    OUTPUT_COLUMNS,
    OutputSchemaBuilder,
    PredictionCountError,
)
from modules.experiment.io.prediction_normalization import (
    PREDICTION_COLUMNS,
    PredictionFormatError,
    PredictionValidationError,
    build_prediction_dataframe,
    normalize_model_prediction,
    normalize_model_predictions,
)
from modules.models.base import ModelPrediction


@pytest.mark.contract
def test_output_columns_include_contract_fields() -> None:
    required = {
        "news_id",
        "text",
        "date",
        "continuous_sentiment",
        "prob_positive",
        "prob_negative",
        "prob_neutral",
        "model_key",
        "dataset_key",
        "run_id",
    }
    assert required.issubset(set(OUTPUT_COLUMNS))


@pytest.mark.contract
def test_normalize_model_prediction_continuous_sentiment() -> None:
    prediction = ModelPrediction(
        predicted_label="POSITIVE",
        prob_positive=0.7,
        prob_negative=0.2,
        prob_neutral=0.1,
    )
    normalized = normalize_model_prediction(prediction, index=0)
    assert normalized.continuous_sentiment == pytest.approx(0.5)
    assert normalized.probability_sum == pytest.approx(1.0)


@pytest.mark.contract
def test_normalize_rejects_missing_probabilities() -> None:
    prediction = ModelPrediction(
        predicted_label="POSITIVE",
        prob_positive=0.5,
        prob_negative=None,
        prob_neutral=0.5,
    )
    with pytest.raises(PredictionValidationError):
        normalize_model_prediction(prediction, index=0)


@pytest.mark.contract
def test_coerce_rejects_non_model_prediction() -> None:
    with pytest.raises(PredictionFormatError):
        normalize_model_predictions([object()])  # type: ignore[list-item]


@pytest.mark.contract
def test_build_prediction_dataframe_columns() -> None:
    prediction = ModelPrediction(
        predicted_label="NEGATIVE",
        confidence=0.8,
        prob_positive=0.1,
        prob_negative=0.8,
        prob_neutral=0.1,
        extra={"source": "unit"},
    )
    normalized = normalize_model_prediction(prediction, index=0)
    frame = build_prediction_dataframe([normalized])
    assert list(frame.columns) == list(PREDICTION_COLUMNS)
    assert frame.loc[0, "continuous_sentiment"] == pytest.approx(-0.7)


@pytest.mark.contract
def test_output_schema_builder_matches_dataset_rows(
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
        run_id="test_schema_run",
    )
    combination = configuration.combinations[0]
    loaded = DatasetLoader().load(configuration.get_dataset("noticias_exemplo_ptbr"))
    row_count = len(loaded.dataframe)

    predictions = [
        ModelPrediction(
            predicted_label="POSITIVE",
            prob_positive=0.6,
            prob_negative=0.3,
            prob_neutral=0.1,
        )
        for _ in range(row_count)
    ]

    builder = OutputSchemaBuilder(copy_dataset=False)
    standardized = builder.build_from_resolved_configuration(
        configuration=configuration,
        combination=combination,
        loaded_dataset=loaded,
        predictions=predictions,
        device_used="cpu",
    )

    assert set(OUTPUT_COLUMNS).issubset(standardized.dataframe.columns)
    assert len(standardized.dataframe) == row_count
    assert standardized.dataframe["run_id"].iloc[0] == "test_schema_run"
    assert standardized.dataframe["news_id"].notna().all()


@pytest.mark.contract
def test_output_schema_builder_rejects_prediction_count_mismatch(
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )
    combination = configuration.combinations[0]
    loaded = DatasetLoader().load(configuration.get_dataset("noticias_exemplo_ptbr"))
    builder = OutputSchemaBuilder(copy_dataset=False)

    with pytest.raises(PredictionCountError):
        builder.build_from_resolved_configuration(
            configuration=configuration,
            combination=combination,
            loaded_dataset=loaded,
            predictions=[
                ModelPrediction(
                    predicted_label="NEUTRAL",
                    prob_positive=0.2,
                    prob_negative=0.2,
                    prob_neutral=0.6,
                )
            ],
        )
