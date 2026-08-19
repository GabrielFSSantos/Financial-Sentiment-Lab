"""Utilitários compartilhados do módulo de research."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd


BASELINE_COLUMNS = {
    "b0": "b0_news_count",
    "b1": "b1_mean_sentiment",
    "b2": "b2_confidence_weighted_sentiment",
    "b3": "b3_daily_impact_no_memory",
}


def is_missing_scalar(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, type):
        return False
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, np.floating):
        return bool(np.isnan(value))
    if isinstance(value, np.datetime64):
        return bool(np.isnat(value))
    if isinstance(value, np.timedelta64):
        return bool(np.isnat(value))
    return False


def to_serializable(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, type):
        return f"{value.__module__}.{value.__name__}"
    if not isinstance(value, type) and is_dataclass(value):
        return to_serializable(asdict(cast(Any, value)))
    if isinstance(value, dict):
        return {
            str(key): to_serializable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        normalized = [to_serializable(item) for item in value]
        if isinstance(value, set):
            return sorted(normalized)
        return normalized
    if is_missing_scalar(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


__all__ = [
    "BASELINE_COLUMNS",
    "is_missing_scalar",
    "to_serializable",
]
