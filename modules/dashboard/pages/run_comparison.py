"""Comparação entre runs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.dashboard.components.chart_block import chart_block
from modules.dashboard.components.charts import grouped_bar, heatmap
from modules.dashboard.components.insight_panel import render_insights
from modules.dashboard.components.layout import page_header
from modules.dashboard.components.section_block import section_block
from modules.dashboard.components.states import empty_state
from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.services.catalog import list_runs
from modules.dashboard.services.compare import compare_runs, compare_sentiment_by_company, delta_win_rate
from modules.dashboard.services.models import list_combinations
from modules.dashboard.services.runs import param_diffs_to_dataframe


def render() -> None:
    page_header(
        "Comparação entre Runs",
        "Selecione duas ou mais runs para comparar configurações, métricas e desempenho por empresa.",
    )

    runs = list_runs()
    if len(runs) < 2:
        empty_state("É necessário ter pelo menos 2 runs para comparar.")
        return

    run_ids = [r.run_id for r in runs]
    selected = st.multiselect("Runs para comparar", run_ids, default=run_ids[:2])
    baseline = st.selectbox(
        "Baseline para delta",
        run_ids,
        index=run_ids.index("sabesp_r0_baseline") if "sabesp_r0_baseline" in run_ids else 0,
    )

    if len(selected) < 2:
        st.warning("Selecione pelo menos 2 runs.")
        return

    result = compare_runs(selected)
    if result.get("error"):
        st.error(result["error"])
        return

    deltas = []
    for rid in selected:
        if rid != baseline:
            d = delta_win_rate(baseline, rid)
            if d is not None:
                deltas.append({"run_a": baseline, "run_b": rid, "delta": d})

    with section_block(
        "Como ler esta página",
        intro="Compare win rate, parâmetros ITI e sentimento por empresa entre runs da campanha.",
    ):
        pass

    render_insights(insights_engine.generate({"page": "compare", "win_rate_deltas": deltas}))

    metrics_df = pd.DataFrame(result["metrics"])
    if not metrics_df.empty:
        st.dataframe(metrics_df, width="stretch", hide_index=True)
        if "win_rate" in metrics_df.columns:
            chart_block(
                "win_rate_by_run",
                "Win rate ITI vs baselines",
                lambda: grouped_bar(
                    metrics_df.dropna(subset=["win_rate"]),
                    x="run_id",
                    y="win_rate",
                    color="run_id",
                ),
            )
            wr = metrics_df.dropna(subset=["win_rate"])
            if not wr.empty:
                chart_block(
                    "win_rate_heatmap",
                    "Heatmap win rate",
                    lambda: heatmap(wr.set_index("run_id")[["win_rate"]].T),
                )

    param_diffs = result.get("param_diffs") or []
    if param_diffs:
        chart_block(
            "param_diff_table",
            "Diferenças de parâmetros ITI",
            lambda: st.dataframe(
                param_diffs_to_dataframe(param_diffs),
                width="stretch",
                hide_index=True,
            ),
        )
        st.caption("Colunas run_a / run_b: valores do baseline e da run candidata, respectivamente.")
    else:
        st.caption("Nenhuma diferença de parâmetros ITI entre as runs selecionadas.")

    combo_run = selected[0]
    combos = list_combinations(combo_run)
    if combos:
        model_key = combos[0]["model_key"]
        dataset_key = combos[0]["dataset_key"]
        sentiment_cmp = compare_sentiment_by_company(selected, model_key, dataset_key)
        if not sentiment_cmp.empty:
            chart_block(
                "sentiment_compare_runs",
                "Sentimento médio por empresa e run",
                lambda: grouped_bar(
                    sentiment_cmp,
                    x="company",
                    y="sentiment_mean",
                    color="run_id",
                ),
            )
        else:
            st.caption("Agregados por empresa indisponíveis para comparação.")
