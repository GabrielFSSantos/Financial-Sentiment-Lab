"""Artefatos extras do plano ITI-v2: holdout, sensibilidade de bloco, máscaras, corpus e recursos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from modules.experiment.campaign.iti_v2_contrasts import (
    ContrastSpec,
    apply_holm_secondary,
    load_contrast_plan,
    run_delta_contrast,
)
from modules.research.config.analysis_plan import AnalysisPlan
def _mask_series(
    panel: pd.DataFrame,
    candidate_col: str,
    baseline_col: str,
    target_col: str,
) -> pd.Series:
    cols = [candidate_col, baseline_col, target_col]
    work = panel[cols].apply(pd.to_numeric, errors="coerce")
    return work.notna().all(axis=1)


def export_contrast_masks(
    panel: pd.DataFrame,
    specs: list[ContrastSpec],
    out_path: Path,
) -> Path:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        target_col = f"future_log_return_{spec.horizon_weeks}"
        mask = _mask_series(panel, spec.candidate_column, spec.baseline_column, target_col)
        for index, included in mask.items():
            row = panel.loc[index]
            rows.append(
                {
                    "contrast_id": spec.id,
                    "row_index": int(index),
                    "included": bool(included),
                    "company_id": row.get("company_id", ""),
                    "period_end": row.get("period_end", row.get("date", "")),
                    "candidate_column": spec.candidate_column,
                    "baseline_column": spec.baseline_column,
                    "target_column": target_col,
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(out_path, index=False)
    return out_path


def export_global_intersection_mask(
    panel: pd.DataFrame,
    specs: list[ContrastSpec],
    out_path: Path,
) -> Path:
    masks: list[pd.Series] = []
    for spec in specs:
        target_col = f"future_log_return_{spec.horizon_weeks}"
        masks.append(
            _mask_series(panel, spec.candidate_column, spec.baseline_column, target_col)
        )
    if not masks:
        pd.DataFrame().to_csv(out_path, index=False)
        return out_path
    combined = masks[0]
    for extra in masks[1:]:
        combined = combined & extra
    out = panel.loc[combined].copy()
    out["mask_name"] = "global_intersection_secondary_family"
    out.to_csv(out_path, index=False)
    return out_path


def run_block_sensitivity_primary(
    panel: pd.DataFrame,
    primary_spec: ContrastSpec,
    *,
    plan: AnalysisPlan,
    block_sizes: tuple[int, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for block_size in block_sizes:
        row = run_delta_contrast(
            panel,
            primary_spec,
            plan=plan,
            block_length_weeks=int(block_size),
        )
        row["block_length_weeks"] = int(block_size)
        row["sensitivity"] = block_size != plan.block_length_weeks
        rows.append(row)
    return rows


def evaluate_split_contrasts(
    panel: pd.DataFrame,
    *,
    split_label: str,
    plan: AnalysisPlan,
    contrast_plan_path: Path,
) -> dict[str, Any]:
    primary_spec, secondary_specs = load_contrast_plan(contrast_plan_path)
    primary_delta = run_delta_contrast(panel, primary_spec, plan=plan)
    secondary_rows = [
        run_delta_contrast(panel, spec, plan=plan) for spec in secondary_specs
    ]
    secondary_rows = apply_holm_secondary(secondary_rows, alpha=plan.alpha)
    return {
        "split": split_label,
        "n_panel": int(len(panel)),
        "execution_mode": "exploratory",
        "note": "Holdout não é confirmatório sem referência humana independente (P06).",
        "primary_test": primary_delta,
        "secondary_family": secondary_rows,
    }


def build_table_corpus(corpus_dir: Path, out_path: Path) -> Path:
    manifest_path = corpus_dir / "corpus_manifest.json"
    selection_path = corpus_dir / "selection_report.json"
    payload: dict[str, Any] = {"corpus_dir": str(corpus_dir)}
    if manifest_path.is_file():
        payload["corpus_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if selection_path.is_file():
        payload["selection_report"] = json.loads(selection_path.read_text(encoding="utf-8"))
    exclusions = corpus_dir / "exclusions.csv"
    if exclusions.is_file() and exclusions.stat().st_size > 0:
        try:
            excl = pd.read_csv(exclusions)
        except pd.errors.EmptyDataError:
            excl = pd.DataFrame()
        payload["n_exclusions"] = int(len(excl))
        payload["exclusion_reasons"] = (
            excl["reason"].value_counts().to_dict() if "reason" in excl.columns else {}
        )
    split_path = corpus_dir / "split_manifest.json"
    if split_path.is_file():
        payload["split_manifest"] = json.loads(split_path.read_text(encoding="utf-8"))
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def build_table_resources(run_dir: Path, out_path: Path) -> Path:
    meta_path = run_dir / "sdumont_job_metadata.txt"
    manifest_path = run_dir / "run_manifest.json"
    inference_path = run_dir / "inference_manifest.json"
    resources: dict[str, Any] = {"run_dir": str(run_dir)}
    if meta_path.is_file():
        resources["sdumont_metadata_raw"] = meta_path.read_text(encoding="utf-8")
    if manifest_path.is_file():
        resources["run_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if inference_path.is_file():
        resources["inference_manifest"] = json.loads(inference_path.read_text(encoding="utf-8"))
    job_srm = Path(__file__).resolve().parents[3] / "jobs/sdumont/run_iti_v2.srm"
    if job_srm.is_file():
        resources["slurm_requested"] = {
            "source": str(job_srm.relative_to(Path(__file__).resolve().parents[3])),
            "note": "Valores solicitados no script; uso observado em sdumont_job_metadata quando run HPC.",
        }
    out_path.write_text(json.dumps(resources, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def count_primary_view_predictions(predictions_path: Path, primary_view: str) -> dict[str, int]:
    if not predictions_path.is_file():
        return {"n_rows": 0, "n_articles_ok": 0}
    frame = pd.read_csv(predictions_path)
    if "view_id" in frame.columns:
        frame = frame.loc[frame["view_id"].astype(str) == primary_view]
    ok = frame.loc[frame["status"] == "ok"] if "status" in frame.columns else frame
    n_articles = int(ok["news_id"].nunique()) if "news_id" in ok.columns else int(len(ok))
    return {"n_rows": int(len(frame)), "n_articles_ok": n_articles}
