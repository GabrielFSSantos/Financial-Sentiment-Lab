"""Financial Sentiment Lab — Dashboard de exploração da pesquisa."""

from __future__ import annotations

import sys
from pathlib import Path

# Garante imports do projeto ao rodar via streamlit
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from modules.dashboard.config import THEME_CSS
from modules.dashboard.pages import (
    comparacao_runs,
    datasets_scraper,
    experimentos,
    modelos,
    research,
    runs,
    visao_geral,
)


def _load_css() -> None:
    if THEME_CSS.is_file():
        st.markdown(f"<style>{THEME_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Financial Sentiment Lab",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _load_css()

    pages = [
        st.Page(visao_geral.render, title="Visão Geral", icon="🏠", url_path="visao-geral", default=True),
        st.Page(datasets_scraper.render, title="Datasets e Scraper", icon="📰", url_path="datasets"),
        st.Page(modelos.render, title="Modelos", icon="🤖", url_path="modelos"),
        st.Page(runs.render, title="Runs", icon="▶️", url_path="runs"),
        st.Page(comparacao_runs.render, title="Comparação", icon="⚖️", url_path="comparacao"),
        st.Page(experimentos.render, title="Experimentos", icon="🧪", url_path="experimentos"),
        st.Page(research.render, title="Research", icon="🔬", url_path="research"),
    ]

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
