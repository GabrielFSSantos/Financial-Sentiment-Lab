"""Campanha rotulos_manual_pt_100 usa título + corpo (text_compose)."""

from __future__ import annotations

from pathlib import Path

from modules.datasets.config.loader import load_datasets_configuration
from modules.datasets.loader import DatasetLoader


def test_rotulos_manual_pt_100_text_compose(project_root: Path) -> None:
    configuration = load_datasets_configuration(project_root=project_root)
    dataset = configuration.get_dataset("rotulos_manual_pt_100")
    assert dataset.text_compose is not None
    assert dataset.columns.get("text") is None

    loaded = DatasetLoader().load(dataset)
    assert not loaded.dataframe.empty
    sample_text = str(loaded.dataframe.iloc[0]["text"])
    title = str(loaded.dataframe.iloc[0].get("title", ""))
    if title and title != "nan":
        assert title in sample_text
