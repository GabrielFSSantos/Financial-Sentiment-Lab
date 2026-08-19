"""Testes isolados de ``configs/datasets.yaml``."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.datasets.config.loader import (
    ConfigurationError,
    load_datasets_configuration,
)


def test_load_datasets_configuration(project_root: Path) -> None:
    configuration = load_datasets_configuration(project_root=project_root)
    assert configuration.schema_version == "2.0"
    assert len(configuration.datasets) >= 5
    assert configuration.get_dataset("noticias_exemplo").path is not None
    assert configuration.get_dataset("saneamento_corpus").path is not None


def test_load_datasets_configuration_rejects_missing_path(
    project_root: Path,
    tmp_path: Path,
) -> None:
    invalid_yaml = tmp_path / "datasets.yaml"
    invalid_yaml.write_text(
        """
schema_version: "2.0"
defaults:
  language: pt
  format: csv
  reader:
    encoding: utf-8
    delimiter: ","
    quotechar: '"'
    header: 0
    low_memory: false
    skip_blank_lines: true
    on_bad_lines: error
  validation: {}
  labels:
    available: false
    normalize_case: true
    strip_whitespace: true
    mapping: {}
  dates:
    available: false
    format: null
    dayfirst: false
    fail_on_invalid: true
    output_format: "%Y-%m-%d"
  limits:
    max_rows: 200
datasets:
  bad_dataset:
    enabled: true
    order: 1
    dataset_name: bad_dataset
    display_name: Bad
    format: csv
    columns:
      news_id: id
      text: body
    required_fields:
      - news_id
      - text
    labels:
      available: false
    dates:
      available: false
    validation: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="path"):
        load_datasets_configuration(
            project_root=project_root,
            config_path=invalid_yaml,
        )
