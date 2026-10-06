"""Carregamento de ``configs/evaluation.yaml``."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.evaluation.core.settings import (
    EvaluationConfigError,
    load_evaluation_settings,
)


def test_load_evaluation_settings(project_root: Path) -> None:
    settings = load_evaluation_settings(
        project_root / "configs" / "evaluation.yaml"
    )
    assert settings.gate_accuracy == pytest.approx(0.70)
    assert settings.gate_kappa == pytest.approx(0.40)
    assert settings.manual_labels_path.is_absolute()
    assert "llm_judge_pilot" in str(settings.llm_judge_output_csv)


def test_load_evaluation_settings_missing_file(tmp_path: Path) -> None:
    with pytest.raises(EvaluationConfigError, match="Missing"):
        load_evaluation_settings(tmp_path / "missing.yaml")
