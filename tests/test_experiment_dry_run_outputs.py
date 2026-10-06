"""Dry-run do experimento — contrato em memória (sem gravar outputs/)."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.experiment.config.loader import load_configuration
from modules.experiment.pipeline.runner import ExperimentRunner


@pytest.mark.pipeline
@pytest.mark.slow
def test_dry_run_validates_without_writing_output_tree(project_root: Path) -> None:
    run_id = "pytest_dry_run_contract"
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
        dry_run=True,
        run_id=run_id,
    )
    runner = ExperimentRunner(configuration)
    outcome = runner.run()

    assert outcome.exit_code == 0
    summary = outcome.summary
    assert summary.get("dry_run") is True
    assert summary.get("status") == "success"
    assert not configuration.paths.run_root.exists()

    combinations = summary.get("combinations", [])
    assert len(combinations) == 1
    combo = combinations[0]
    assert combo.get("status") == "skipped"
    assert combo.get("error_message") == "dry_run_validation_only"
    assert combo.get("extra", {}).get("validated") is True
    assert combo.get("row_count", 0) > 0
