"""Contrato de juízes de rótulo (LLM-as-judge)."""

from __future__ import annotations

import pytest

from modules.evaluation.judges.base import JudgePrediction
from modules.evaluation.judges.llm_stub import LlmJudgeStub


@pytest.mark.contract
def test_judge_prediction_fields() -> None:
    item = JudgePrediction(
        news_id="n1",
        label="POSITIVE",
        rationale="unit",
        judge_id="stub",
        prompt_version="v0",
    )
    assert item.news_id == "n1"
    assert item.label == "POSITIVE"


@pytest.mark.contract
def test_llm_judge_stub_raises_not_implemented() -> None:
    judge = LlmJudgeStub()
    with pytest.raises(NotImplementedError, match="Juiz LLM"):
        judge.judge([("n1", "texto de teste")])
