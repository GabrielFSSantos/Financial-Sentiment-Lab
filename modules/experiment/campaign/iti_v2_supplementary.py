"""Sinais auxiliares: view documento e LEGACY-C para contrastes pareados."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.iti_v2_legacy import attach_legacy_c_daily
from modules.experiment.campaign.iti_v2_protocol import load_iti_v2_protocol
from modules.experiment.indexing.iti_v2 import build_daily_iti_v2_frame, build_weekly_signals
from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
from modules.research.io.market_weekly_returns import weekly_market_session_calendar


def _protocol_views(protocol_path: Path) -> tuple[str, str, int, int]:
    protocol = load_iti_v2_protocol(protocol_path)
    text = protocol.raw.get("text", {})
    index = protocol.raw.get("index", {})
    legacy = protocol.raw.get("legacy", {})
    primary = str(text.get("primary_view", "entity_context_v1"))
    comparison = str(text.get("comparison_view", "document_v1"))
    warmup = int(index.get("warmup_days", 70))
    legacy_alpha = float(legacy.get("alpha", 0.7))
    return primary, comparison, warmup, legacy_alpha


def _filter_predictions(frame: pd.DataFrame, view_id: str) -> pd.DataFrame:
    if "view_id" not in frame.columns:
        return frame
    return frame.loc[frame["view_id"].astype(str) == view_id].copy()


def build_supplementary_weekly(
    predictions_path: Path,
    run_dir: Path,
    *,
    protocol_path: Path | None = None,
) -> dict[str, Path]:
    protocol_path = protocol_path or (
        PROJECT_ROOT / "configs/campaigns/iti_v2/protocol.yaml"
    )
    protocol = load_iti_v2_protocol(protocol_path)
    primary_view, comparison_view, warmup, legacy_alpha = _protocol_views(protocol_path)

    preds = pd.read_csv(predictions_path)
    paths: dict[str, Path] = {}
    calendar_end = pd.to_datetime(preds["date"], errors="coerce").max()
    market = load_market_prices(load_market_configuration(project_root=PROJECT_ROOT))
    price_col = "adj_close" if "adj_close" in market.columns else "close"
    sessions = weekly_market_session_calendar(market, price_col=price_col)
    mapping_path = PROJECT_ROOT / "configs/campaigns/iti_v2/research_weekly.yaml"
    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    company_to_ticker = dict(mapping.get("mapping", {}).get("company_to_ticker", {}))

    entity_preds = _filter_predictions(preds, primary_view)
    if entity_preds.empty:
        entity_preds = preds

    daily_entity = build_daily_iti_v2_frame(
        entity_preds,
        half_lives=tuple(protocol.half_life_days),
        warmup_days=warmup,
        calendar_end=calendar_end,
    )
    daily_legacy = attach_legacy_c_daily(
        daily_entity,
        alpha=legacy_alpha,
        horizon_mode=str(protocol.raw.get("legacy", {}).get("horizon_mode", "ewma_alpha")),
    )
    weekly_legacy = build_weekly_signals(
        daily_legacy,
        week_anchor=protocol.week_anchor,
        value_columns=("legacy_c_iti",),
        market_sessions=sessions,
        company_to_ticker=company_to_ticker,
    )
    legacy_path = run_dir / "iti_weekly_legacy_c.csv"
    weekly_legacy.to_csv(legacy_path, index=False)
    paths["weekly_legacy"] = legacy_path

    doc_preds = _filter_predictions(preds, comparison_view)
    doc_ok = (
        not doc_preds.empty
        and "status" in doc_preds.columns
        and (doc_preds["status"] == "ok").any()
    )
    if doc_ok:
        daily_doc = build_daily_iti_v2_frame(
            doc_preds,
            half_lives=tuple(protocol.half_life_days),
            warmup_days=warmup,
            calendar_end=calendar_end,
        )
        weekly_doc = build_weekly_signals(
            daily_doc,
            week_anchor=protocol.week_anchor,
            market_sessions=sessions,
            company_to_ticker=company_to_ticker,
        )
        rename = {
            col: f"document_{col}"
            for col in weekly_doc.columns
            if col.startswith("iti_v2_h") or col in ("soft_input", "hard_input")
        }
        weekly_doc = weekly_doc.rename(columns=rename)
        doc_path = run_dir / "iti_weekly_document_v1.csv"
        weekly_doc.to_csv(doc_path, index=False)
        paths["weekly_document"] = doc_path

    return paths


def _panel_join_keys(panel: pd.DataFrame, weekly: pd.DataFrame) -> list[str]:
    if "period_end" in panel.columns and "week_end" in weekly.columns:
        return ["company_id", "period_end"]
    for keys in (
        ("company_id", "week_id"),
        ("company_id", "date"),
    ):
        if all(k in panel.columns for k in keys) and all(k in weekly.columns for k in keys):
            return list(keys)
    return ["company_id"]


def enrich_aligned_panel(panel: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    """Junta colunas ``document_*`` e ``legacy_c_iti`` ao painel alinhado."""

    work = panel.copy()
    if "period_end" not in work.columns and "week_end" in work.columns:
        work["period_end"] = work["week_end"]

    legacy_path = run_dir / "iti_weekly_legacy_c.csv"
    if legacy_path.is_file():
        legacy = pd.read_csv(legacy_path)
        if "week_end" in legacy.columns:
            legacy["period_end"] = legacy["week_end"]
        join_keys = _panel_join_keys(work, legacy)
        cols = [c for c in ("legacy_c_iti",) if c in legacy.columns]
        if cols and join_keys:
            work = work.merge(
                legacy[join_keys + cols].drop_duplicates(subset=join_keys),
                on=join_keys,
                how="left",
            )

    doc_path = run_dir / "iti_weekly_document_v1.csv"
    if doc_path.is_file():
        doc = pd.read_csv(doc_path)
        if "week_end" in doc.columns:
            doc["period_end"] = doc["week_end"]
        join_keys = _panel_join_keys(work, doc)
        doc_cols = [c for c in doc.columns if c.startswith("document_")]
        if doc_cols and join_keys:
            work = work.merge(
                doc[join_keys + doc_cols].drop_duplicates(subset=join_keys),
                on=join_keys,
                how="left",
            )
    return work
