"""Módulo Runs."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from modules.dashboard.components.charts import horizontal_bar, time_series
from modules.dashboard.components.filters import init_session_state, run_selector
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.kpi_cards import kpi_row
from modules.dashboard.components.layout import page_header, section_header
from modules.dashboard.components.states import unavailable_data
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.campaigns import load_manifest
from modules.dashboard.services.catalog import get_resolved_config, list_runs
from modules.dashboard.services.models import load_class_distribution, class_distribution_columns
from modules.dashboard.services.research import extract_win_rate, load_iti_daily, load_research_summary
from modules.dashboard.services.runs import diff_configs, get_campaign_hypothesis, get_run_detail


def render() -> None:
    init_session_state()
    page_header(
        "Runs",
        "Relatório interativo de cada execução: configuração, resultados e comparação com baseline.",
    )

    runs = list_runs()
    if not runs:
        unavailable_data("Nenhuma run em outputs/", how_to="./scripts/run_experiment.sh --run-id minha_run")
        return

    run_id = run_selector()
    if not run_id:
        return

    detail = get_run_detail(run_id)
    if not detail:
        return

    manifest = load_manifest()
    baseline_id = (manifest or {}).get("baseline_run_id", "sabesp_r0_baseline")
    hypothesis = get_campaign_hypothesis(run_id)

    combo = detail["combinations"][0] if detail["combinations"] else {}
    model_key = combo.get("model_key", "")
    dataset_key = combo.get("dataset_key", "")

    kpi_row(
        [
            ("Status", detail["status"], None),
            ("Linhas", combo.get("row_count", "—"), None),
            ("Duração (s)", f"{combo.get('duration_seconds', 0):.0f}", None),
            ("Device", combo.get("device", "—"), None),
        ]
    )

    win_rate = extract_win_rate(load_research_summary(run_id))
    baseline_rate = extract_win_rate(load_research_summary(baseline_id)) if baseline_id != run_id else None
    delta = (win_rate - baseline_rate) if win_rate is not None and baseline_rate is not None else None

    render_insights(
        insights_engine.generate(
            {
                "page": "runs",
                "has_research": detail["has_research"],
                "hypothesis": hypothesis,
                "win_rate_delta": delta,
            }
        )
    )

    section_header("Identificação")
    st.write(f"**Run ID:** `{run_id}`")
    st.write(f"**Início:** {detail['started_at']}")
    st.write(f"**Fim:** {detail['finished_at']}")
    st.write(f"**Modelos:** {', '.join(detail['models'])}")
    st.write(f"**Datasets:** {', '.join(detail['datasets'])}")
    if hypothesis:
        st.write(f"**Hipótese:** {hypothesis}")

    section_header("Configuração ITI")
    st.json(
        {
            "alpha": detail["alpha"],
            "equation_mode": detail["equation_mode"],
            "disabled_dimensions": detail["disabled_dimensions"],
            "iti_enabled": detail["iti_enabled"],
        }
    )

    if baseline_id != run_id and baseline_id in [r.run_id for r in runs]:
        section_header(f"Diff vs baseline ({baseline_id})")
        config_a = get_resolved_config(baseline_id) or {}
        config_b = get_resolved_config(run_id) or {}
        diffs = diff_configs(config_a, config_b)
        if diffs:
            st.dataframe(pd.DataFrame(diffs), width="stretch", hide_index=True)
        else:
            st.caption("Nenhuma diferença de parâmetros ITI detectada.")

    if model_key and dataset_key:
        section_header("Distribuição de classes previstas")
        dist = load_class_distribution(run_id, model_key, dataset_key)
        if not dist.empty:
            label_col, count_col = class_distribution_columns(dist)
            horizontal_bar(dist, x=count_col, y=label_col, title="Classes previstas")
        else:
            st.caption("Distribuição indisponível.")

        section_header("ITI diário")
        iti = load_iti_daily(run_id, model_key, dataset_key)
        if not iti.empty and "iti_liquido" in iti.columns:
            by_date = iti.groupby("date")["iti_liquido"].mean().reset_index()
            time_series(by_date, x="date", y="iti_liquido", title="ITI líquido médio (diário)")
        else:
            st.caption("Índices ITI não disponíveis.")

    section_header("Configuração completa")
    with st.expander("resolved_config.yaml"):
        config = get_resolved_config(run_id)
        if config:
            st.code(json.dumps(config.get("temporal_index", {}), indent=2, ensure_ascii=False), language="json")
