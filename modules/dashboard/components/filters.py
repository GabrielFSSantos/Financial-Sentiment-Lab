"""Filtros compartilhados."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from modules.dashboard.services.catalog import RunSummary, list_runs


def init_session_state() -> None:
    if "selected_run_id" not in st.session_state:
        runs = list_runs()
        st.session_state.selected_run_id = runs[0].run_id if runs else None


def run_selector(*, label: str = "Run", key: str = "run_filter") -> str | None:
    runs = list_runs()
    if not runs:
        return None
    options = [r.run_id for r in runs]
    default = st.session_state.get("selected_run_id")
    if default not in options:
        default = options[0]
    selected = st.selectbox(label, options, index=options.index(default), key=key)
    st.session_state.selected_run_id = selected
    return selected


def date_range_filter(
    frame: pd.DataFrame,
    *,
    key_prefix: str = "date",
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if frame.empty or "date" not in frame.columns:
        return None, None
    dates = frame["date"].dropna()
    if dates.empty:
        return None, None
    min_d = dates.min().date()
    max_d = dates.max().date()
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("De", value=min_d, min_value=min_d, max_value=max_d, key=f"{key_prefix}_from")
    with col2:
        end = st.date_input("Até", value=max_d, min_value=min_d, max_value=max_d, key=f"{key_prefix}_to")
    return pd.Timestamp(start), pd.Timestamp(end)


def multiselect_from_column(
    frame: pd.DataFrame,
    column: str,
    *,
    label: str,
    key: str,
) -> list[str]:
    if frame.empty or column not in frame.columns:
        return []
    options = sorted(frame[column].dropna().astype(str).unique())
    return st.multiselect(label, options, key=key)
