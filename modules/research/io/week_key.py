"""Chave canônica de semana civil W-FRI para junção sinal × mercado."""

from __future__ import annotations

import pandas as pd

WEEK_FREQ = "W-FRI"


def week_key_from_timestamp(value: object) -> pd.Timestamp | pd.NaT:
    """Normaliza instante para o fim da semana civil W-FRI (meia-noite)."""

    ts = pd.Timestamp(value)
    if pd.isna(ts):
        return pd.NaT
    return ts.to_period(WEEK_FREQ).end_time.normalize()


def week_key_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.apply(week_key_from_timestamp)


def _week_key_scalar(value: object) -> pd.Timestamp | pd.NaT:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    text = str(value).strip()
    if "/" in text:
        # ITI-v2: "YYYY-MM-DD/YYYY-MM-DD" com fim = sexta W-FRI (ver iti_weekly_signals.week_id).
        end_part = text.split("/")[-1].strip()
        try:
            return week_key_from_timestamp(end_part)
        except (ValueError, TypeError):
            pass
        try:
            return pd.Period(text, freq=WEEK_FREQ).end_time.normalize()
        except (ValueError, TypeError):
            pass
    return week_key_from_timestamp(value)


def week_key_from_week_id_column(series: pd.Series) -> pd.Series:
    """week_id do pipeline ITI costuma ser str(Period); market usa Timestamp em week_id."""

    return series.map(_week_key_scalar)


def week_key_to_iso_string(key: pd.Timestamp) -> str:
    if pd.isna(key):
        return ""
    return pd.Timestamp(key).date().isoformat()
