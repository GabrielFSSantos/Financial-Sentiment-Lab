"""Testes do serviço de classificador."""

from __future__ import annotations

from modules.dashboard.services.classifier import (
    classifier_gate_passed,
    finbert_accuracy,
    finbert_kappa,
    load_classifier_eval,
)


def test_load_classifier_eval_from_outputs() -> None:
    summary = load_classifier_eval()
    if summary is None:
        return
    assert summary.gate_kappa == 0.4
    assert len(summary.models) >= 1
    finbert = next(m for m in summary.models if m.model_key == "finbert_ptbr")
    assert finbert.accuracy is not None
    assert finbert.cohen_kappa is not None


def test_finbert_metrics() -> None:
    kappa = finbert_kappa()
    accuracy = finbert_accuracy()
    if kappa is None:
        return
    assert 0 <= kappa <= 1
    assert accuracy is not None
    assert not classifier_gate_passed()
