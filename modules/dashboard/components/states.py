"""Estados vazios e mensagens de erro."""

from __future__ import annotations

import streamlit as st


def empty_state(message: str, *, hint: str | None = None) -> None:
    st.info(message)
    if hint:
        st.caption(hint)


def unavailable_data(what: str, *, how_to: str | None = None) -> None:
    st.warning(f"Dado indisponível: {what}")
    if how_to:
        st.code(how_to, language="bash")
