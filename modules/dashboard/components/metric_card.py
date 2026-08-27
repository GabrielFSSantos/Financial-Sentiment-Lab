"""Card de métrica com explicação."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.metrics.catalog import get_metric, interpret_value


def metric_card(key: str, value: float | None, *, format_pct: bool = False) -> None:
    info = get_metric(key)
    if not info:
        st.metric(key, value)
        return

    display = f"{value:.1%}" if format_pct and value is not None else (f"{value:.3f}" if isinstance(value, float) else value)
    st.metric(info.label, display)
    interpretation = interpret_value(key, value) if value is not None else info.description
    with st.expander("O que significa?"):
        st.markdown(f"**{info.label}**")
        st.write(info.description)
        st.write(interpretation)
