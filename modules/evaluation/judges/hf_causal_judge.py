"""Hugging Face causal LM as fixed-prompt label judge."""

from __future__ import annotations

import os
from typing import Callable, Sequence

from modules.evaluation.judges.base import BaseLabelJudge, JudgePrediction
from modules.evaluation.judges.prompts import format_prompt_v1_quali
from modules.evaluation.judges.response_parser import parse_classe_justificativa

GenerateFn = Callable[[str], str]


class HfCausalLabelJudge(BaseLabelJudge):
    """Run prompt_v1_quali through a causal LM (or injected generator for tests)."""

    def __init__(
        self,
        *,
        model_id: str,
        prompt_version: str = "prompt_v1_quali",
        judge_id: str | None = None,
        max_new_tokens: int = 128,
        generate_fn: GenerateFn | None = None,
        mock: bool = False,
    ) -> None:
        self.model_id = model_id
        self.prompt_version = prompt_version
        self.judge_id = judge_id or model_id
        self.max_new_tokens = max_new_tokens
        self._generate_fn = generate_fn
        self._mock = mock or os.environ.get("LLM_JUDGE_MOCK", "").strip() in {
            "1",
            "true",
            "yes",
        }
        self._pipeline = None

    def _ensure_pipeline(self) -> None:
        if self._generate_fn is not None or self._mock or self._pipeline is not None:
            return
        from transformers import pipeline

        self._pipeline = pipeline(
            "text-generation",
            model=self.model_id,
            device_map="auto",
        )

    def _generate(self, prompt: str) -> str:
        if self._mock:
            return (
                "CLASSE: NEUTRAL\n"
                "JUSTIFICATIVA: Resposta simulada (modo demonstração sem modelo carregado)."
            )
        if self._generate_fn is not None:
            return self._generate_fn(prompt)
        self._ensure_pipeline()
        if self._pipeline is None:
            raise RuntimeError("Pipeline não inicializado.")
        out = self._pipeline(
            prompt,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )
        return str(out[0]["generated_text"])

    def judge(
        self,
        texts: Sequence[tuple[str, str, str]],
    ) -> list[JudgePrediction]:
        """Map (news_id, title, body) to predictions."""
        results: list[JudgePrediction] = []
        for news_id, title, body in texts:
            prompt = format_prompt_v1_quali(title, body)
            raw = self._generate(prompt)
            label, rationale = parse_classe_justificativa(raw)
            results.append(
                JudgePrediction(
                    news_id=news_id,
                    label=label,
                    rationale=rationale,
                    judge_id=self.judge_id,
                    prompt_version=self.prompt_version,
                )
            )
        return results
