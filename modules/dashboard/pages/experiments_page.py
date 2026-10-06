"""Módulo Experimentos — campanha Sabesp."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.dashboard.components.chart_block import chart_block
from modules.dashboard.components.charts import alpha_scatter, grouped_bar
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header
from modules.dashboard.components.states import empty_state
from modules.dashboard.content.pt_br import TAB_ABLATIONS, TAB_ALPHA, TAB_CAMPAIGN
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

    tab_campaign, tab_alpha, tab_ablations = st.tabs([TAB_CAMPAIGN, TAB_ALPHA, TAB_ABLATIONS])

    with tab_campaign:
        st.write(f"**Campanha:** {manifest.get('campaign')}")
        st.write(f"**Baseline:** {manifest.get('baseline_run_id')}")
        st.write(manifest.get("description", ""))
        if not df.empty:
            display = df.copy()
            if "win_rate" in display.columns:
                display["win_rate"] = display["win_rate"].apply(
                    lambda v: f"{v:.1%}" if pd.notna(v) else "—"
                )
            if "hypothesis" in display.columns:
                display = display.rename(columns={"hypothesis": "Hipótese"})
            st.dataframe(display, width="stretch", hide_index=True)

        run_ids = df["run_id"].tolist() if "run_id" in df.columns else []
        selected = st.selectbox("Selecionar run para detalhe", run_ids)
        if selected:
            st.session_state.selected_run_id = selected
            st.info(f"Run `{selected}` selecionada. Abra **Runs** no menu para detalhes.")

    with tab_alpha:
        alpha_runs = df[df["run_id"].str.contains("alpha|r0_baseline", regex=True, na=False)].copy()
        if not alpha_runs.empty and "alpha" in alpha_runs.columns:
            chart_block(
                "alpha_vs_winrate",
                "Win rate vs α (EWMA)",
                lambda: alpha_scatter(alpha_runs.dropna(subset=["win_rate", "alpha"])),
            )
        else:
            empty_state("Runs com parâmetro α não encontradas.")

    with tab_ablations:
        ablations = df[~df["run_id"].str.contains("alpha|r9_ensemble|r8_weekly", regex=True, na=False)]
        ablations = ablations[ablations["run_id"] != "sabesp_r0_baseline"]
        if not ablations.empty and "win_rate" in ablations.columns:
            chart_block(
                "ablation_bars",
                "Win rate — ablações de variáveis",
                lambda: grouped_bar(
                    ablations.dropna(subset=["win_rate"]),
                    x="run_id",
                    y="win_rate",
                    color="run_id",
                ),
            )
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
