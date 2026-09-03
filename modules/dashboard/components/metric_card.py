"""Card de métrica com explicação."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.content.pt_br import HELP_EXPANDER
from modules.dashboard.metrics.catalog import get_metric, interpret_value


def _format_value(value: float | int | None, *, format_pct: bool = False) -> str:
    if value is None:
        return "—"
    if format_pct:
        return f"{float(value):.1%}"
    if isinstance(value, int) or (isinstance(value, float) and value == int(value) and abs(value) >= 100):
        return f"{int(value):,}".replace(",", ".")
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def metric_card(
    key: str,
    value: float | int | None,
    *,
    format_pct: bool = False,
) -> None:
    info = get_metric(key)
    label = info.label if info else key
    st.metric(label, _format_value(value, format_pct=format_pct))
    if info:
        with st.expander(HELP_EXPANDER, expanded=False):
            st.markdown(info.description)
            st.markdown(info.interpretation_guide)
            if value is not None and isinstance(value, (int, float)):
                band = interpret_value(key, float(value))
                if band:
                    st.markdown(band)


def metric_row(items: list[tuple[str, float | int | None, bool]]) -> None:
    """Renderiza uma linha de metric_cards: (catalog_key, value, format_pct)."""
    if not items:
        return
    cols = st.columns(len(items))
    for col, (key, value, fmt_pct) in zip(cols, items, strict=True):
        with col:
            metric_card(key, value, format_pct=fmt_pct)
