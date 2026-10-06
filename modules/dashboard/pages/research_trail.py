"""Trilha da pesquisa e hub de documentação."""

from __future__ import annotations

import streamlit as st

from modules.dashboard.components.filters import init_session_state
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.section_block import section_block
from modules.dashboard import PROJECT_ROOT
from modules.dashboard.config import CHART_INVENTORY_DOC, DOCUMENTACAO_DOC, TRAJETORIA_DOC
from modules.dashboard.content.pt_br import PIPELINE_STEPS, RESEARCH_PHASES
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.catalog import list_runs, run_display_name, run_status_badge
from modules.dashboard.services.classifier import classifier_gate_passed, finbert_kappa


def render() -> None:
    init_session_state()
    page_header(
        "Trilha da pesquisa",
        "Fases F0–F6, documentação e status das execuções — números oficiais na trajetória (Parte 4).",
    )

    runs = list_runs()
    render_insights(
        insights_engine.generate(
            {
                "page": "trail",
                "total_runs": len(runs),
                "classifier_gate_failed": not classifier_gate_passed(),
            }
        )
    )

    with section_block("Pipeline resumido", "pipeline_journey"):
        for i, (title, desc) in enumerate(PIPELINE_STEPS, 1):
            st.markdown(f"**{i}. {title}** — {desc}")

    section_header("Fases da pesquisa (F0–F6)")
    for phase_id, title, desc in RESEARCH_PHASES:
        st.markdown(f"**{phase_id} — {title}** — {desc}")

    kappa = finbert_kappa()
    if kappa is not None:
        st.caption(f"FinBERT κ (amostra manual): {kappa:.3f}")

    section_header("Execuções disponíveis")
    if not runs:
        st.caption("Nenhuma run em outputs/. Execute `./scripts/run_experiment.sh`.")
    for run in runs:
        badge = run_status_badge(run)
        st.markdown(f"- **{run_display_name(run.run_id)}** (`{run.run_id}`) — {badge}")

    section_header("Documentação")
    doc_links = [
        ("Trajetória da pesquisa (Parte 4 — resultados)", TRAJETORIA_DOC),
        ("Documentação técnica", DOCUMENTACAO_DOC),
        ("Inventário de gráficos do dashboard", CHART_INVENTORY_DOC),
    ]
    for label, path in doc_links:
        if path.is_file():
            st.markdown(f"- [{label}]({path.as_uri()})")
        else:
            st.markdown(f"- {label} _(ausente: `{path.name}`)_")

    st.caption(
        "Números oficiais (win rate 2/24, κ, correlações) permanecem em docs/research_trail/part-04-results.md — "
        "este hub não replica tabelas numéricas."
    )
    st.caption(f"Projeto: `{PROJECT_ROOT}`")
