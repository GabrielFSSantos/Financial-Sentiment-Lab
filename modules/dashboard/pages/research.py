"""Módulo Research — validação ITI vs mercado."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.chart_block import chart_block
from modules.dashboard.components.charts import grouped_bar, heatmap, scatter_plot, time_series
from modules.dashboard.components.filters import init_session_state, run_selector
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header
from modules.dashboard.components.metric_card import metric_row
from modules.dashboard.components.states import empty_state, unavailable_data
from modules.dashboard.content.pt_br import (
    EXPLORATORY_CALLOUT,
    TAB_INCREMENTAL,
    TAB_ITI_MARKET,
    TAB_PANORAMA,
    TAB_RAW_METRICS,
    TAB_SERIES,
)
from modules.dashboard.content.value_labels import horizon_label
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.classifier import classifier_gate_passed
from modules.dashboard.services.models import list_combinations
from modules.dashboard.services.research import (
    extract_win_rate,
    load_aligned_panel,
    load_baselines_daily,
    load_incremental_deltas,
    load_iti_daily,
    load_market_metrics,
    load_research_summary,
)


def render() -> None:
    init_session_state()
    page_header(
        "Research",
        "Validação analítica: ITI vs baselines e mercado. Drill-down geral → empresa → período.",
    )

    run_id = run_selector()
    if not run_id:
        unavailable_data("runs")
        return

    summary = load_research_summary(run_id)
    if not summary:
        unavailable_data(
            "research desta run",
            how_to=f"./scripts/run_research.sh --run-id {run_id}",
        )
        return

    combos = list_combinations(run_id)
    if not combos:
        empty_state("Nenhuma combinação com índices.")
        return

    combo_labels = [f"{c['model_key']} × {c['dataset_key']}" for c in combos]
    idx = st.selectbox("Combinação", range(len(combo_labels)), format_func=lambda i: combo_labels[i])
    combo = combos[idx]
    model_key = combo["model_key"]
    dataset_key = combo["dataset_key"]

    win_rate = extract_win_rate(summary)
    combo_info = (summary.get("combinations") or [{}])[0]
    overlap = combo_info.get("overlap_days")
    predictor = combo_info.get("predictor_stats") or {}
    sig_wins = predictor.get("significant_wins") or predictor.get("wins_significant")

    panel = load_aligned_panel(run_id, model_key, dataset_key)
    companies = sorted(panel["company"].dropna().unique()) if not panel.empty and "company" in panel.columns else []
    horizons = [1, 2, 4]
    if not panel.empty:
        hcols = [c for c in panel.columns if c.startswith("future_log_return_")]
        if hcols:
            horizons = sorted(int(c.split("_")[-1]) for c in hcols)

    tab_panorama, tab_market, tab_incremental, tab_series, tab_raw = st.tabs(
        [TAB_PANORAMA, TAB_ITI_MARKET, TAB_INCREMENTAL, TAB_SERIES, TAB_RAW_METRICS]
    )

    with tab_panorama:
        st.markdown(f'<div class="fsl-callout-warning">{EXPLORATORY_CALLOUT}</div>', unsafe_allow_html=True)
        render_insights(
            insights_engine.generate(
                {
                    "page": "research",
                    "win_rate": win_rate,
                    "overlap_days": overlap,
                    "classifier_gate_failed": not classifier_gate_passed(),
                    "significant_wins": sig_wins,
                }
            )
        )
        st.write(summary.get("conclusion", ""))
        metric_row(
            [
                ("win_rate", win_rate, True),
                ("overlap_weeks", float(overlap) if overlap is not None else None, False),
                ("significant_wins", float(sig_wins) if sig_wins is not None else None, False),
            ]
        )

    with tab_market:
        selected_company = st.selectbox("Empresa", ["Todas"] + companies, key="research_company")
        horizon = st.selectbox(
            "Horizonte",
            horizons,
            format_func=horizon_label,
            key="research_horizon",
        )
        future_col = f"future_log_return_{horizon}"
        subset = panel.copy()
        if selected_company != "Todas" and "company" in subset.columns:
            subset = subset[subset["company"] == selected_company]
        if not subset.empty and future_col in subset.columns and "iti_liquido" in subset.columns:
            chart_block(
                "iti_vs_return",
                f"ITI vs retorno futuro ({horizon_label(horizon)})",
                lambda: scatter_plot(
                    subset.dropna(subset=[future_col, "iti_liquido"]),
                    x="iti_liquido",
                    y=future_col,
                    color="company" if selected_company == "Todas" and "company" in subset.columns else None,
                    hover_data=["date"] if "date" in subset.columns else None,
                ),
            )
        else:
            empty_state("aligned_panel.csv indisponível ou colunas ausentes.")

    with tab_incremental:
        deltas = load_incremental_deltas(run_id, model_key, dataset_key)
        if not deltas.empty:
            st.dataframe(deltas.head(50), width="stretch", hide_index=True)
            if "delta" in deltas.columns and "baseline" in deltas.columns:
                chart_block(
                    "incremental_delta",
                    "Delta médio ITI − baseline",
                    lambda: grouped_bar(
                        deltas.groupby("baseline")["delta"].mean().reset_index(),
                        x="baseline",
                        y="delta",
                        color="baseline",
                    ),
                )
        else:
            empty_state("incremental_deltas.csv não disponível.")

    with tab_series:
        iti = load_iti_daily(run_id, model_key, dataset_key)
        baselines = load_baselines_daily(run_id, model_key, dataset_key)
        company_filter = st.selectbox("Empresa (séries)", ["Todas"] + companies, key="research_series_co")
        if not iti.empty:
            iti_sub = iti.copy()
            if company_filter != "Todas":
                iti_sub = iti_sub[iti_sub["company"] == company_filter]
            daily = iti_sub.groupby("date")["iti_liquido"].mean().reset_index()
            chart_block(
                "iti_daily",
                "ITI líquido diário",
                lambda: time_series(daily, x="date", y="iti_liquido"),
            )
        if not baselines.empty and "b1_mean_sentiment" in baselines.columns:
            bl = baselines.copy()
            if company_filter != "Todas":
                bl = bl[bl["company"] == company_filter]
            daily_b = bl.groupby("date")["b1_mean_sentiment"].mean().reset_index()
            chart_block(
                "iti_daily",
                "Baseline B1 (sentimento médio)",
                lambda: time_series(daily_b, x="date", y="b1_mean_sentiment"),
            )

    with tab_raw:
        market = load_market_metrics(run_id, model_key, dataset_key)
        if not market.empty:
            st.dataframe(market, width="stretch", hide_index=True)
            if {"series", "metric", "value"}.issubset(market.columns):
                pivot = market.pivot_table(
                    index=["series", "horizon"],
                    columns="metric",
                    values="value",
                    aggfunc="first",
                )
                if not pivot.empty:
                    chart_block(
                        "market_metrics_heatmap",
                        "Baseline × métrica × horizonte",
                        lambda: heatmap(pivot),
                    )
        else:
            st.caption("market_metrics.csv indisponível.")
