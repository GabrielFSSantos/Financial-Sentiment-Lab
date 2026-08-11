"""Testes do fetch declarativo de assets."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.assets import fetch_dataset_asset, fetch_model_asset
from pipeline.configuration import load_configuration


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


def test_fetch_dataset_skips_example_csv(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_en"],
        dataset_keys=["news_example_en"],
    )
    dataset = configuration.get_dataset("news_example_en")

    report = fetch_dataset_asset(dataset)
    assert report is None


@patch("pipeline.assets.snapshot_download")
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


@patch("datasets.load_dataset")
def test_fetch_dataset_sample_materializes(
    mock_load_dataset,
    project_root: Path,
    tmp_path: Path,
) -> None:
    from dataclasses import replace
    from datetime import datetime

    mock_load_dataset.return_value = iter(
        [
            {
                "text": f"news {index}",
                "published_at": datetime(2024, 1, index + 1, 12, 0, 0),
            }
            for index in range(3)
        ]
    )

    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["ptbr_financial_news_dataset"],
        model_keys=["finbert_ptbr"],
    )
    target = tmp_path / "sample.jsonl"
    dataset = replace(
        configuration.get_dataset("ptbr_financial_news_dataset"),
        path=target,
        source={
            **configuration.get_dataset(
                "ptbr_financial_news_dataset"
            ).source,
            "local_path": str(target),
        },
    )

    report = fetch_dataset_asset(dataset)
    assert report is not None
    assert report.status == "downloaded"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert content.count("\n") == 3
    assert "2024-01-01T12:00:00" in content


def test_configuration_includes_bilingual_defaults(project_root: Path) -> None:
    configuration = load_configuration(project_root=project_root)
    assert configuration.get_model("finbert_en").language == "en"
    assert configuration.get_dataset("news_example_en").language == "en"
    assert configuration.get_dataset("noticias_exemplo").limits["max_rows"] is None


def test_limits_max_reads_all_example_rows(project_root: Path) -> None:
    from pipeline.dataset_loader import DatasetLoader

    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["noticias_exemplo"],
        model_keys=["finbert_ptbr"],
    )
    loaded = DatasetLoader().load(configuration.get_dataset("noticias_exemplo"))
    assert len(loaded.dataframe) == 18
