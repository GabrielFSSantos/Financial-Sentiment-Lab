"""Testes de validação de formato e colunas."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.datasets.config.loader import DatasetConfiguration
from modules.datasets.loader import (
    DatasetFileError,
    DatasetLoader,
    DatasetValidationError,
    validate_dataset,
)
from modules.experiment.config.loader import load_configuration


def test_validate_dataset_noticias_exemplo(project_root: Path) -> None:
    configuration = load_configuration(
        project_root=project_root,
        dataset_keys=["noticias_exemplo"],
        model_keys=["finbert_ptbr"],
    )
    report = validate_dataset(configuration.get_dataset("noticias_exemplo"))
    assert report["valid"] is True
    assert "id" in report["columns"] or "noticia" in report["columns"]


def test_validate_file_rejects_missing_path(tmp_path: Path) -> None:
    dataset = DatasetConfiguration(
        key="missing",
        enabled=True,
        order=1,
        dataset_name="missing",
        display_name="Missing",
        language="pt",
        path=tmp_path / "missing.csv",
        format="csv",
        reader={
            "encoding": "utf-8",
            "delimiter": ",",
            "quotechar": '"',
            "header": 0,
            "low_memory": False,
            "skip_blank_lines": True,
            "on_bad_lines": "error",
        },
        columns={"news_id": "id", "text": "body"},
        required_fields=("news_id", "text"),
        labels={"available": False},
        dates={"available": False},
        validation={},
        metadata={},
        source={},
        text_compose=None,
        limits={},
        raw={},
    )

    with pytest.raises(DatasetFileError, match="não encontrado"):
        DatasetLoader().validate_file(dataset)


def test_inspect_columns_rejects_missing_mapped_column(
    project_root: Path,
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("id,body\n1,hello\n", encoding="utf-8")

    from dataclasses import replace

    base = load_configuration(
        project_root=project_root,
        dataset_keys=["noticias_exemplo"],
        model_keys=["finbert_ptbr"],
    ).get_dataset("noticias_exemplo")

    dataset = replace(
        base,
        key="bad_columns",
        dataset_name="bad_columns",
        path=csv_path,
        columns={"news_id": "id", "text": "missing_column"},
    )

    with pytest.raises(DatasetValidationError, match="missing_column"):
        DatasetLoader().inspect_columns(dataset)
