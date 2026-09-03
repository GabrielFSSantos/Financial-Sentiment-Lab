"""Serviço de avaliação do classificador (bateria PT)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from modules.dashboard.config import CLASSIFIER_EVAL_DIR


@dataclass
class ClassifierModelResult:
    model_key: str
    accuracy: float | None
    cohen_kappa: float | None
    passes_gate: bool


@dataclass
class ClassifierEvalSummary:
    gate_accuracy: float
    gate_kappa: float
    models: list[ClassifierModelResult]
    winner: str | None
    finbert_confusion: pd.DataFrame | None
    comparative_report: str | None
    error_analysis_summary: dict[str, Any] | None


def _parse_confusion_from_report(path: Path) -> pd.DataFrame | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if "## Matriz de confusão" not in text:
        return None
    section = text.split("## Matriz de confusão", 1)[1].strip()
    lines = [ln for ln in section.splitlines() if ln.strip() and not ln.startswith("#")]
    if len(lines) < 2:
        return None
    header_line = lines[0].strip()
    if header_line.startswith("|"):
        header_line = header_line.strip("|")
    cols = [c.strip() for c in re.split(r"\s*\|\s*", header_line) if c.strip()]
    rows: list[list[str]] = []
    for line in lines[1:]:
        if "---" in line:
            continue
        clean = line.strip().strip("|")
        parts = [p.strip() for p in re.split(r"\s*\|\s*", clean) if p.strip()]
        if len(parts) >= 2:
            rows.append(parts)
    if not rows or not cols:
        return None
    index = [r[0] for r in rows]
    values = [[int(x) for x in r[1:]] for r in rows]
    try:
        return pd.DataFrame(values, index=index, columns=cols[: len(values[0])])
    except (ValueError, IndexError):
        return None


def load_classifier_eval(eval_dir: Path | None = None) -> ClassifierEvalSummary | None:
    base = eval_dir or CLASSIFIER_EVAL_DIR
    summary_path = base / "summary.json"
    if not summary_path.is_file():
        return None

    raw = json.loads(summary_path.read_text(encoding="utf-8"))
    models = [
        ClassifierModelResult(
            model_key=m["model_key"],
            accuracy=m.get("accuracy"),
            cohen_kappa=m.get("cohen_kappa"),
            passes_gate=bool(m.get("passes_gate")),
        )
        for m in raw.get("models") or []
    ]

    report_path = base / "comparative_report.md"
    comparative = report_path.read_text(encoding="utf-8") if report_path.is_file() else None

    error_path = base / "error_analysis_summary.json"
    error_summary = None
    if error_path.is_file():
        error_summary = json.loads(error_path.read_text(encoding="utf-8"))

    confusion = _parse_confusion_from_report(base / "finbert_ptbr_report.md")

    return ClassifierEvalSummary(
        gate_accuracy=float(raw.get("gate_accuracy", 0.7)),
        gate_kappa=float(raw.get("gate_kappa", 0.4)),
        models=models,
        winner=raw.get("winner"),
        finbert_confusion=confusion,
        comparative_report=comparative,
        error_analysis_summary=error_summary,
    )


def finbert_kappa(eval_dir: Path | None = None) -> float | None:
    summary = load_classifier_eval(eval_dir)
    if not summary:
        return None
    for model in summary.models:
        if model.model_key == "finbert_ptbr":
            return model.cohen_kappa
    return None


def finbert_accuracy(eval_dir: Path | None = None) -> float | None:
    summary = load_classifier_eval(eval_dir)
    if not summary:
        return None
    for model in summary.models:
        if model.model_key == "finbert_ptbr":
            return model.accuracy
    return None


def classifier_gate_passed(eval_dir: Path | None = None) -> bool:
    summary = load_classifier_eval(eval_dir)
    if not summary:
        return False
    return any(m.passes_gate for m in summary.models)
