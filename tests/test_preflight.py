"""Preflight: flags reais, I/O opcional e invariantes sempre ativas."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from modules.datasets.loader import DatasetLoader
from modules.experiment.config.loader import load_configuration
from modules.experiment.pipeline.runner import ExperimentRunner

REAL_PREFLIGHT_FLAGS = {
    "enabled",
    "validate_model_files",
    "validate_dataset_files",
    "validate_output_directory",
}


def test_experiment_yaml_preflight_has_only_real_flags(project_root: Path) -> None:
    payload = yaml.safe_load(
        (project_root / "configs" / "experiment.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert set(payload["preflight_checks"]) == REAL_PREFLIGHT_FLAGS


def test_preflight_disabled_skips_inspect_columns(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )
    configuration = replace(
        configuration,
        preflight_checks={
            **configuration.preflight_checks,
            "enabled": False,
        },
    )
    runner = ExperimentRunner(configuration)
    called: list[str] = []

    def _fail_inspect(dataset) -> tuple[str, ...]:
        called.append(dataset.key)
        raise AssertionError("inspect_columns não deveria ser chamado")

    monkeypatch.setattr(
        runner.dataset_loader,
        "inspect_columns",
        _fail_inspect,
    )
    report = runner.run_preflight()
    assert report.valid is True
    assert report.dataset_reports == ()
    assert called == []


def test_inspect_columns_jsonl_requests_nrows_one(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jsonl_path = tmp_path / "noticias.jsonl"
    jsonl_path.write_text(
        '{"id":"1","noticia":"a","data":"2024-01-01",'
        '"empresa":"Sabesp","setor":"saneamento","ticker":"SBSP3",'
        '"titulo":"t","sentimento":"neutro","fonte":"x","url":"u"}\n'
        '{"id":"2","noticia":"b","data":"2024-01-02",'
        '"empresa":"Sabesp","setor":"saneamento","ticker":"SBSP3",'
        '"titulo":"t2","sentimento":"positivo","fonte":"x","url":"u2"}\n',
        encoding="utf-8",
    )
    base = load_configuration(
        project_root=project_root,
        dataset_keys=["noticias_exemplo_ptbr"],
        model_keys=["finbert_ptbr"],
    ).get_dataset("noticias_exemplo_ptbr")
    dataset = replace(
        base,
        key="jsonl_sample",
        dataset_name="jsonl_sample",
        path=jsonl_path,
        format="jsonl",
    )

    captured: dict[str, object] = {}
    import modules.datasets.loader as loader_mod

    original = loader_mod.pd.read_json

    def _tracked_read_json(*args, **kwargs):
        captured.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(loader_mod.pd, "read_json", _tracked_read_json)
    columns = DatasetLoader().inspect_columns(dataset)
    assert captured.get("nrows") == 1
    assert "noticia" in columns or "text" in columns
