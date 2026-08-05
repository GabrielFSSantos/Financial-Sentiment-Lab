"""Testes de carregamento das configurações YAML."""

from __future__ import annotations

from pathlib import Path

from pipeline.configuration import load_configuration


def test_load_configuration_with_example_dataset(
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo"],
    )

    assert configuration.schema_version == "2.0"
    assert len(configuration.models) == 1
    assert configuration.models[0].key == "finbert_ptbr"
    assert len(configuration.datasets) == 1
    assert configuration.datasets[0].key == "noticias_exemplo"
    assert len(configuration.combinations) == 1
