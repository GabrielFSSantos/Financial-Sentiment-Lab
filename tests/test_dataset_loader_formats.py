"""Testes dos formatos estendidos do dataset loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from modules.experiment.config.loader import load_configuration
from modules.datasets.loader import DatasetLoader


def test_news_example_en_loads(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["news_example_en"],
        model_keys=["finbert_en"],
    )
    dataset = configuration.get_dataset("news_example_en")
    loaded = DatasetLoader().load(dataset)

    assert len(loaded.dataframe) == 18
    assert loaded.has_labels
    assert set(loaded.dataframe["true_label"].dropna()) <= {
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
    }


def test_text_compose_builds_text(project_root: Path) -> None:
    from dataclasses import replace

    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["news_example_en"],
        model_keys=["finbert_en"],
    )
    dataset = replace(
        configuration.get_dataset("news_example_en"),
        text_compose={
            "template": "Title: {title}\nBody: {body}",
            "fields": {"title": "title", "body": "news_text"},
            "skip_if_all_empty": True,
        },
        columns={
            **configuration.get_dataset("news_example_en").columns,
            "text": None,
            "true_label": None,
        },
    )
    loader = DatasetLoader()

    sample = pd.DataFrame(
        {
            "title": ["Apple beats estimates"],
            "news_text": ["Apple reported stronger than expected earnings."],
            "date": ["2023-11-24"],
            "company": ["Apple"],
            "sector": ["Tech"],
            "ticker": ["AAPL"],
            "id": ["1"],
            "source": ["Example"],
            "url": ["https://example.invalid/a"],
        }
    )
    composed = loader._apply_text_compose(dataset, sample)
    assert "__composed_text__" in composed.columns
    assert "Apple beats estimates" in composed.iloc[0]["__composed_text__"]

    mapped = loader._map_standard_columns(
        dataset,
        composed,
        pd.Series([1], dtype="Int64"),
    )
    assert "Apple reported" in mapped.iloc[0]["text"]
