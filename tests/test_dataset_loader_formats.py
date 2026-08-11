"""Testes dos formatos estendidos do dataset loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.configuration import load_configuration
from pipeline.dataset_loader import DatasetLoader


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
    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["en_financial_news_dataset"],
        model_keys=["finbert_en"],
    )
    dataset = configuration.get_dataset("en_financial_news_dataset")
    loader = DatasetLoader()

    sample = pd.DataFrame(
        {
            "Article_title": ["Apple beats estimates"],
            "Article": ["Apple reported stronger than expected earnings."],
            "Date": ["2023-11-24 00:00:00 UTC"],
            "Stock_symbol": ["AAPL"],
            "Url": ["https://example.invalid/a"],
            "Publisher": ["Nasdaq"],
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
