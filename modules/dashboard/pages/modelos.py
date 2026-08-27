"""Módulo Modelos."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.charts import grouped_bar, horizontal_bar, time_series
from modules.dashboard.components.filters import init_session_state, run_selector
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.metric_card import metric_card
from modules.dashboard.components.states import empty_state, unavailable_data
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.models import (
    has_supervised_labels,
    load_aggregates,
    load_class_distribution,
    load_execution_metrics,
    load_per_class_metrics,
    load_predictions,
    list_combinations,
    class_distribution_columns,
    sentiment_by_company,
)


def render() -> None:
    init_session_state()
    page_header(
        "Modelos",
        "Comportamento dos modelos de sentimento por run, empresa e período.",
    )

    run_id = run_selector()
    if not run_id:
        unavailable_data("runs")
        return

    combos = list_combinations(run_id)
    if not combos:
        empty_state("Nenhuma combinação modelo×dataset nesta run.")
        return

    combo_labels = [f"{c['model_key']} × {c['dataset_key']}" for c in combos]
    idx = st.selectbox("Combinação", range(len(combo_labels)), format_func=lambda i: combo_labels[i])
    combo = combos[idx]
    model_key = combo["model_key"]
    dataset_key = combo["dataset_key"]

    has_labels = has_supervised_labels(run_id, model_key, dataset_key)
    preds = load_predictions(run_id, model_key, dataset_key)
    aggregates = load_aggregates(run_id, model_key, dataset_key)
    class_dist = load_class_distribution(run_id, model_key, dataset_key)
    exec_metrics = load_execution_metrics(run_id, model_key, dataset_key)
    per_class = load_per_class_metrics(run_id, model_key, dataset_key)

    dominant = None
    if not class_dist.empty and "count" in class_dist.columns:
        dominant = class_dist.loc[class_dist["count"].idxmax(), class_dist.columns[0]]

    render_insights(
        insights_engine.generate(
            {"page": "models", "has_labels": has_labels, "dominant_class": dominant}
        )
    )

    section_header("Desempenho geral")
    if not has_labels:
        st.info(
            "Este dataset não possui rótulos verdadeiros — métricas supervisionadas "
            "(F1, precisão, recall) não estão disponíveis."
        )
    else:
        if not per_class.empty:
            for _, row in per_class.iterrows():
                label = str(row.get("label", "")).lower()
                if label in ("f1", "f1_score"):
                    metric_card("f1", float(row.get("value", 0)))
                elif "precision" in label:
                    metric_card("precision", float(row.get("value", 0)))
                elif "recall" in label:
                    metric_card("recall", float(row.get("value", 0)))

    if not exec_metrics.empty:
        st.dataframe(exec_metrics, width="stretch", hide_index=True)

    section_header("Distribuição de classes previstas")
    if not class_dist.empty:
        label_col, count_col = class_distribution_columns(class_dist)
        horizontal_bar(class_dist, x=count_col, y=label_col, title="Volume por classe")
    else:
        empty_state("Distribuição de classes indisponível.")

    section_header("Desempenho por empresa")
    by_company = sentiment_by_company(aggregates)
    if not by_company.empty:
        companies = st.multiselect(
            "Filtrar empresas",
            sorted(by_company["company"].unique()),
            default=sorted(by_company["company"].unique())[:5],
        )
        subset = by_company[by_company["company"].isin(companies)] if companies else by_company
        grouped_bar(
            subset,
            x="company",
            y="sentiment_mean",
            color="company",
            title="Sentimento médio por empresa",
        )
        grouped_bar(
            subset,
            x="company",
            y="news_count",
            color="company",
            title="Volume de notícias por empresa",
        )
    else:
        empty_state("Agregados por empresa indisponíveis.")

    if not preds.empty and "date" in preds.columns:
        section_header("Evolução temporal do sentimento")
        daily = (
            preds.groupby("date")["continuous_sentiment"]
            .mean()
            .reset_index()
            .sort_values("date")
        )
        time_series(daily, x="date", y="continuous_sentiment", title="Sentimento contínuo médio")

    section_header("Amostra de previsões")
    cols = [c for c in ["news_id", "date", "company", "title", "predicted_label", "confidence"] if c in preds.columns]
    if cols:
        st.dataframe(preds[cols].head(100), width="stretch", hide_index=True)
