"""Visão geral da pesquisa."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.chart_block import chart_block
from modules.dashboard.components.charts import horizontal_bar, time_series
from modules.dashboard.components.filters import init_session_state
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.kpi_cards import catalog_kpi_row, kpi_row
from modules.dashboard.components.layout import page_header
from modules.dashboard.components.metric_card import metric_row
from modules.dashboard.components.section_block import section_block
from modules.dashboard.components.states import empty_state
from modules.dashboard.config import TRAJETORIA_DOC
from modules.dashboard.content.pt_br import PIPELINE_STEPS
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.campaigns import best_campaign_run, load_manifest
from modules.dashboard.services.classifier import finbert_kappa, classifier_gate_passed
from modules.dashboard.services.corpus import compute_stats, load_corpus
from modules.dashboard.services.research import extract_win_rate, load_research_summary
from modules.dashboard.services.catalog import list_runs


def _render_pipeline() -> None:
    for i, (title, desc) in enumerate(PIPELINE_STEPS, 1):
        st.markdown(f"**{i}. {title}** — {desc}")
    if TRAJETORIA_DOC.is_file():
        st.markdown(f"[Trajetória completa (F0–F6)]({TRAJETORIA_DOC.as_uri()})")


def render() -> None:
    init_session_state()
    page_header(
        "Visão Geral",
        "Resumo executivo do estado atual da pesquisa: corpus, runs e campanha Sabesp.",
    )

    runs = list_runs()
    corpus = load_corpus()
    stats = compute_stats(corpus)

    manifest = load_manifest()
    best = best_campaign_run(manifest)
    baseline_id = (manifest or {}).get("baseline_run_id", "sabesp_r0_baseline")
    baseline_rate = extract_win_rate(load_research_summary(baseline_id))
    best_rate = (best.get("metrics_summary") or {}).get("win_rate") if best else None
    kappa = finbert_kappa()

    metric_row(
        [
            ("win_rate", best_rate, True),
            ("kappa", kappa, False),
            ("news_count", float(stats.total), False),
            ("runs_count", float(len(runs)), False),
        ]
    )

    kpi_row(
        [
            ("Empresas", stats.companies, None),
            ("Período", f"{stats.date_min or '—'} → {stats.date_max or '—'}", None),
            ("Setores", stats.sectors, None),
            ("Fontes", stats.sources, None),
        ]
    )

    render_insights(
        insights_engine.generate(
            {
                "page": "overview",
                "total_news": stats.total,
                "last_run": runs[0].run_id if runs else None,
                "best_campaign_run": {
                    "run_id": best.get("run_id") if best else None,
                    "win_rate": best_rate,
                }
                if best
                else None,
                "baseline_win_rate": baseline_rate,
            }
        )
    )

    with section_block("Pipeline da pesquisa", "pipeline_journey"):
        _render_pipeline()

    col1, col2 = st.columns(2)
    with col1:
        chart_block(
            "corpus_by_company",
            "Notícias por empresa",
            lambda: horizontal_bar(
                stats.by_company.rename(columns={"company": "Empresa", "count": "Notícias"}),
                x="Notícias",
                y="Empresa",
            )
            if not stats.by_company.empty
            else empty_state("Corpus não disponível."),
        )
    with col2:
        chart_block(
            "corpus_time_series",
            "Volume mensal",
            lambda: time_series(stats.time_series, x="period", y="count")
            if not stats.time_series.empty
            else empty_state("Série temporal indisponível."),
        )

    with section_block("Estado da campanha"):
        if manifest:
            st.write(f"**Baseline:** `{manifest.get('baseline_run_id')}`")
            if baseline_rate is not None:
                catalog_kpi_row([("win_rate", baseline_rate, True)])
            if best:
                st.write(f"**Melhor run:** `{best.get('run_id')}`")
                if best_rate is not None:
                    st.write(f"Win rate: **{best_rate:.1%}**")
            if not classifier_gate_passed():
                st.markdown(
                    '<div class="fsl-callout-warning">Gate κ do classificador não atendido — '
                    "resultados exploratórios.</div>",
                    unsafe_allow_html=True,
                )
            st.caption("Abra **Experimentos** no menu lateral para detalhes da campanha R0–R9.")
        else:
            empty_state(
                "Manifest da campanha não encontrado.",
                hint="outputs/campaigns/sabesp_2026/manifest.json",
            )
