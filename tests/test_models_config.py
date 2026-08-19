"""Testes isolados de ``configs/models.yaml``."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.models.config.loader import (
    ConfigurationError,
    load_models_configuration,
)


def test_load_models_configuration(project_root: Path) -> None:
    configuration = load_models_configuration(project_root=project_root)
    assert configuration.schema_version == "2.0"
    assert len(configuration.models) >= 4
    assert configuration.get_model("finbert_ptbr").adapter.startswith(
        "modules.models.adapters"
    )


def test_load_models_configuration_rejects_invalid_adapter(
    project_root: Path,
    tmp_path: Path,
) -> None:
    invalid_yaml = tmp_path / "models.yaml"
    invalid_yaml.write_text(
        """
schema_version: "2.0"
defaults:
  language: pt
  parameters:
    batch_size: 32
    max_length: 512
    device: auto
  loading: {}
  validation: {}
models:
  bad_model:
    enabled: true
    order: 1
    model_name: bad_model
    display_name: Bad
    adapter: InvalidAdapter
    model_dir: model_store/bad
    parameters:
      batch_size: 32
      max_length: 512
      device: auto
    loading: {}
    validation: {}
    files:
      required:
        - config.json
    labels:
      id2label:
        0: POSITIVE
        1: NEGATIVE
        2: NEUTRAL
      canonical:
        positive: POSITIVE
        negative: NEGATIVE
        neutral: NEUTRAL
      continuous_sentiment:
        positive_label: POSITIVE
        negative_label: NEGATIVE
        formula: "prob_positive - prob_negative"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="adapter"):
        load_models_configuration(
            project_root=project_root,
            config_path=invalid_yaml,
        )
