"""Contrastes ITI-v2: teste principal Δ e família secundária (bootstrap pareado + Holm)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from modules.research.config.analysis_plan import AnalysisPlan
from modules.research.config.loader import InferenceConfiguration
from modules.research.validation.inference import compute_delta_inference
from modules.research.validation.metrics import NUMPY_METRIC_FUNCTIONS, compute_metric_with_inference


@dataclass(frozen=True)
class ContrastSpec:
    id: str
    candidate_column: str
    baseline_column: str
    metric: str
    horizon_weeks: int
    description: str = ""


def load_contrast_plan(path: Path) -> tuple[ContrastSpec, list[ContrastSpec]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    primary_raw = raw["primary"]
    primary = ContrastSpec(
        id=str(primary_raw["id"]),
        candidate_column=str(primary_raw["candidate_column"]),
        baseline_column=str(primary_raw["baseline_column"]),
        metric=str(primary_raw["metric"]),
        horizon_weeks=int(primary_raw["horizon_weeks"]),
        description=str(primary_raw.get("description", "")),
    )
    secondary: list[ContrastSpec] = []
    for item in raw.get("secondary", []):
        secondary.append(
            ContrastSpec(
                id=str(item["id"]),
                candidate_column=str(item["candidate_column"]),
                baseline_column=str(item["baseline_column"]),
                metric=str(item["metric"]),
                horizon_weeks=int(item["horizon_weeks"]),
            )
        )
    return primary, secondary


def _target_column(horizon_weeks: int) -> str:
    return f"future_log_return_{horizon_weeks}"


def _mask_panel(
    panel: pd.DataFrame,
    candidate_col: str,
    baseline_col: str,
    target_col: str,
) -> pd.DataFrame:
    cols = [candidate_col, baseline_col, target_col]
    missing = [c for c in cols if c not in panel.columns]
    if missing:
        return pd.DataFrame()
    work = panel[cols].apply(pd.to_numeric, errors="coerce")
    return panel.loc[work.notna().all(axis=1)].copy()


def _inference_config(plan: AnalysisPlan, n_bootstrap: int | None = None) -> InferenceConfiguration:
    return InferenceConfiguration(
        enabled=True,
        n_bootstrap=n_bootstrap or plan.bootstrap_replicates,
        block_size=plan.block_length_weeks,
        ci_level=1.0 - plan.alpha,
        random_seed=plan.seed,
    )


def run_delta_contrast(
    panel: pd.DataFrame,
    spec: ContrastSpec,
    *,
    plan: AnalysisPlan,
    n_bootstrap: int | None = None,
    block_length_weeks: int | None = None,
) -> dict[str, Any]:
    target_col = _target_column(spec.horizon_weeks)
    masked = _mask_panel(panel, spec.candidate_column, spec.baseline_column, target_col)
    row: dict[str, Any] = {
        "contrast_id": spec.id,
        "candidate_column": spec.candidate_column,
        "baseline_column": spec.baseline_column,
        "metric": spec.metric,
        "horizon_weeks": spec.horizon_weeks,
        "target_column": target_col,
        "description": spec.description,
    }
    if masked.empty:
        row.update(
            {
                "status": "missing_columns_or_data",
                "n": 0,
                "rho_candidate": None,
                "rho_baseline": None,
                "delta": None,
                "p_value": 1.0,
                "p_holm": 1.0,
                "ci_low": None,
                "ci_high": None,
            }
        )
        return row

    metric_fn = NUMPY_METRIC_FUNCTIONS.get(spec.metric.lower())
    if metric_fn is None:
        row.update({"status": "unknown_metric", "n": int(len(masked))})
        return row

    cand = masked[spec.candidate_column].astype(float).to_numpy()
    base = masked[spec.baseline_column].astype(float).to_numpy()
    target = masked[target_col].astype(float).to_numpy()

    rho_cand = metric_fn(cand, target)
    rho_base = metric_fn(base, target)
    inference = _inference_config(plan, n_bootstrap=n_bootstrap)
    if block_length_weeks is not None:
        inference = InferenceConfiguration(
            enabled=inference.enabled,
            n_bootstrap=inference.n_bootstrap,
            block_size=int(block_length_weeks),
            ci_level=inference.ci_level,
            random_seed=inference.random_seed,
        )
    delta_result = compute_delta_inference(
        spec.metric,
        cand,
        base,
        target,
        metric_fn=metric_fn,
        inference=inference,
    )

    row.update(
        {
            "status": "ok" if delta_result.value is not None else "undefined",
            "n": delta_result.n,
            "rho_candidate": rho_cand,
            "rho_baseline": rho_base,
            "delta": delta_result.value,
            "p_value": delta_result.p_value if delta_result.p_value is not None else 1.0,
            "ci_low": delta_result.ci_low,
            "ci_high": delta_result.ci_high,
            "n_bootstrap": delta_result.n_bootstrap,
        }
    )
    return row


def run_marginal_correlation(
    panel: pd.DataFrame,
    signal_column: str,
    *,
    plan: AnalysisPlan,
    horizon_weeks: int,
    n_bootstrap: int | None = None,
) -> dict[str, Any]:
    """Correlação marginal (exploratória) sinal × retorno — não é o teste Δ principal."""

    target_col = _target_column(horizon_weeks)
    if signal_column not in panel.columns or target_col not in panel.columns:
        return {
            "signal_column": signal_column,
            "horizon_weeks": horizon_weeks,
            "status": "missing_columns",
            "n": 0,
        }
    predictor = panel[signal_column]
    target = panel[target_col]
    inference = _inference_config(plan, n_bootstrap=n_bootstrap)
    result = compute_metric_with_inference(
        plan.primary_metric,
        predictor,
        target,
        inference=inference,
    )
    return {
        "signal_column": signal_column,
        "horizon_weeks": horizon_weeks,
        "metric": plan.primary_metric,
        "target_column": target_col,
        "status": "ok" if result.value is not None else "undefined",
        "n": result.n,
        "estimate": result.value,
        "p_value": result.p_value,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "n_bootstrap": result.n_bootstrap,
    }


def apply_holm_secondary(
    rows: list[dict[str, Any]],
    *,
    alpha: float,
) -> list[dict[str, Any]]:
    from modules.experiment.campaign.iti_v2_statistics import holm_adjust

    p_values: list[float] = []
    indices: list[int] = []
    for index, row in enumerate(rows):
        p = row.get("p_value")
        if p is None or not np.isfinite(p):
            rows[index]["p_holm"] = 1.0
            rows[index]["significant_holm"] = False
            continue
        p_values.append(float(p))
        indices.append(index)

    if not p_values:
        return rows

    adjusted = holm_adjust(p_values, alpha=alpha)
    for adj, row_index in zip(adjusted, indices, strict=True):
        rows[row_index]["p_holm"] = adj["p_holm"]
        rows[row_index]["significant_holm"] = adj["significant_at_alpha"]
    return rows


def build_result_registry(
    *,
    run_id: str,
    execution_mode: str,
    primary_delta: dict[str, Any],
    secondary_rows: list[dict[str, Any]],
    marginal_primary: dict[str, Any],
    horizons_exploratory: list[dict[str, Any]],
    artifacts: dict[str, str],
    human_reference_status: str = "pending_blind_annotation",
) -> dict[str, Any]:
    return {
        "schema_version": "iti_v2_result_registry_1",
        "run_id": run_id,
        "execution_mode": execution_mode,
        "human_reference_status": human_reference_status,
        "primary_test": primary_delta,
        "secondary_family": secondary_rows,
        "marginal_primary_signal": marginal_primary,
        "horizon_sensitivity": horizons_exploratory,
        "artifacts": artifacts,
    }


def write_contrast_tables(
    run_dir: Path,
    primary: dict[str, Any],
    secondary: list[dict[str, Any]],
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    primary_path = run_dir / "table_primary.json"
    primary_path.write_text(json.dumps(primary, indent=2), encoding="utf-8")
    paths["table_primary"] = primary_path

    sec_path = run_dir / "table_secondary.json"
    sec_path.write_text(json.dumps(secondary, indent=2), encoding="utf-8")
    paths["table_secondary"] = sec_path

    df = pd.DataFrame(secondary)
    csv_path = run_dir / "table_secondary.csv"
    df.to_csv(csv_path, index=False)
    paths["table_secondary_csv"] = csv_path
    return paths
