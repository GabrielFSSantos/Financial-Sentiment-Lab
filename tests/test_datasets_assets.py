"""Testes de fetch de datasets (``modules.datasets.assets``)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.datasets.assets import (
    _row_matches_dataset_limits,
    fetch_dataset_asset,
    fetch_enabled_datasets,
)
from modules.datasets.config.loader import load_datasets_configuration
from modules.experiment.config.loader import load_configuration


def test_fetch_dataset_skips_example_csv(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_en"],
        dataset_keys=["news_example_en"],
    )
    dataset = configuration.get_dataset("news_example_en")

    report = fetch_dataset_asset(dataset)
    assert report is None


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

    target = tmp_path / "sample.jsonl"
    dataset = replace(
        load_configuration(
            project_root=project_root,
            dataset_keys=["noticias_exemplo_ptbr"],
            model_keys=["finbert_ptbr"],
        ).get_dataset("noticias_exemplo_ptbr"),
        path=target,
        format="jsonl",
        limits={"max_rows": 3},
        source={
            "provider": "huggingface_dataset",
            "repo_id": "example/sample-dataset",
            "revision": "main",
            "split": "train",
            "data_files": "sample.jsonl",
            "materialize_format": "jsonl",
            "local_path": str(target),
        },
    )

    report = fetch_dataset_asset(dataset)
    assert report is not None
    assert report.status == "downloaded"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert content.count("\n") == 3
    assert "2024-01-01 12:00:00" in content


def test_fetch_dataset_skips_local_csv_without_source(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["saneamento_corpus"],
        model_keys=["finbert_ptbr"],
    )
    dataset = configuration.get_dataset("saneamento_corpus")
    assert not dataset.source
    assert fetch_dataset_asset(dataset) is None


def test_row_matches_dataset_limits_filters_ticker_and_date(project_root: Path) -> None:
    configuration = load_datasets_configuration(project_root=project_root)
    dataset = configuration.get_dataset("fnspid_pilot")
    assert _row_matches_dataset_limits(
        {"Stock_symbol": "AAPL", "Date": "2022-06-01"},
        dataset,
    )
    assert not _row_matches_dataset_limits(
        {"Stock_symbol": "TSLA", "Date": "2022-06-01"},
        dataset,
    )
    assert not _row_matches_dataset_limits(
        {"Stock_symbol": "AAPL", "Date": "2019-01-01"},
        dataset,
    )


@patch("modules.datasets.assets.fetch_dataset_asset")
def test_fetch_enabled_datasets_includes_disabled_when_requested(
    mock_fetch,
    project_root: Path,
) -> None:
    configuration = load_datasets_configuration(project_root=project_root)
    mock_fetch.return_value = None

    fetch_enabled_datasets(
        configuration,
        dataset_keys=["nosible_financial_sentiment_en"],
    )

    mock_fetch.assert_called_once()
    called_dataset = mock_fetch.call_args.args[0]
    assert called_dataset.key == "nosible_financial_sentiment_en"
    assert called_dataset.enabled is False


@patch("datasets.load_dataset")
def test_fetch_dataset_sample_passes_hf_config_name(
    mock_load_dataset,
    project_root: Path,
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    mock_load_dataset.return_value = iter([{"sentence": "ok", "label": "positive", "id": "1"}])

    target = tmp_path / "phrasebank.csv"
    base = load_datasets_configuration(project_root=project_root).get_dataset(
        "financial_phrasebank_en"
    )
    dataset = replace(
        base,
        path=target,
        limits={"max_rows": 1},
        source={**base.source, "local_path": str(target)},
    )

    report = fetch_dataset_asset(dataset)
    assert report is not None
    assert report.status == "downloaded"
    mock_load_dataset.assert_called_once()
    assert mock_load_dataset.call_args.kwargs["name"] == "sentences_allagree"
