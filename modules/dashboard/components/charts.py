"""Gráficos Plotly padronizados."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.dashboard.components.chart_utils import current_chart_key
from modules.dashboard.config import RUN_COLORS

DEFAULT_HEIGHT = 420


def _plot(fig: go.Figure, *, height: int = DEFAULT_HEIGHT) -> None:
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, width="stretch", key=current_chart_key())


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
        color_discrete_sequence=RUN_COLORS,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    _plot(fig)


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
    _plot(fig, height=380)


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
    _plot(fig)


def heatmap(
    frame: pd.DataFrame,
    *,
    title: str = "",
) -> None:
    if frame.empty:
        st.caption("Sem dados para exibir.")
        return
    fig = px.imshow(frame, aspect="auto", title=title, color_continuous_scale="Blues")
    _plot(fig)


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
    _plot(fig)


def alpha_scatter(
    frame: pd.DataFrame,
    *,
    title: str = "Win rate em função de α (EWMA)",
) -> None:
    if frame.empty or "alpha" not in frame.columns or "win_rate" not in frame.columns:
        st.caption("Sem dados de α e win rate.")
        return
    data = frame.dropna(subset=["win_rate", "alpha"])
    if data.empty:
        st.caption("Sem dados de α e win rate.")
        return
    fig = px.scatter(
        data,
        x="alpha",
        y="win_rate",
        text="run_id" if "run_id" in data.columns else None,
        title=title,
        color_discrete_sequence=RUN_COLORS,
    )
    fig.update_traces(textposition="top center")
    _plot(fig)


def confusion_heatmap(
    matrix: pd.DataFrame,
    *,
    title: str = "Matriz de confusão",
) -> None:
    if matrix.empty:
        st.caption("Matriz de confusão indisponível.")
        return
    fig = px.imshow(
        matrix,
        aspect="auto",
        title=title,
        color_continuous_scale="Blues",
        text_auto=True,
    )
    _plot(fig)
