"""Dashboard — campanha ITI-v2 (leitor de artefatos em outputs/campaigns/iti_v2/)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.experiment import PROJECT_ROOT

CAMPAIGN_ROOT = PROJECT_ROOT / "outputs/campaigns/iti_v2"


def _list_runs() -> list[str]:
    if not CAMPAIGN_ROOT.is_dir():
        return []
    return sorted(
        [
            p.name
            for p in CAMPAIGN_ROOT.iterdir()
            if p.is_dir() and (p / "metrics_primary.json").is_file()
        ],
        reverse=True,
    )


def render() -> None:
    st.header("Campanha ITI-v2")
    st.caption(
        "Leitura de artefatos versionados; não recalcula índices. "
        "Referência humana independente: pendente (P06)."
    )
    runs = _list_runs()
    if not runs:
        st.warning("Nenhum run ITI-v2 com métricas em `outputs/campaigns/iti_v2/`.")
        return

    run_id = st.selectbox("Run", runs, index=0)
    run_dir = CAMPAIGN_ROOT / run_id

    primary_path = run_dir / "metrics_primary.json"
    delta_path = run_dir / "metrics_primary_delta.json"
    registry_path = run_dir / "result_registry.json"

    if primary_path.is_file():
        metrics = json.loads(primary_path.read_text(encoding="utf-8"))
        st.subheader("Teste principal e marginal exploratória")
        st.json(
            {
                "execution_mode": metrics.get("execution_mode"),
                "n_panel": metrics.get("n_panel"),
                "primary_delta": metrics.get("primary_delta"),
                "primary_delta_p": metrics.get("primary_delta_p_value"),
                "marginal_spearman": metrics.get("estimate"),
            }
        )

    if delta_path.is_file():
        st.subheader("Δ ITI-H7 − Soft (detalhe)")
        st.json(json.loads(delta_path.read_text(encoding="utf-8")))

    sec_path = run_dir / "table_secondary.csv"
    if sec_path.is_file():
        st.subheader("Família secundária (Holm)")
        st.dataframe(pd.read_csv(sec_path), use_container_width=True)

    panel_path = run_dir / "aligned_panel.csv"
    if panel_path.is_file():
        panel = pd.read_csv(panel_path)
        st.subheader("Painel alinhado (amostra)")
        st.dataframe(panel.head(20), use_container_width=True)

    fig_dir = run_dir / "generated_figures"
    if fig_dir.is_dir():
        st.subheader("Figuras")
        for image in sorted(fig_dir.glob("*.png")):
            st.image(str(image), caption=image.name)

    if registry_path.is_file():
        with st.expander("result_registry.json"):
            st.code(registry_path.read_text(encoding="utf-8")[:8000])
