"""Loader estrito analysis_plan.yaml."""

from pathlib import Path

import pytest

from modules.research.config.analysis_plan import AnalysisPlanError, load_analysis_plan


def test_load_analysis_plan_ok(project_root: Path) -> None:
    path = project_root / "configs/campaigns/iti_v2/analysis_plan.yaml"
    plan = load_analysis_plan(path)
    assert plan.primary_metric == "spearman"
    assert plan.bootstrap_replicates == 10000


def test_rejects_unknown_field(project_root: Path, tmp_path: Path) -> None:
    src = project_root / "configs/campaigns/iti_v2/analysis_plan.yaml"
    text = src.read_text(encoding="utf-8") + "\nextra_field: true\n"
    bad = tmp_path / "bad.yaml"
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(AnalysisPlanError, match="desconhecidos"):
        load_analysis_plan(bad)
