"""Bloco de seção com título e ajuda padronizada."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import streamlit as st

from modules.dashboard.content.chart_help import CHART_HELP
from modules.dashboard.content.pt_br import HELP_EXPANDER


@contextmanager
def section_block(
    title: str,
    help_key: str | None = None,
    *,
    intro: str | None = None,
) -> Iterator[None]:
    st.markdown(f"#### {title}")
    if intro:
        st.markdown(intro)
    if help_key:
        help_text = CHART_HELP.get(help_key, "")
        if help_text.strip():
            with st.expander(HELP_EXPANDER, expanded=False):
                st.markdown(help_text.strip())
    yield
