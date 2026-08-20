"""Testes de compatibilidade de idioma modelo×dataset."""

from __future__ import annotations

from pathlib import Path

from modules.experiment.config.loader import (
    ConfigurationLoader,
    DatasetConfiguration,
    ModelConfiguration,
    load_configuration,
)


def test_load_configuration_includes_language_fields(
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )

    assert configuration.models[0].language == "pt"
    assert configuration.datasets[0].language == "pt"
    assert configuration.compatibility["require_language_match"] is True
    assert configuration.temporal_index["enabled"] is True


def test_language_mismatch_is_skipped(project_root: Path) -> None:
    loader = ConfigurationLoader(project_root=project_root)
    models = [
        ModelConfiguration(
            key="model_pt",
            enabled=True,
            order=1,
            model_name="model_pt",
            display_name="Model PT",
            language="pt",
            adapter="models.bert.finbert_ptbr.FinBertPtBrModel",
            model_dir=project_root / "model_store/FinBERT-PT-BR",
            parameters={},
            loading={},
            validation={},
            required_files=("config.json",),
            labels={},
            metadata={},
            source={},
            raw={},
        )
    ]
    datasets = [
        DatasetConfiguration(
            key="dataset_en",
            enabled=True,
            order=1,
            dataset_name="dataset_en",
            display_name="Dataset EN",
            language="en",
            path=project_root / "data/noticias_exemplo_ptbr/noticias.csv",
            format="csv",
            reader={},
            columns={"news_id": "id", "text": "noticia"},
            required_fields=("news_id", "text"),
            labels={},
            dates={},
            validation={},
            metadata={},
            source={},
            text_compose=None,
            limits={},
            raw={},
        )
    ]

    combinations, skipped = loader._build_combinations(
        models,
        datasets,
        require_language_match=True,
    )

    assert combinations == []
    assert len(skipped) == 1
    assert skipped[0].reason == "language_mismatch"


def test_language_match_builds_combination(project_root: Path) -> None:
    loader = ConfigurationLoader(project_root=project_root)
    models = [
        ModelConfiguration(
            key="model_pt",
            enabled=True,
            order=1,
            model_name="model_pt",
            display_name="Model PT",
            language="pt",
            adapter="models.bert.finbert_ptbr.FinBertPtBrModel",
            model_dir=project_root / "model_store/FinBERT-PT-BR",
            parameters={},
            loading={},
            validation={},
            required_files=("config.json",),
            labels={},
            metadata={},
            source={},
            raw={},
        )
    ]
    datasets = [
        DatasetConfiguration(
            key="dataset_pt",
            enabled=True,
            order=1,
            dataset_name="dataset_pt",
            display_name="Dataset PT",
            language="pt",
            path=project_root / "data/noticias_exemplo_ptbr/noticias.csv",
            format="csv",
            reader={},
            columns={"news_id": "id", "text": "noticia"},
            required_fields=("news_id", "text"),
            labels={},
            dates={},
            validation={},
            metadata={},
            source={},
            text_compose=None,
            limits={},
            raw={},
        )
    ]

    combinations, skipped = loader._build_combinations(
        models,
        datasets,
        require_language_match=True,
    )

    assert len(combinations) == 1
    assert skipped == []


def test_language_mismatch_allowed_when_disabled(
    project_root: Path,
) -> None:
    loader = ConfigurationLoader(project_root=project_root)
    models = [
        ModelConfiguration(
            key="model_pt",
            enabled=True,
            order=1,
            model_name="model_pt",
            display_name="Model PT",
            language="pt",
            adapter="models.bert.finbert_ptbr.FinBertPtBrModel",
            model_dir=project_root / "model_store/FinBERT-PT-BR",
            parameters={},
            loading={},
            validation={},
            required_files=("config.json",),
            labels={},
            metadata={},
            source={},
            raw={},
        )
    ]
    datasets = [
        DatasetConfiguration(
            key="dataset_en",
            enabled=True,
            order=1,
            dataset_name="dataset_en",
            display_name="Dataset EN",
            language="en",
            path=project_root / "data/noticias_exemplo_ptbr/noticias.csv",
            format="csv",
            reader={},
            columns={"news_id": "id", "text": "noticia"},
            required_fields=("news_id", "text"),
            labels={},
            dates={},
            validation={},
            metadata={},
            source={},
            text_compose=None,
            limits={},
            raw={},
        )
    ]

    combinations, skipped = loader._build_combinations(
        models,
        datasets,
        require_language_match=False,
    )

    assert len(combinations) == 1
    assert skipped == []
