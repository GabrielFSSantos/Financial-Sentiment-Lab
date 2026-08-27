"""Cards de KPI."""

from __future__ import annotations

import streamlit as st


def kpi_row(items: list[tuple[str, str | int | float, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        with col:
            if isinstance(value, float) and 0 <= value <= 1:
                st.metric(label, f"{value:.1%}", delta=delta)
            else:
                st.metric(label, value, delta=delta)
