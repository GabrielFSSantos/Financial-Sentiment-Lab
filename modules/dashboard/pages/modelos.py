"""Módulo Modelos."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.chart_block import chart_block
from modules.dashboard.components.charts import confusion_heatmap, grouped_bar, horizontal_bar, time_series
from modules.dashboard.components.filters import init_session_state, run_selector
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header
from modules.dashboard.components.metric_card import metric_card, metric_row
from modules.dashboard.components.states import empty_state, unavailable_data
from modules.dashboard.config import TRAJETORIA_DOC
from modules.dashboard.content.pt_br import TAB_CLASSIFIER, TAB_DISTRIBUTION, TAB_PANORAMA
from modules.dashboard.content.value_labels import model_label
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.classifier import finbert_accuracy, finbert_kappa, load_classifier_eval
from modules.dashboard.services.models import (
    class_distribution_columns,
    has_supervised_labels,
    load_aggregates,
    load_class_distribution,
    load_execution_metrics,
    load_per_class_metrics,
    load_predictions,
    list_combinations,
    sentiment_by_company,
)


def _render_classifier_tab() -> None:
    eval_summary = load_classifier_eval()
    if not eval_summary:
        empty_state(
            "Bateria classifier_eval_pt não encontrada.",
            hint="./scripts/campaigns/classifier_eval_pt.sh run",
        )
        return

    with st.expander("O que isto mostra?", expanded=False):
        from modules.dashboard.content.chart_help import CHART_HELP

        st.markdown(CHART_HELP.get("kappa_gate", ""))

    metric_row(
        [
            ("accuracy", finbert_accuracy(), True),
            ("kappa", finbert_kappa(), False),
        ]
    )
    st.caption(
        f"Gates: acurácia ≥ {eval_summary.gate_accuracy:.0%}, κ ≥ {eval_summary.gate_kappa:.2f}"
    )

    rows = [
        {
            "Modelo": model_label(m.model_key),
            "Acurácia": f"{m.accuracy:.1%}" if m.accuracy is not None else "—",
            "κ": f"{m.cohen_kappa:.3f}" if m.cohen_kappa is not None else "—",
            "Gate": "✓" if m.passes_gate else "✗",
        }
        for m in eval_summary.models
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    if eval_summary.finbert_confusion is not None:
        chart_block(
            "kappa_gate",
            "Matriz de confusão — FinBERT PT-BR",
            lambda: confusion_heatmap(eval_summary.finbert_confusion),
        )

    if TRAJETORIA_DOC.is_file():
        st.markdown(f"[Trajetória §4.4 — classificador]({TRAJETORIA_DOC.as_uri()})")


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
        label_col, _ = class_distribution_columns(class_dist)
        dominant = class_dist.loc[class_dist["count"].idxmax(), label_col]

    kappa = finbert_kappa()
    accuracy = finbert_accuracy()

    tab_panorama, tab_distribution, tab_classifier = st.tabs(
        [TAB_PANORAMA, TAB_DISTRIBUTION, TAB_CLASSIFIER]
    )

    with tab_panorama:
        render_insights(
            insights_engine.generate(
                {
                    "page": "models",
                    "has_labels": has_labels,
                    "dominant_class": dominant,
                    "kappa": kappa,
                    "accuracy": accuracy,
                }
            )
        )
        if not has_labels:
            st.info(
                "Este dataset não possui rótulos verdadeiros — métricas supervisionadas "
                "(F1, precisão, recall) não estão disponíveis nesta run."
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

        cols = [c for c in ["news_id", "date", "company", "title", "predicted_label", "confidence"] if c in preds.columns]
        if cols:
            st.markdown("##### Amostra de previsões")
            st.dataframe(preds[cols].head(100), width="stretch", hide_index=True)

    with tab_distribution:
        if not class_dist.empty:
            label_col, count_col = class_distribution_columns(class_dist)
            chart_block(
                "class_distribution",
                "Volume por classe",
                lambda: horizontal_bar(class_dist, x=count_col, y=label_col),
            )
        else:
            empty_state("Distribuição de classes indisponível.")

        by_company = sentiment_by_company(aggregates)
        if not by_company.empty:
            companies = st.multiselect(
                "Filtrar empresas",
                sorted(by_company["company"].unique()),
                default=sorted(by_company["company"].unique())[:5],
            )
            subset = by_company[by_company["company"].isin(companies)] if companies else by_company
            chart_block(
                "sentiment_by_company",
                "Sentimento médio por empresa",
                lambda: grouped_bar(subset, x="company", y="sentiment_mean", color="company"),
            )
            chart_block(
                "sentiment_by_company",
                "Volume de notícias por empresa",
                lambda: grouped_bar(subset, x="company", y="news_count", color="company"),
            )
        else:
            empty_state("Agregados por empresa indisponíveis.")

        if not preds.empty and "date" in preds.columns:
            daily = (
                preds.groupby("date")["continuous_sentiment"]
                .mean()
                .reset_index()
                .sort_values("date")
            )
            chart_block(
                "sentiment_time_series",
                "Sentimento contínuo médio",
                lambda: time_series(daily, x="date", y="continuous_sentiment"),
            )

    with tab_classifier:
        _render_classifier_tab()
