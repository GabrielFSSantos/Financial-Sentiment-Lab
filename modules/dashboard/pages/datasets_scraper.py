"""Módulo Datasets e Scraper."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.dashboard.components.charts import grouped_bar, heatmap, horizontal_bar, time_series
from modules.dashboard.components.filters import date_range_filter, multiselect_from_column
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.kpi_cards import kpi_row
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.states import empty_state
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.catalog import list_datasets
from modules.dashboard.services.corpus import (
    company_month_heatmap,
    compute_stats,
    filter_corpus,
    load_corpus,
    resolve_dataset_path,
)


def render() -> None:
    page_header(
        "Datasets e Scraper",
        "Explore a base de notícias: cobertura por empresa, setor, fonte e evolução temporal.",
    )

    datasets = list_datasets()
    dataset_options = {d.key: d for d in datasets if d.enabled}
    selected_key = st.selectbox(
        "Dataset",
        list(dataset_options.keys()),
        format_func=lambda k: dataset_options[k].display_name,
    )
    dataset = dataset_options.get(selected_key)
    path = resolve_dataset_path(dataset)
    raw = load_corpus(path)

    if raw.empty:
        empty_state(f"Arquivo não encontrado: {path}")
        return

    section_header("Filtros")
    col1, col2, col3 = st.columns(3)
    with col1:
        companies = multiselect_from_column(raw, "company", label="Empresa", key="ds_company")
    with col2:
        sectors = multiselect_from_column(raw, "sector", label="Setor", key="ds_sector")
    with col3:
        sources = multiselect_from_column(raw, "source", label="Fonte", key="ds_source")

    date_from, date_to = date_range_filter(raw, key_prefix="ds")
    filtered = filter_corpus(
        raw,
        companies=companies or None,
        sectors=sectors or None,
        sources=sources or None,
        date_from=date_from,
        date_to=date_to,
    )

    freq_label = st.radio("Granularidade temporal", ["Mês", "Semana", "Dia"], horizontal=True)
    freq_map = {"Mês": "ME", "Semana": "W", "Dia": "D"}
    stats = compute_stats(filtered, freq=freq_map[freq_label])

    kpi_row(
        [
            ("Total", stats.total, None),
            ("Empresas", stats.companies, None),
            ("Setores", stats.sectors, None),
            ("Fontes", stats.sources, None),
        ]
    )

    top_share = None
    if not stats.by_company.empty and stats.total > 0:
        top_share = stats.by_company.iloc[0]["count"] / stats.total

    render_insights(
        insights_engine.generate(
            {
                "page": "datasets",
                "alerts": stats.alerts,
                "gaps": stats.gaps,
                "top_company_share": top_share,
            }
        )
    )

    section_header("Principais visualizações")
    c1, c2 = st.columns(2)
    with c1:
        if not stats.by_company.empty:
            horizontal_bar(
                stats.by_company.rename(columns={"company": "Empresa", "count": "Qtd"}),
                x="Qtd",
                y="Empresa",
                title="Ranking por empresa",
            )
    with c2:
        if not stats.by_source.empty:
            horizontal_bar(
                stats.by_source.rename(columns={"source": "Fonte", "count": "Qtd"}),
                x="Qtd",
                y="Fonte",
                title="Ranking por fonte",
            )

    if not stats.time_series.empty:
        time_series(stats.time_series, x="period", y="count", title="Volume ao longo do tempo")

    heat = company_month_heatmap(filtered)
    if not heat.empty:
        section_header("Cobertura empresa × mês")
        heatmap(heat, title="Heatmap de notícias")

    if companies and len(companies) == 1 and "source" in filtered.columns:
        section_header("Composição por fonte (empresa selecionada)")
        by_src = filtered.groupby("source").size().reset_index(name="count")
        grouped_bar(by_src, x="source", y="count", color="source", title=f"Fontes — {companies[0]}")

    section_header("Notícias")
    display_cols = [c for c in ["news_id", "date", "company", "title", "source", "url"] if c in filtered.columns]
    if display_cols:
        show = filtered[display_cols].copy()
        if "date" in show.columns:
            show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(show.head(200), width="stretch", hide_index=True)
        if len(filtered) > 200:
            st.caption(f"Exibindo 200 de {len(filtered)} registros. Use filtros para refinar.")
