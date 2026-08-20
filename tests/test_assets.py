"""Testes de orquestração de assets no experimento."""

from __future__ import annotations

from pathlib import Path

from modules.experiment.config.loader import load_configuration


def test_configuration_includes_bilingual_defaults(project_root: Path) -> None:
    configuration = load_configuration(project_root=project_root)
    assert configuration.get_model("finbert_en").language == "en"
    assert configuration.get_dataset("news_example_en").language == "en"
    assert configuration.get_dataset("noticias_exemplo_ptbr").limits["max_rows"] is None


def test_limits_max_reads_all_example_rows(project_root: Path) -> None:
    from modules.datasets.loader import DatasetLoader

    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["noticias_exemplo_ptbr"],
        model_keys=["finbert_ptbr"],
    )
    loaded = DatasetLoader().load(configuration.get_dataset("noticias_exemplo_ptbr"))
    assert len(loaded.dataframe) == 18
