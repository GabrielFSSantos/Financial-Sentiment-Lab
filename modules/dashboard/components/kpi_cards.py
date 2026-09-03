"""Cards de KPI — usa catálogo de métricas quando disponível."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.metric_card import metric_row


def kpi_row(items: list[tuple[str, str | int | float, str | None]]) -> None:
    """Linha de KPIs simples (label, valor, delta). Usa st.metric direto."""
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        with col:
            if isinstance(value, float) and 0 <= value <= 1 and "%" not in str(label).lower():
                st.metric(label, f"{value:.1%}", delta=delta)
            else:
                st.metric(label, value, delta=delta)


def catalog_kpi_row(items: list[tuple[str, float | int | None, bool]]) -> None:
    """Linha de KPIs com explicação via catálogo (catalog_key, value, format_pct)."""
    metric_row(items)


def mixed_kpi_row(
    catalog_items: list[tuple[str, float | int | None, bool]] | None = None,
    simple_items: list[tuple[str, str | int | float, str | None]] | None = None,
) -> None:
    """Combina métricas do catálogo e KPIs simples na mesma linha."""
    catalog_items = catalog_items or []
    simple_items = simple_items or []
    total = len(catalog_items) + len(simple_items)
    if total == 0:
        return
    cols = st.columns(total)
    idx = 0
    for key, value, fmt_pct in catalog_items:
        with cols[idx]:
            from modules.dashboard.components.metric_card import metric_card

            metric_card(key, value, format_pct=fmt_pct)
        idx += 1
    for label, value, delta in simple_items:
        with cols[idx]:
            if isinstance(value, float) and 0 <= value <= 1:
                st.metric(label, f"{value:.1%}", delta=delta)
            else:
                st.metric(label, value, delta=delta)
        idx += 1
