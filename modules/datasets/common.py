"""Utilitários compartilhados do módulo de datasets."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from modules.models.sentiment import CANONICAL_SENTIMENT_LABELS


ASSET_FETCH_HINT = (
    " Execute ./scripts/setup_env.sh --fetch-assets para baixar."
)

CANONICAL_LABELS = CANONICAL_SENTIMENT_LABELS


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
    "ASSET_FETCH_HINT",
    "CANONICAL_LABELS",
    "is_missing_scalar",
    "to_serializable",
]
