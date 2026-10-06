"""Load ``configs/evaluation.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.common.paths import CONFIGS_DIR, PROJECT_ROOT


class EvaluationConfigError(ValueError):
    """Invalid evaluation YAML."""


@dataclass(frozen=True)
class EvaluationSettings:
    manual_labels_path: Path
    manual_labels_exploratorio_path: Path | None
    strict_corpus_path: Path
    eval_joined_path: Path
    report_dir: Path
    gate_accuracy: float
    gate_kappa: float
    battery_models: tuple[str, ...]
    column_aliases: dict[str, tuple[str, ...]]
    llm_judge_output_csv: Path
    llm_judge_prompt_version: str
    llm_judge_model_id: str


def load_evaluation_settings(
    config_path: Path | None = None,
) -> EvaluationSettings:
    path = config_path or (CONFIGS_DIR / "evaluation.yaml")
    if not path.is_file():
        raise EvaluationConfigError(f"Missing evaluation config: {path}")

    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, Mapping):
        raise EvaluationConfigError(f"Root of {path} must be a mapping.")

    paths = raw.get("paths", {})
    if not isinstance(paths, Mapping):
        raise EvaluationConfigError("evaluation.paths must be a mapping.")

    gate = raw.get("classifier_gate", {})
    models = raw.get("classifier_battery_models", [])
    aliases = raw.get("column_aliases", {})
    llm = raw.get("llm_judge_pilot", {})

    def _p(key: str) -> Path:
        value = paths.get(key)
        if not value:
            raise EvaluationConfigError(f"evaluation.paths.{key} is required.")
        return (PROJECT_ROOT / str(value)).resolve()

    def _p_optional(key: str) -> Path | None:
        value = paths.get(key)
        if not value:
            return None
        return (PROJECT_ROOT / str(value)).resolve()

    alias_map: dict[str, tuple[str, ...]] = {}
    if isinstance(aliases, Mapping):
        for canonical, legacy in aliases.items():
            if isinstance(legacy, list):
                alias_map[str(canonical)] = tuple(str(item) for item in legacy)

    llm_out = PROJECT_ROOT / "outputs/campaigns/llm_judge_pilot/llm_judge_pilot.csv"
    llm_prompt = "prompt_v1_quali"
    llm_model = "mistralai/Mistral-7B-Instruct-v0.3"
    if isinstance(llm, Mapping):
        if llm.get("output_csv"):
            llm_out = (PROJECT_ROOT / str(llm["output_csv"])).resolve()
        if llm.get("prompt_version"):
            llm_prompt = str(llm["prompt_version"])
        if llm.get("model_id"):
            llm_model = str(llm["model_id"])

    return EvaluationSettings(
        manual_labels_path=_p("manual_labels"),
        manual_labels_exploratorio_path=_p_optional("manual_labels_exploratorio"),
        strict_corpus_path=_p("strict_corpus"),
        eval_joined_path=_p("eval_joined"),
        report_dir=_p("report_dir"),
        gate_accuracy=float(gate.get("accuracy", 0.70)),
        gate_kappa=float(gate.get("kappa", 0.40)),
        battery_models=tuple(str(m) for m in models) if models else (),
        column_aliases=alias_map,
        llm_judge_output_csv=llm_out,
        llm_judge_prompt_version=llm_prompt,
        llm_judge_model_id=llm_model,
    )
