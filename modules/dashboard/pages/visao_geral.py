"""Visão geral da pesquisa."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.charts import horizontal_bar, time_series
from modules.dashboard.components.filters import init_session_state
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.kpi_cards import kpi_row
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.states import empty_state
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.campaigns import best_campaign_run, load_manifest
from modules.dashboard.services.corpus import compute_stats, load_corpus
from modules.dashboard.services.research import extract_win_rate, load_research_summary
from modules.dashboard.services.catalog import list_runs


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
    baseline_rate = None
    if manifest:
        baseline_id = manifest.get("baseline_run_id", "sabesp_r0_baseline")
        baseline_rate = extract_win_rate(load_research_summary(baseline_id))

    last_run = runs[0].run_id if runs else "—"
    models_used = sorted({m for r in runs for m in r.models})

    kpi_row(
        [
            ("Notícias", stats.total, None),
            ("Empresas", stats.companies, None),
            ("Runs", len(runs), None),
            ("Modelos", len(models_used), None),
        ]
    )
    kpi_row(
        [
            ("Período", f"{stats.date_min or '—'} → {stats.date_max or '—'}", None),
            ("Setores", stats.sectors, None),
            ("Fontes", stats.sources, None),
            ("Última run", last_run[:20] + "…" if len(last_run) > 20 else last_run, None),
        ]
    )

    insights = insights_engine.generate(
        {
            "page": "overview",
            "total_news": stats.total,
            "last_run": last_run,
            "best_campaign_run": {
                "run_id": best.get("run_id") if best else None,
                "win_rate": (best.get("metrics_summary") or {}).get("win_rate") if best else None,
            }
            if best
            else None,
            "baseline_win_rate": baseline_rate,
        }
    )
    render_insights(insights)

    section_header("Distribuição do corpus")
    col1, col2 = st.columns(2)
    with col1:
        if not stats.by_company.empty:
            horizontal_bar(
                stats.by_company.rename(columns={"company": "Empresa", "count": "Notícias"}),
                x="Notícias",
                y="Empresa",
                title="Notícias por empresa",
            )
        else:
            empty_state("Corpus não disponível.")
    with col2:
        if not stats.time_series.empty:
            time_series(
                stats.time_series,
                x="period",
                y="count",
                title="Volume mensal de notícias",
            )

    section_header("Campanha Sabesp")
    if manifest:
        best_rate = (best.get("metrics_summary") or {}).get("win_rate") if best else None
        st.write(
            f"**Baseline:** {manifest.get('baseline_run_id')} "
            f"({baseline_rate:.1%} win rate)" if baseline_rate else f"**Baseline:** {manifest.get('baseline_run_id')}"
        )
        if best:
            st.write(
                f"**Melhor run:** {best.get('run_id')} — "
                f"win rate {(best_rate or 0):.1%}"
            )
    else:
        empty_state("Manifest da campanha não encontrado.", hint="outputs/campaigns/sabesp_2026/manifest.json")

    section_header("Acesso rápido")
    st.markdown(
        "- **Datasets** — explorar corpus e cobertura\n"
        "- **Modelos** — desempenho por run e empresa\n"
        "- **Runs** — detalhe de cada execução\n"
        "- **Comparação** — diff entre runs\n"
        "- **Experimentos** — campanha Sabesp R0–R9\n"
        "- **Research** — validação ITI vs mercado"
    )
