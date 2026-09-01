"""Testes de concordância de rótulos (manual_labels, classifier_eval)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from modules.evaluation.classifier_eval import (
    evaluate_predictions_frame,
    format_evaluation_report,
)
from modules.evaluation.classifier_eval_pt import (
    GATE_ACCURACY,
    GATE_KAPPA,
    build_eval_dataset,
    passes_gate,
    pick_winner,
)
from modules.evaluation.manual_labels import compare_manual_labels


def test_classifier_eval_accuracy_and_kappa() -> None:
    frame = pd.DataFrame(
        {
            "true_label": ["POSITIVE", "NEGATIVE", "NEUTRAL", "POSITIVE"],
            "predicted_label": ["POSITIVE", "NEGATIVE", "POSITIVE", "POSITIVE"],
        }
    )
    metrics = evaluate_predictions_frame(frame)
    assert metrics["n_labeled"] == 4
    assert metrics["accuracy"] == 0.75
    assert isinstance(metrics["cohen_kappa"], float)
    report = format_evaluation_report(metrics)
    assert "Cohen's kappa" in report


def test_manual_labels_compare_includes_kappa(tmp_path: Path) -> None:
    manual = tmp_path / "manual.csv"
    predictions = tmp_path / "predictions.csv"
    report = tmp_path / "report.md"

    manual.write_text(
        "news_id,rotulo_manual\n"
        "1,POS\n"
        "2,NEG\n"
        "3,NEU\n",
        encoding="utf-8",
    )
    predictions.write_text(
        "news_id,predicted_label\n"
        "1,POSITIVE\n"
        "2,NEGATIVE\n"
        "3,NEUTRAL\n",
        encoding="utf-8",
    )

    metrics = compare_manual_labels(
        manual,
        predictions,
        output_report=report,
    )
    assert metrics["accuracy"] == 1.0
    assert metrics["cohen_kappa"] == 1.0
    assert "Cohen's kappa" in report.read_text(encoding="utf-8")


def test_classifier_eval_requires_labels() -> None:
    frame = pd.DataFrame({"true_label": [""], "predicted_label": ["POSITIVE"]})
    with pytest.raises(ValueError, match="Nenhuma linha"):
        evaluate_predictions_frame(frame)


def test_build_eval_dataset_joins_corpus(project_root: Path) -> None:
    manual = project_root / "data/saneamento_corpus/rotulos_manual_100.csv"
    corpus = project_root / "data/saneamento_corpus/noticias_strict_sabesp.csv"
    if not manual.is_file() or not corpus.is_file():
        pytest.skip("Artefatos de rótulos manuais ausentes")
    output = project_root / "data/saneamento_corpus/rotulos_manual_100_eval.csv"
    path = build_eval_dataset(
        manual_path=manual,
        corpus_path=corpus,
        output_path=output,
    )
    frame = pd.read_csv(path)
    assert len(frame) == 100
    assert frame["noticia"].astype(str).str.len().gt(10).all()
    assert frame["rotulo_manual"].astype(str).str.strip().ne("").all()


def test_classifier_eval_pt_gate_logic() -> None:
    weak = {"accuracy": 0.48, "cohen_kappa": 0.163}
    strong = {"accuracy": 0.72, "cohen_kappa": 0.45}
    assert not passes_gate(weak)
    assert passes_gate(strong)
    winner = pick_winner(
        [
            {**weak, "model_key": "finbert_ptbr"},
            {**strong, "model_key": "bertimbau_sentiment"},
        ]
    )
    assert winner == "bertimbau_sentiment"
    assert GATE_ACCURACY == 0.70
    assert GATE_KAPPA == 0.40
