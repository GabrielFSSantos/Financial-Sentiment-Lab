"""Utilitários compartilhados para gráficos Plotly."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import streamlit as st

from modules.dashboard.config import BASELINE_COLORS, RUN_COLORS

_chart_key_stack: list[str] = []


def _next_auto_key() -> str:
    if "chart_key_counter" not in st.session_state:
        st.session_state.chart_key_counter = 0
    st.session_state.chart_key_counter += 1
    return f"chart_auto_{st.session_state.chart_key_counter}"


@contextmanager
def chart_context(chart_id: str) -> Iterator[None]:
    _chart_key_stack.append(chart_id)
    try:
        yield
    finally:
        _chart_key_stack.pop()


def current_chart_key() -> str:
    return _chart_key_stack[-1] if _chart_key_stack else _next_auto_key()


def run_color(i: int) -> str:
    return RUN_COLORS[i % len(RUN_COLORS)]


def baseline_color(key: str) -> str:
    normalized = key.strip().lower()
    if normalized in BASELINE_COLORS:
        return BASELINE_COLORS[normalized]
    if normalized.startswith("b") and len(normalized) >= 2:
        return BASELINE_COLORS.get(normalized[:2], RUN_COLORS[0])
    return RUN_COLORS[0]


def format_percent(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def format_count(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")
