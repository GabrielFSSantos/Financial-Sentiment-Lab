"""Layout padrão das páginas."""

from __future__ import annotations

import streamlit as st


def page_header(title: str, description: str) -> None:
    st.title(title)
    st.markdown(f'<p class="fsl-page-desc">{description}</p>', unsafe_allow_html=True)


def section_header(title: str) -> None:
    st.markdown(f"### {title}")
