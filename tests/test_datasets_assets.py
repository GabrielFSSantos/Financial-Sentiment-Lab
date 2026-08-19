"""Testes de fetch de datasets (``modules.datasets.assets``)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.datasets.assets import fetch_dataset_asset
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
            dataset_keys=["noticias_exemplo"],
            model_keys=["finbert_ptbr"],
        ).get_dataset("noticias_exemplo"),
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
        dataset_keys=["saneamento_ptbr_filtrado"],
        model_keys=["finbert_ptbr"],
    )
    dataset = configuration.get_dataset("saneamento_ptbr_filtrado")
    assert not dataset.source
    assert fetch_dataset_asset(dataset) is None
