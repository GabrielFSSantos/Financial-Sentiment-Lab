"""Resolução das dimensões m,r,e,u,q,h do ITI."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Mapping

import numpy as np
import pandas as pd

from modules.experiment.indexing.constants import DIMENSION_KEYS, DIMENSION_SHORT_NAMES

DEFAULT_PROVIDER_ORDER: tuple[str, ...] = (
    "dataset_columns",
    "prediction_metadata",
    "heuristics",
    "defaults",
)

_SHORT_TO_LONG = {short: long for long, short in DIMENSION_SHORT_NAMES.items()}
_LONG_TO_SHORT = DIMENSION_SHORT_NAMES

_RISK_KEYWORDS = (
    "multa",
    "risco",
    "investiga",
    "fraude",
    "crise",
    "default",
    "downgrade",
)
_SHORT_HORIZON_KEYWORDS = ("curto prazo", "imediato", "hoje", "esta semana")
_LONG_HORIZON_KEYWORDS = ("plano plurianual", "longo prazo", "próximos anos", "decênio")


def resolve_dimensions(
    frame: pd.DataFrame,
    *,
    settings: Mapping[str, Any],
    defaults: Mapping[str, float],
    seen_titles: set[str] | None = None,
) -> dict[str, pd.Series]:
    dimension_settings = dict(settings.get("dimensions") or {})
    provider_order = tuple(
        str(item).strip()
        for item in dimension_settings.get("provider_order", DEFAULT_PROVIDER_ORDER)
        if str(item).strip()
    )
    heuristics_settings = dict(dimension_settings.get("heuristics") or {})
    event_keywords = dict(heuristics_settings.get("event_keywords") or _default_event_keywords())

    resolved: dict[str, pd.Series] = {
        key: pd.Series(float(defaults[key]), index=frame.index, dtype=float)
        for key in DIMENSION_KEYS
    }

    for provider in provider_order:
        if provider == "dataset_columns":
            _apply_dataset_columns(frame, resolved)
        elif provider == "prediction_metadata":
            _apply_prediction_metadata(frame, resolved)
        elif provider == "heuristics" and heuristics_settings.get("enabled", True):
            _apply_heuristics(
                frame,
                resolved,
                event_keywords=event_keywords,
                seen_titles=seen_titles or set(),
            )
        elif provider == "defaults":
            continue

    for key in DIMENSION_KEYS:
        short = _LONG_TO_SHORT[key]
        resolved[key] = _clip_dimension(resolved[key])
        if short in frame.columns:
            frame[short] = resolved[key]
    return resolved


def _default_event_keywords() -> dict[str, tuple[str, ...]]:
    return {
        "regulacao": ("regulat", "aneel", "ana", "arsesp", "agepar", "multa"),
        "investimento": ("invest", "capex", "obras", "expansão", "expansao"),
        "tarifa": ("tarifa", "reajuste", "precific"),
        "privatizacao": ("privatiz", "concess", "leilão", "leilao"),
    }


def _apply_dataset_columns(
    frame: pd.DataFrame,
    resolved: dict[str, pd.Series],
) -> None:
    for key in DIMENSION_KEYS:
        short = _LONG_TO_SHORT[key]
        if short in frame.columns:
            resolved[key] = _numeric_series(frame[short], fallback=resolved[key])
            continue
        if key in frame.columns:
            resolved[key] = _numeric_series(frame[key], fallback=resolved[key])


def _apply_prediction_metadata(
    frame: pd.DataFrame,
    resolved: dict[str, pd.Series],
) -> None:
    if "prediction_metadata" not in frame.columns:
        return

    aliases_by_key = {
        key: {key, _LONG_TO_SHORT[key], key.replace("_", "")}
        for key in DIMENSION_KEYS
    }

    for index, raw_metadata in frame["prediction_metadata"].items():
        metadata = _parse_metadata(raw_metadata)
        if not metadata:
            continue
        for key, aliases in aliases_by_key.items():
            for alias in aliases:
                if alias in metadata:
                    try:
                        resolved[key].at[index] = float(metadata[alias])
                    except (TypeError, ValueError):
                        pass
                    break


def _apply_heuristics(
    frame: pd.DataFrame,
    resolved: dict[str, pd.Series],
    *,
    event_keywords: Mapping[str, tuple[str, ...]],
    seen_titles: set[str],
) -> None:
    titles = _text_series(frame, "title")
    bodies = _text_series(frame, "text")
    companies = _text_series(frame, "company")
    tickers = _text_series(frame, "ticker")
    sentiments = _numeric_series(frame.get("continuous_sentiment"), fallback=0.0)
    confidences = _numeric_series(frame.get("confidence"), fallback=0.5)

    for index in frame.index:
        title = titles.at[index]
        body = bodies.at[index]
        haystack = f"{title} {body}".lower()
        if not haystack.strip():
            continue
        company = companies.at[index].lower()
        ticker = tickers.at[index].lower()

        if ticker and ticker in haystack:
            resolved["relevance"].at[index] = max(resolved["relevance"].at[index], 1.0)
        elif company and company in haystack:
            resolved["relevance"].at[index] = max(resolved["relevance"].at[index], 0.85)
        elif company:
            resolved["relevance"].at[index] = max(resolved["relevance"].at[index], 0.65)

        magnitude = min(2.0, abs(float(sentiments.at[index])) * float(confidences.at[index]) + 0.15)
        resolved["magnitude"].at[index] = max(resolved["magnitude"].at[index], magnitude)

        event_weight = 1.0
        for keywords in event_keywords.values():
            if any(keyword in haystack for keyword in keywords):
                event_weight = max(event_weight, 1.15)
        resolved["event_weight"].at[index] = max(resolved["event_weight"].at[index], event_weight)

        normalized_title = re.sub(r"\s+", " ", title.strip().lower())
        if normalized_title and normalized_title not in seen_titles:
            resolved["novelty"].at[index] = max(resolved["novelty"].at[index], 1.0)
            seen_titles.add(normalized_title)
        elif normalized_title:
            resolved["novelty"].at[index] = min(resolved["novelty"].at[index], 0.75)

        if any(keyword in haystack for keyword in _RISK_KEYWORDS) or float(sentiments.at[index]) < 0:
            resolved["risk"].at[index] = max(resolved["risk"].at[index], 1.1)

        if any(keyword in haystack for keyword in _SHORT_HORIZON_KEYWORDS):
            resolved["horizon"].at[index] = min(resolved["horizon"].at[index], 0.75)
        elif any(keyword in haystack for keyword in _LONG_HORIZON_KEYWORDS):
            resolved["horizon"].at[index] = max(resolved["horizon"].at[index], 1.25)


def _parse_metadata(value: Any) -> dict[str, Any]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return dict(parsed)
    return {}


def _text_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype=str)
    return frame[column].fillna("").astype(str)


def _numeric_series(series: Any, *, fallback: float | pd.Series) -> pd.Series:
    if series is None:
        if isinstance(fallback, pd.Series):
            return fallback.copy()
        return pd.Series(float(fallback), dtype=float)
    converted = pd.to_numeric(series, errors="coerce")
    if isinstance(fallback, pd.Series):
        return converted.fillna(fallback)
    return converted.fillna(float(fallback))


def _clip_dimension(series: pd.Series, *, minimum: float = 0.05, maximum: float = 2.0) -> pd.Series:
    return series.clip(lower=minimum, upper=maximum)
