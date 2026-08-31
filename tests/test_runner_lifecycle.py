"""Sinais restaurados na falha inicial e unload só ao trocar de modelo."""

from __future__ import annotations

import signal
from pathlib import Path

import pytest

from modules.experiment.config.loader import load_configuration
from modules.experiment.pipeline.runner import ExperimentRunner


def test_run_restores_signals_if_prepare_fails(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )
    runner = ExperimentRunner(configuration)
    original = signal.getsignal(signal.SIGINT)

    def _boom() -> None:
        raise RuntimeError("prepare falhou")

    monkeypatch.setattr(runner.results, "prepare", _boom)
    with pytest.raises(RuntimeError, match="prepare falhou"):
        runner.run()
    assert signal.getsignal(signal.SIGINT) == original


def test_release_keeps_model_when_next_key_matches(
    project_root: Path,
) -> None:
    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )
    runner = ExperimentRunner(configuration)
    calls: list[str] = []

    class _FakeRegistry:
        instantiated_keys = ("finbert_ptbr",)

        def unload(self, key: str, remove_instance: bool = True) -> None:
            del remove_instance
            calls.append(key)

    runner._registry = _FakeRegistry()  # type: ignore[assignment]
    runner._release_model_after_combination(
        "finbert_ptbr",
        next_model_key="finbert_ptbr",
    )
    assert calls == []
    runner._release_model_after_combination(
        "finbert_ptbr",
        next_model_key="other_model",
    )
    assert calls == ["finbert_ptbr"]
    runner._release_model_after_combination(
        "finbert_ptbr",
        next_model_key=None,
    )
    assert calls == ["finbert_ptbr", "finbert_ptbr"]


def test_loaded_dataset_texts_are_cached(project_root: Path) -> None:
    from modules.datasets.loader import DatasetLoader

    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )
    loaded = DatasetLoader().load(
        configuration.get_dataset("noticias_exemplo_ptbr")
    )
    first = loaded.texts
    second = loaded.texts
    assert first is second
    assert first


def test_execute_combinations_passes_shared_model_as_next_key(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    from modules.experiment.config.loader import ExperimentCombination
    from modules.experiment.pipeline.runner import CombinationRunResult

    configuration = load_configuration(
        project_root=project_root,
        model_keys=["finbert_ptbr"],
        dataset_keys=["noticias_exemplo_ptbr"],
    )
    base = configuration.combinations[0]
    second = ExperimentCombination(
        index=1,
        model_key=base.model_key,
        dataset_key="outro_dataset",
        combination_id=f"{base.model_key}__outro_dataset",
    )
    configuration = replace(
        configuration,
        combinations=(base, second),
    )
    runner = ExperimentRunner(configuration)
    captured: list[tuple[str, str | None]] = []

    def _fake_execute(
        combination: ExperimentCombination,
        *,
        next_model_key: str | None = None,
    ) -> CombinationRunResult:
        captured.append((combination.dataset_key, next_model_key))
        return CombinationRunResult(
            combination_id=combination.combination_id,
            model_key=combination.model_key,
            dataset_key=combination.dataset_key,
            status="success",
            duration_seconds=0.1,
            row_count=1,
            valid_text_count=1,
            device="cpu",
        )

    monkeypatch.setattr(
        runner,
        "_execute_combination",
        _fake_execute,
    )
    runner._execute_combinations()

    assert captured == [
        ("noticias_exemplo_ptbr", "finbert_ptbr"),
        ("outro_dataset", None),
    ]
