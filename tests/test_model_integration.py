"""Testes de integração de modelos e matriz bilíngue do experimento."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from modules.experiment.config.loader import load_configuration
from modules.datasets.loader import DatasetLoader
from modules.models.registry import create_model_registry


def test_full_bilingual_combination_matrix(project_root: Path) -> None:
    configuration = load_configuration(project_root=project_root)

    assert len(configuration.models) == 3
    assert len(configuration.datasets) == 4
    assert len(configuration.combinations) == 7
    assert len(configuration.skipped_combinations) == 5

    for combination in configuration.combinations:
        model = configuration.get_model(combination.model_key)
        dataset = configuration.get_dataset(combination.dataset_key)
        assert model.language == dataset.language

    skipped_pairs = {
        (skipped.model_key, skipped.dataset_key)
        for skipped in configuration.skipped_combinations
    }
    assert len(skipped_pairs) == 5


def test_finbert_tone_en_legacy_load(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_tone_en"],
        dataset_keys=["news_example_en"],
    )
    model_configuration = configuration.get_model("finbert_tone_en")

    if not model_configuration.model_dir.is_dir():
        pytest.skip("FinBERT-Tone-EN não está em model_store/")

    registry = create_model_registry(configuration)
    registered = registry.create(model_configuration, load=True)

    try:
        assert registered.is_loaded
        runtime = registered.instance.get_metadata()
        assert runtime["model_language"] == "en"
        assert runtime["tokenizer_class"] in {
            "BertTokenizer",
            "BertTokenizerFast",
        }

        dataset = configuration.get_dataset("news_example_en")
        loaded = DatasetLoader().load(dataset)
        predictions = registered.predict(loaded.texts[:2])
        assert len(predictions) == 2
        assert all(
            prediction.predicted_label in {"POSITIVE", "NEGATIVE", "NEUTRAL"}
            for prediction in predictions
        )
    finally:
        registered.unload()


def test_max_rows_limits_example_csv_read(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["noticias_exemplo_ptbr"],
        model_keys=["finbert_ptbr"],
    )
    dataset = configuration.get_dataset("noticias_exemplo_ptbr")

    limited = replace(
        dataset,
        limits={**dataset.limits, "max_rows": 5},
    )
    loaded = DatasetLoader().load(limited)
    assert len(loaded.dataframe) == 5


def test_control_pt_models_load_when_present(project_root: Path) -> None:
    for model_key in ("bertweet_pt_sentiment", "bertimbau_sentiment"):
        configuration = load_configuration(
            project_root=project_root,
            model_keys=[model_key],
            dataset_keys=["noticias_exemplo_ptbr"],
        )
        model_configuration = configuration.get_model(model_key)
        if not model_configuration.model_dir.is_dir():
            pytest.skip(f"{model_key} não está em model_store/")
        registry = create_model_registry(configuration)
        registered = registry.create(model_configuration, load=True)
        try:
            assert registered.is_loaded
            dataset = configuration.get_dataset("noticias_exemplo_ptbr")
            loaded = DatasetLoader().load(dataset)
            predictions = registered.predict(loaded.texts[:2])
            assert len(predictions) == 2
            assert all(
                prediction.predicted_label in {"POSITIVE", "NEGATIVE", "NEUTRAL"}
                for prediction in predictions
            )
        finally:
            registered.unload()
