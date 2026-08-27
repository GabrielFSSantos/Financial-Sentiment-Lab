"""Gráficos Plotly padronizados."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

COLORS = px.colors.qualitative.Set2


def horizontal_bar(
    frame: pd.DataFrame,
    x: str,
    y: str,
    *,
    title: str = "",
    top_n: int | None = 15,
) -> None:
    if frame.empty:
        st.caption("Sem dados para exibir.")
        return
    data = frame.head(top_n) if top_n else frame
    fig = px.bar(
        data,
        x=x,
        y=y,
        orientation="h",
        title=title,
        color_discrete_sequence=COLORS,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, width="stretch")


def time_series(
    frame: pd.DataFrame,
    x: str,
    y: str,
    *,
    title: str = "",
    color: str | None = None,
) -> None:
    if frame.empty:
        st.caption("Sem dados para exibir.")
        return
    fig = px.line(frame, x=x, y=y, color=color, title=title, markers=True)
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, width="stretch")


def grouped_bar(
    frame: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    *,
    title: str = "",
    barmode: str = "group",
) -> None:
    if frame.empty:
        st.caption("Sem dados para exibir.")
        return
    fig = px.bar(frame, x=x, y=y, color=color, barmode=barmode, title=title)
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")


def heatmap(
    frame: pd.DataFrame,
    *,
    title: str = "",
) -> None:
    if frame.empty:
        st.caption("Sem dados para exibir.")
        return
    fig = px.imshow(frame, aspect="auto", title=title, color_continuous_scale="Blues")
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch")


def scatter_plot(
    frame: pd.DataFrame,
    x: str,
    y: str,
    *,
    title: str = "",
    color: str | None = None,
    hover_data: list[str] | None = None,
) -> None:
    if frame.empty:
        st.caption("Sem dados para exibir.")
        return
    fig = px.scatter(frame, x=x, y=y, color=color, hover_data=hover_data, title=title)
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")
