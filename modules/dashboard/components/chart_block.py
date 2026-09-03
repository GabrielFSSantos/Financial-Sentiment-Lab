"""Bloco de gráfico com título e explicação."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from modules.dashboard.components.chart_utils import chart_context
from modules.dashboard.content.chart_help import CHART_HELP
from modules.dashboard.content.pt_br import HELP_EXPANDER


def chart_block(
    help_key: str,
    title: str,
    render_fn: Callable[[], None],
    *,
    chart_id: str | None = None,
) -> None:
    st.markdown(f"#### {title}")
    help_text = CHART_HELP.get(help_key, "")
    if help_text.strip():
        with st.expander(HELP_EXPANDER, expanded=False):
            st.markdown(help_text.strip())
    key = chart_id or f"chart_{help_key}_{title}".replace(" ", "_").lower()
    with chart_context(key):
        render_fn()
