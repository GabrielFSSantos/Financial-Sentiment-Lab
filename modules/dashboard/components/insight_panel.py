"""Painel de insights automáticos."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.insights.rules import Insight, InsightLevel


def render_insights(insights: list[Insight], *, title: str = "Insights") -> None:
    if not insights:
        return
    st.markdown(f"### {title}")
    for insight in insights:
        css = "fsl-insight"
        if insight.level == InsightLevel.WARNING:
            css += " fsl-insight-warning"
        elif insight.level == InsightLevel.SUCCESS:
            css += " fsl-insight-success"
        elif insight.level == InsightLevel.DANGER:
            css += " fsl-insight-danger"
        st.markdown(f'<div class="{css}">{insight.message}</div>', unsafe_allow_html=True)
