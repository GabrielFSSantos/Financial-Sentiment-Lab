"""Parser de respostas do juiz LLM."""

from __future__ import annotations

import pytest

from modules.evaluation.judges.hf_causal_judge import HfCausalLabelJudge
from modules.evaluation.judges.response_parser import parse_classe_justificativa


@pytest.mark.contract
def test_parse_classe_justificativa() -> None:
    raw = "CLASSE: POSITIVE\nJUSTIFICATIVA: Contrato favorável à Sabesp."
    label, rationale = parse_classe_justificativa(raw)
    assert label == "POSITIVE"
    assert "Contrato" in rationale


@pytest.mark.contract
def test_hf_judge_with_injected_generator() -> None:
    def _gen(_prompt: str) -> str:
        return "CLASSE: NEGATIVE\nJUSTIFICATIVA: Multa regulatória."

    judge = HfCausalLabelJudge(
        model_id="test-model",
        generate_fn=_gen,
    )
    out = judge.judge([("n1", "Título", "Corpo")])
    assert out[0].label == "NEGATIVE"
    assert out[0].news_id == "n1"
