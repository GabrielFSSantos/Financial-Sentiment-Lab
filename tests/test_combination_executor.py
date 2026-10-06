"""Execução de combinação modelo × dataset (executor)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from modules.datasets.loader import DatasetLoader
from modules.experiment.config.loader import load_configuration
from modules.experiment.io.output_schema import (
    PredictionSchemaStatistics,
    StandardizedPredictions,
)
from modules.experiment.pipeline.combination_executor import (
    CombinationRunResult,
    execute_combination,
)
from modules.experiment.stages.aggregation import AggregationResult
from modules.experiment.stages.metrics import ClassificationMetricsResult
from modules.models.base import ModelPrediction


@pytest.mark.pipeline
def test_combination_run_result_serializes() -> None:
    result = CombinationRunResult(
        combination_id="m__d",
        model_key="m",
        dataset_key="d",
        status="success",
        duration_seconds=1.0,
        row_count=2,
        valid_text_count=2,
        device="cpu",
    )
    payload = result.to_dict()
    assert payload["status"] == "success"
    assert payload["row_count"] == 2


@pytest.mark.pipeline
def test_execute_combination_persists_results_and_index(
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
        run_id="test_executor_run",
    )
    combination = configuration.combinations[0]
    model_configuration = configuration.get_model(combination.model_key)
    loaded_real = DatasetLoader().load(
        configuration.get_dataset(combination.dataset_key)
    )

    predictions_df = pd.DataFrame({"news_id": ["1"], "continuous_sentiment": [0.1]})
    statistics = PredictionSchemaStatistics(
        row_count=1,
        positive_count=0,
        negative_count=0,
        neutral_count=1,
        mean_confidence=0.5,
        mean_continuous_sentiment=0.1,
        minimum_continuous_sentiment=0.1,
        maximum_continuous_sentiment=0.1,
        probability_rows_normalized=0,
        prediction_metadata_rows=0,
    )
    standardized = StandardizedPredictions(
        dataframe=predictions_df,
        statistics=statistics,
        combination=combination,
        model_configuration=model_configuration,
        dataset=loaded_real,
        warnings=(),
    )

    empty = pd.DataFrame()
    classification = ClassificationMetricsResult(
        summary=empty,
        per_class=empty,
        confusion_matrix=empty,
        class_distribution=empty,
        enabled=False,
        available=False,
        evaluated_rows=0,
        ignored_unlabeled_rows=0,
        warnings=(),
    )
    aggregation = AggregationResult(
        dataframe=empty,
        enabled=False,
        status="skipped",
        sentiment_column="continuous_sentiment",
        minimum_news_per_group=1,
        requested_levels=(),
        generated_levels=(),
        skipped_levels={},
        level_summaries=(),
        warnings=(),
    )

    registered = MagicMock()
    registered.device_type = "cpu"
    registered.device_name = "cpu"
    registered.predict.return_value = [
        ModelPrediction(
            predicted_label="NEUTRAL",
            prob_positive=0.2,
            prob_negative=0.2,
            prob_neutral=0.6,
        )
    ]
    registered.load = MagicMock()

    runner = MagicMock()
    runner.configuration = configuration
    runner.logger = MagicMock()
    runner.dataset_loader.load.return_value = loaded_real
    runner.registry.create.return_value = registered
    runner.output_builder.build.return_value = standardized
    runner.classification_calculator.calculate.return_value = classification
    runner.classification_calculator.labels = ("POSITIVE", "NEGATIVE", "NEUTRAL")
    runner.aggregator.aggregate.return_value = aggregation
    runner.results = MagicMock()
    runner._raise_if_interrupted = MagicMock()
    runner._success_metadata.return_value = {}
    runner.temporal_index_builder.enabled = True
    runner.temporal_index_builder.fail_on_error = True
    runner.temporal_index_builder.build.return_value = MagicMock()

    result = execute_combination(runner, combination)

    assert result.status == "success"
    assert result.row_count == 1
    runner.results.save_combination_results.assert_called_once()
    runner.results.save_temporal_index.assert_called_once()
    runner.results.complete_combination.assert_called_once()
