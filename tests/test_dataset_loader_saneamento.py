"""Testes de carregamento dos datasets filtrados de saneamento."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.experiment.config.loader import load_configuration
from modules.datasets.loader import DatasetLoader


def test_saneamento_ptbr_filtrado_loads_when_present(project_root: Path) -> None:
    path = project_root / "data/saneamento_ptbr_filtrado/noticias.csv"
    if not path.is_file():
        pytest.skip("saneamento_ptbr_filtrado/noticias.csv ausente localmente")

    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["saneamento_ptbr_filtrado"],
        model_keys=["finbert_ptbr"],
    )
    loaded = DatasetLoader().load(configuration.get_dataset("saneamento_ptbr_filtrado"))

    assert len(loaded.dataframe) > 0
    assert loaded.dataframe.iloc[0]["text"]


def test_saneamento_en_filtrado_loads_when_present(project_root: Path) -> None:
    path = project_root / "data/saneamento_en_filtrado/news.csv"
    if not path.is_file():
        pytest.skip("saneamento_en_filtrado/news.csv ausente localmente")

    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["saneamento_en_filtrado"],
        model_keys=["finbert_en"],
    )
    loaded = DatasetLoader().load(configuration.get_dataset("saneamento_en_filtrado"))

    assert len(loaded.dataframe) > 0
    assert loaded.dataframe.iloc[0]["text"]
