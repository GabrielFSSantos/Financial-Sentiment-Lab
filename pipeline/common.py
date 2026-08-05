"""Utilitários compartilhados entre os módulos da pipeline."""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Sequence, cast

import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CANONICAL_LABELS: tuple[str, ...] = (
    "NEGATIVE",
    "NEUTRAL",
    "POSITIVE",
)


class DataFrameAccessError(ValueError):
    """Indica coluna duplicada ou conversão numérica inválida."""


def is_missing_scalar(value: object) -> bool:
    """Retorna ``True`` somente para valores escalares ausentes."""

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
    """Converte valores comuns da pipeline para tipos JSON/YAML."""

    if value is None or value is pd.NA:
        return None

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, type):
        return f"{value.__module__}.{value.__name__}"

    if not isinstance(value, type) and is_dataclass(value):
        return to_serializable(asdict(cast(Any, value)))

    if isinstance(value, dict):
        return {
            str(key): to_serializable(item)
            for key, item in value.items()
        }

    mapping = getattr(value, "items", None)
    if callable(mapping) and not isinstance(value, (str, bytes)):
        try:
            return {
                str(key): to_serializable(item)
                for key, item in value.items()
            }
        except TypeError:
            pass

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


def deduplicate(values: Sequence[str]) -> list[str]:
    """Remove strings vazias e duplicatas preservando a ordem."""

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


def column_series(
    dataframe: pd.DataFrame,
    column: str,
) -> pd.Series:
    """Retorna uma Series garantindo que a coluna não esteja duplicada."""

    value = dataframe[column]
    if isinstance(value, pd.DataFrame):
        raise DataFrameAccessError(
            f"A coluna {column!r} aparece mais de uma vez."
        )
    return cast(pd.Series, value)


def numeric_series(
    series: pd.Series,
    *,
    errors: Literal["raise", "coerce"] = "coerce",
) -> pd.Series:
    """Converte uma Series para numérica."""

    converted = pd.to_numeric(series, errors=errors)
    if not isinstance(converted, pd.Series):
        raise DataFrameAccessError(
            "A conversão numérica não retornou uma Series."
        )
    return converted


def resolve_timezone(name: str) -> ZoneInfo:
    """Resolve um fuso horário IANA com fallback para UTC."""

    try:
        return ZoneInfo(str(name))
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def now_iso(
    *,
    timezone_name: str = "UTC",
) -> str:
    """Retorna o timestamp atual no fuso informado."""

    return datetime.now(resolve_timezone(timezone_name)).isoformat()


__all__ = [
    "CANONICAL_LABELS",
    "DataFrameAccessError",
    "column_series",
    "deduplicate",
    "is_missing_scalar",
    "now_iso",
    "numeric_series",
    "resolve_timezone",
    "to_serializable",
]
