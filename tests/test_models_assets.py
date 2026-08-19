"""Testes de fetch/check de modelos (``modules.models.assets``)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.experiment.config.loader import load_configuration
from modules.models.assets import fetch_model_asset


def test_fetch_model_skips_when_present(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo"],
    )
    model = configuration.get_model("finbert_ptbr")

    if not model.model_dir.is_dir():
        pytest.skip("FinBERT-PT-BR não está em model_store/")

    report = fetch_model_asset(model)
    assert report is not None
    assert report.status == "skipped"


@patch("modules.models.assets.snapshot_download")
def test_fetch_model_downloads_when_missing(
    mock_download,
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_en"],
        dataset_keys=["news_example_en"],
    )
    model = configuration.get_model("finbert_en")

    if model.model_dir.is_dir():
        pytest.skip("FinBERT-EN já presente em model_store/")

    report = fetch_model_asset(model)
    assert report is not None
    assert report.status == "downloaded"
    mock_download.assert_called_once()
