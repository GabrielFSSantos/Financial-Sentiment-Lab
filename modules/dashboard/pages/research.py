"""Módulo Research — validação ITI vs mercado."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.dashboard.components.charts import grouped_bar, heatmap, scatter_plot, time_series
from modules.dashboard.components.filters import init_session_state, run_selector
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.metric_card import metric_card
from modules.dashboard.components.states import empty_state, unavailable_data
from modules.dashboard.insights import engine as insights_engine
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

    render_insights(
        insights_engine.generate(
            {"page": "research", "win_rate": win_rate, "overlap_days": overlap}
        )
    )

    section_header("Resumo")
    st.write(summary.get("conclusion", ""))
    if win_rate is not None:
        metric_card("win_rate", win_rate, format_pct=True)

    with st.expander("O que é vitória incremental?"):
        st.markdown(
            "Compara correlação do ITI com retornos futuros contra baselines B0–B2. "
            "Uma **vitória** ocorre quando o ITI supera o baseline na mesma métrica e horizonte. "
            "Não implica causalidade — apenas associação estatística."
        )

    section_header("Filtros de drill-down")
    panel = load_aligned_panel(run_id, model_key, dataset_key)
    companies = []
    if not panel.empty and "company" in panel.columns:
        companies = sorted(panel["company"].dropna().unique())
    selected_company = st.selectbox("Empresa", ["Todas"] + companies)

    horizons = [1, 2, 4]
    if not panel.empty:
        hcols = [c for c in panel.columns if c.startswith("future_log_return_")]
        if hcols:
            horizons = sorted(int(c.split("_")[-1]) for c in hcols)
    horizon = st.selectbox("Horizonte (semanas)", horizons)

    section_header("Vitórias incrementais ITI vs baselines")
    deltas = load_incremental_deltas(run_id, model_key, dataset_key)
    if not deltas.empty:
        st.dataframe(deltas.head(50), width="stretch", hide_index=True)
        if "delta" in deltas.columns and "baseline" in deltas.columns:
            grouped_bar(
                deltas.groupby("baseline")["delta"].mean().reset_index(),
                x="baseline",
                y="delta",
                color="baseline",
                title="Delta médio ITI − baseline",
            )
    else:
        empty_state("incremental_deltas.csv não disponível.")

    section_header("ITI vs retorno futuro")
    if not panel.empty:
        future_col = f"future_log_return_{horizon}"
        subset = panel.copy()
        if selected_company != "Todas" and "company" in subset.columns:
            subset = subset[subset["company"] == selected_company]
        if future_col in subset.columns and "iti_liquido" in subset.columns:
            scatter_plot(
                subset.dropna(subset=[future_col, "iti_liquido"]),
                x="iti_liquido",
                y=future_col,
                title=f"ITI vs retorno futuro (h={horizon})",
                color="company" if "company" in subset.columns and selected_company == "Todas" else None,
                hover_data=["date"] if "date" in subset.columns else None,
            )
    else:
        empty_state("aligned_panel.csv não disponível.")

    section_header("Métricas de mercado")
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
                heatmap(pivot, title="Baseline × métrica × horizonte")
    else:
        st.caption("market_metrics.csv indisponível.")

    section_header("Série ITI e baselines")
    iti = load_iti_daily(run_id, model_key, dataset_key)
    baselines = load_baselines_daily(run_id, model_key, dataset_key)
    if not iti.empty:
        iti_sub = iti.copy()
        if selected_company != "Todas":
            iti_sub = iti_sub[iti_sub["company"] == selected_company]
        daily = iti_sub.groupby("date")["iti_liquido"].mean().reset_index()
        time_series(daily, x="date", y="iti_liquido", title="ITI líquido diário")
    if not baselines.empty and "b1_mean_sentiment" in baselines.columns:
        bl = baselines.copy()
        if selected_company != "Todas":
            bl = bl[bl["company"] == selected_company]
        daily_b = bl.groupby("date")["b1_mean_sentiment"].mean().reset_index()
        time_series(daily_b, x="date", y="b1_mean_sentiment", title="Baseline B1 (sentimento médio)")

    section_header("Limitações")
    st.caption(
        "Evento único (Sabesp), amostra semanal pequena (~24 pontos), correlação ≠ causalidade. "
        "Use resultados para gerar hipóteses, não conclusões definitivas."
    )
