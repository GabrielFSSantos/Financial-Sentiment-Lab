"""Módulo Experimentos — campanha Sabesp."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.dashboard.components.charts import grouped_bar
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.states import empty_state
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.campaigns import (
    best_campaign_run,
    campaign_comparison_table,
    load_manifest,
)


def render() -> None:
    page_header(
        "Experimentos",
        "Campanha Sabesp R0–R9: hipóteses, parâmetros (alpha, equação) e resultados comparativos.",
    )

    manifest = load_manifest()
    if not manifest:
        empty_state(
            "Manifest da campanha não encontrado.",
            hint="outputs/campaigns/sabesp_2026/manifest.json",
        )
        return

    rows = campaign_comparison_table(manifest)
    df = pd.DataFrame(rows)
    best = best_campaign_run(manifest)
    best_rate = (best.get("metrics_summary") or {}).get("win_rate") if best else None

    render_insights(
        insights_engine.generate(
            {
                "page": "experiments",
                "best_run_id": best.get("run_id") if best else None,
                "best_win_rate": best_rate,
            }
        )
    )

    section_header("Resumo da campanha")
    st.write(f"**Campanha:** {manifest.get('campaign')}")
    st.write(f"**Baseline:** {manifest.get('baseline_run_id')}")
    st.write(manifest.get("description", ""))

    section_header("Tabela de runs")
    if not df.empty:
        display = df.copy()
        if "win_rate" in display.columns:
            display["win_rate"] = display["win_rate"].apply(
                lambda v: f"{v:.1%}" if pd.notna(v) else "—"
            )
        st.dataframe(display, width="stretch", hide_index=True)

    section_header("Win rate vs Alpha")
    alpha_runs = df[df["run_id"].str.contains("alpha|r0_baseline", regex=True)].copy()
    if not alpha_runs.empty and "alpha" in alpha_runs.columns:
        alpha_runs = alpha_runs.dropna(subset=["win_rate", "alpha"])
        if not alpha_runs.empty:
            fig = px.scatter(
                alpha_runs,
                x="alpha",
                y="win_rate",
                text="run_id",
                title="Win rate em função de α (EWMA)",
            )
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, width="stretch")

    section_header("Ablações vs baseline")
    ablations = df[~df["run_id"].str.contains("alpha|r9_ensemble|r8_weekly", regex=True)]
    ablations = ablations[ablations["run_id"] != "sabesp_r0_baseline"]
    if not ablations.empty and "win_rate" in ablations.columns:
        grouped_bar(
            ablations.dropna(subset=["win_rate"]),
            x="run_id",
            y="win_rate",
            color="run_id",
            title="Win rate — ablações de variáveis",
        )

    section_header("Destaques")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**R8 — ITI média semanal vs último dia**")
        r8 = df[df["run_id"] == "sabesp_r8_weekly_mean"]
        if not r8.empty:
            st.write(r8.iloc[0].to_dict())
    with col2:
        st.markdown("**R9 — Modelo alternativo PT-BR**")
        r9 = df[df["run_id"] == "sabesp_r9_ensemble"]
        if not r9.empty:
            st.write(r9.iloc[0].to_dict())

    section_header("Selecionar run para detalhe")
    run_ids = df["run_id"].tolist() if "run_id" in df.columns else []
    selected = st.selectbox("Run", run_ids)
    if selected:
        st.session_state.selected_run_id = selected
        st.info(f"Run `{selected}` selecionada. Abra o módulo **Runs** para detalhes completos.")
