"""Inferência estatística da campanha ITI-v2 (bootstrap + Holm)."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

from modules.research.config.analysis_plan import AnalysisPlan
from modules.research.config.loader import InferenceConfiguration
from modules.research.validation.metrics import compute_metric_with_inference


def _bootstrap_replicates(plan: AnalysisPlan) -> int:
    override = os.environ.get("ITI_V2_BOOTSTRAP", "").strip()
    if override.isdigit():
        return int(override)
    return plan.bootstrap_replicates


def holm_adjust(p_values: list[float], *, alpha: float) -> list[dict[str, Any]]:
    """Correção de Holm para família de hipóteses (ordem crescente de p)."""

    m = len(p_values)
    if m == 0:
        return []

    order = np.argsort(p_values)
    adjusted = np.ones(m, dtype=float)
    prev = 0.0
    for rank, idx in enumerate(order):
        factor = m - rank
        raw = min(1.0, float(p_values[idx]) * factor)
        adjusted[idx] = max(raw, prev)
        prev = adjusted[idx]

    rows: list[dict[str, Any]] = []
    for index, p_raw in enumerate(p_values):
        rows.append(
            {
                "hypothesis_index": index,
                "p_raw": p_raw,
                "p_holm": float(adjusted[index]),
                "significant_at_alpha": bool(adjusted[index] <= alpha),
            }
        )
    return rows


def compute_horizon_metrics(
    panel: pd.DataFrame,
    *,
    signal_column: str,
    horizons: tuple[int, ...],
    plan: AnalysisPlan,
) -> list[dict[str, Any]]:
    inference = InferenceConfiguration(
        enabled=True,
        n_bootstrap=_bootstrap_replicates(plan),
        block_size=plan.block_length_weeks,
        ci_level=1.0 - plan.alpha,
        random_seed=plan.seed,
    )
    metric = plan.primary_metric
    rows: list[dict[str, Any]] = []

    for horizon in horizons:
        target_col = f"future_log_return_{horizon}"
        row: dict[str, Any] = {
            "horizon_weeks": horizon,
            "metric": metric,
            "signal_column": signal_column,
            "target_column": target_col,
            "universe": "aligned_panel",
        }
        if target_col not in panel.columns or signal_column not in panel.columns:
            row.update(
                {
                    "status": "missing_columns",
                    "n": 0,
                    "estimate": None,
                    "p_value": None,
                }
            )
            rows.append(row)
            continue

        predictor = panel[signal_column]
        target = panel[target_col]
        result = compute_metric_with_inference(
            metric,
            predictor,
            target,
            inference=inference,
        )
        row.update(
            {
                "status": "ok" if result.value is not None else "undefined",
                "n": result.n,
                "estimate": result.value,
                "p_value": result.p_value,
                "ci_low": result.ci_low,
                "ci_high": result.ci_high,
                "n_bootstrap": result.n_bootstrap,
            }
        )
        rows.append(row)

    p_values = [
        float(r["p_value"])
        for r in rows
        if r.get("p_value") is not None and np.isfinite(r["p_value"])
    ]
    holm = holm_adjust(p_values, alpha=plan.alpha) if p_values else []
    holm_by_index = {item["hypothesis_index"]: item for item in holm}
    p_iter = 0
    for row in rows:
        if row.get("p_value") is None or not np.isfinite(row.get("p_value")):
            row["p_holm"] = None
            row["significant_holm"] = False
            continue
        adj = holm_by_index.get(p_iter)
        p_iter += 1
        if adj:
            row["p_holm"] = adj["p_holm"]
            row["significant_holm"] = adj["significant_at_alpha"]
        else:
            row["p_holm"] = None
            row["significant_holm"] = False

    return rows


def metrics_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)
