"""Módulo Runs."""

from __future__ import annotations

import json

import streamlit as st

from modules.dashboard.components.chart_block import chart_block
from modules.dashboard.components.charts import horizontal_bar, time_series
from modules.dashboard.components.filters import init_session_state, run_selector
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.kpi_cards import kpi_row
from modules.dashboard.components.layout import page_header
from modules.dashboard.components.states import unavailable_data
from modules.dashboard.content.pt_br import TAB_ITI_CONFIG, TAB_ITI_SERIES, TAB_SUMMARY
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.campaigns import load_manifest
from modules.dashboard.services.catalog import get_resolved_config, list_runs
from modules.dashboard.services.models import class_distribution_columns, load_class_distribution
from modules.dashboard.services.research import extract_win_rate, load_iti_daily, load_research_summary
from modules.dashboard.services.runs import (
    diff_configs,
    get_campaign_hypothesis,
    get_run_detail,
    param_diffs_to_dataframe,
)


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

    win_rate = extract_win_rate(load_research_summary(run_id))
    baseline_rate = extract_win_rate(load_research_summary(baseline_id)) if baseline_id != run_id else None
    delta = (win_rate - baseline_rate) if win_rate is not None and baseline_rate is not None else None

    tab_summary, tab_config, tab_series = st.tabs([TAB_SUMMARY, TAB_ITI_CONFIG, TAB_ITI_SERIES])

    with tab_summary:
        kpi_row(
            [
                ("Status", detail["status"], None),
                ("Linhas", combo.get("row_count", "—"), None),
                ("Duração (s)", f"{combo.get('duration_seconds', 0):.0f}", None),
                ("Device", combo.get("device", "—"), None),
            ]
        )
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
        st.write(f"**Run ID:** `{run_id}`")
        st.write(f"**Início:** {detail['started_at']}")
        st.write(f"**Fim:** {detail['finished_at']}")
        st.write(f"**Modelos:** {', '.join(detail['models'])}")
        st.write(f"**Datasets:** {', '.join(detail['datasets'])}")
        if hypothesis:
            st.write(f"**Hipótese:** {hypothesis}")
        if win_rate is not None:
            st.write(f"**Win rate:** {win_rate:.1%}")

    with tab_config:
        st.json(
            {
                "alpha": detail["alpha"],
                "equation_mode": detail["equation_mode"],
                "disabled_dimensions": detail["disabled_dimensions"],
                "iti_enabled": detail["iti_enabled"],
            }
        )
        if baseline_id != run_id and baseline_id in [r.run_id for r in runs]:
            st.markdown(f"##### Diff vs baseline (`{baseline_id}`)")
            config_a = get_resolved_config(baseline_id) or {}
            config_b = get_resolved_config(run_id) or {}
            diffs = diff_configs(config_a, config_b)
            if diffs:
                chart_block(
                    "param_diff_table",
                    "Parâmetros ITI diferentes",
                    lambda: st.dataframe(
                        param_diffs_to_dataframe(diffs),
                        width="stretch",
                        hide_index=True,
                    ),
                )
            else:
                st.caption("Nenhuma diferença de parâmetros ITI detectada.")
        with st.expander("resolved_config.yaml (temporal_index)"):
            config = get_resolved_config(run_id)
            if config:
                st.code(
                    json.dumps(config.get("temporal_index", {}), indent=2, ensure_ascii=False),
                    language="json",
                )

    with tab_series:
        if model_key and dataset_key:
            dist = load_class_distribution(run_id, model_key, dataset_key)
            if not dist.empty:
                label_col, count_col = class_distribution_columns(dist)
                chart_block(
                    "class_distribution",
                    "Classes previstas",
                    lambda: horizontal_bar(dist, x=count_col, y=label_col),
                )
            iti = load_iti_daily(run_id, model_key, dataset_key)
            if not iti.empty and "iti_liquido" in iti.columns:
                by_date = iti.groupby("date")["iti_liquido"].mean().reset_index()
                chart_block(
                    "iti_daily",
                    "ITI líquido médio (diário)",
                    lambda: time_series(by_date, x="date", y="iti_liquido"),
                )
            else:
                st.caption("Índices ITI não disponíveis.")
        else:
            st.caption("Combinação modelo×dataset indisponível.")
