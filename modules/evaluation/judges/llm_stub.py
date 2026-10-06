"""Placeholder LLM judge — implement after qualification (see protocol §7)."""

from __future__ import annotations

from typing import Sequence

from modules.evaluation.judges.base import BaseLabelJudge, JudgePrediction


class LlmJudgeStub(BaseLabelJudge):
    """Raises if called; documents the intended integration point."""

    def judge(self, texts: Sequence[tuple[str, str]]) -> list[JudgePrediction]:
        raise NotImplementedError(
            "Juiz LLM ainda não implementado. Ver docs/tracking/annotation_protocol_v2.md "
            "e modules/evaluation/judges/base.py; backlog em docs/documentation/engineering_backlog.md."
        )
