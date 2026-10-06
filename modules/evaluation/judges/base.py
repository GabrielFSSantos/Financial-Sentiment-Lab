"""Label-judge plugin interface (e.g. LLM-as-judge)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class JudgePrediction:
    news_id: str
    label: str
    rationale: str
    judge_id: str
    prompt_version: str


class BaseLabelJudge(ABC):
    """Second opinion on news sentiment for a target company."""

    @abstractmethod
    def judge(self, texts: Sequence[tuple[str, str]]) -> list[JudgePrediction]:
        """Map (news_id, text) to predictions."""
