"""Verificação automática de critérios do plano ITI-v2 (P08/P11/P12)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.iti_v2_inference import ITI_V2_PREDICTION_COLUMNS
from modules.experiment.campaign.protocol_lock import require_protocol_lock
from modules.research.config.analysis_plan import load_analysis_plan


@dataclass
class AcceptanceResult:
    name: str
    ok: bool
    detail: str


def _check_p02(corpus_dir: Path) -> list[AcceptanceResult]:
    required = (
        "corpus_manifest.json",
        "articles_canonical.csv",
        "dedup_map.csv",
        "coverage_daily.csv",
        "split_manifest.json",
        "selection_report.json",
    )
    results: list[AcceptanceResult] = []
    for name in required:
        path = corpus_dir / name
        results.append(
            AcceptanceResult(
                f"P02:{name}",
                path.is_file(),
                str(path),
            )
        )
    return results


def _check_lock(corpus_dir: Path) -> AcceptanceResult:
    try:
        lock = require_protocol_lock(corpus_dir)
        hashes = lock.get("hashes", {})
        ok = bool(hashes.get("protocol_sha256") and hashes.get("corpus_source_sha256"))
        return AcceptanceResult("P11:protocol_lock", ok, json.dumps(hashes, indent=0)[:200])
    except Exception as error:
        return AcceptanceResult("P11:protocol_lock", False, str(error))


def _check_predictions(path: Path) -> list[AcceptanceResult]:
    results: list[AcceptanceResult] = []
    if not path.is_file():
        results.append(AcceptanceResult("P03:predictions.csv", False, "ausente"))
        return results
    frame = pd.read_csv(path, nrows=5000)
    missing = [c for c in ITI_V2_PREDICTION_COLUMNS if c not in frame.columns]
    results.append(
        AcceptanceResult(
            "P03:prediction_columns",
            not missing,
            f"faltando: {missing}" if missing else f"{len(frame)} linhas",
        )
    )
    ok_rows = frame.loc[frame["status"] == "ok"]
    if not ok_rows.empty:
        sums = (
            ok_rows["p_negative"].astype(float)
            + ok_rows["p_neutral"].astype(float)
            + ok_rows["p_positive"].astype(float)
        )
        bad = (sums - 1.0).abs() > 1e-5
        results.append(
            AcceptanceResult(
                "P03:probability_sum",
                not bad.any(),
                f"{int(bad.sum())} linhas fora da tolerância",
            )
        )
    return results


def _check_temporal_coverage(run_dir: Path, corpus_dir: Path) -> AcceptanceResult:
    """Bloqueador: sinais não podem extrapolar cobertura elegível do corpus (P08)."""

    manifest = corpus_dir / "corpus_manifest.json"
    weekly_path = run_dir / "iti_weekly_signals.csv"
    panel_path = run_dir / "aligned_panel.csv"
    if not manifest.is_file() or not weekly_path.is_file():
        return AcceptanceResult(
            "P08:temporal_signal_coverage",
            False,
            "manifest ou iti_weekly ausente",
        )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    date_max = payload.get("date_max")
    if not date_max:
        return AcceptanceResult(
            "P08:temporal_signal_coverage",
            False,
            "date_max ausente no manifest",
        )
    corpus_end = pd.Timestamp(date_max).normalize()
    weekly = pd.read_csv(weekly_path, parse_dates=["signal_cutoff_at"], low_memory=False)
    if "signal_cutoff_at" not in weekly.columns:
        return AcceptanceResult(
            "P08:temporal_signal_coverage",
            False,
            "signal_cutoff_at ausente",
        )
    max_cutoff = pd.to_datetime(weekly["signal_cutoff_at"], errors="coerce").max()
    ok_cutoff = pd.Timestamp(max_cutoff).normalize() <= corpus_end
    detail = f"max(signal_cutoff_at)={max_cutoff}; corpus_end={corpus_end}"
    if panel_path.is_file():
        panel = pd.read_csv(panel_path, parse_dates=["signal_cutoff_at"], low_memory=False)
        if "signal_cutoff_at" in panel.columns and "iti_v2_h7" in panel.columns:
            pmax = pd.to_datetime(panel["signal_cutoff_at"], errors="coerce").max()
            ok_panel = pd.Timestamp(pmax).normalize() <= corpus_end
            ok_cutoff = ok_cutoff and ok_panel
            detail += f"; panel_max_cutoff={pmax}"
    return AcceptanceResult("P08:temporal_signal_coverage", ok_cutoff, detail)


def _check_run(run_id: str, corpus_dir: Path | None = None) -> list[AcceptanceResult]:
    run_dir = PROJECT_ROOT / "outputs/campaigns/iti_v2" / run_id
    artifacts = (
        "iti_daily.csv",
        "iti_weekly_signals.csv",
        "iti_weekly_legacy_c.csv",
        "aligned_panel.csv",
        "alignment_audit.csv",
        "metrics_primary.json",
        "metrics_primary_delta.json",
        "metrics_secondary.json",
        "result_registry.json",
        "table_primary.json",
        "table_secondary.csv",
        "metrics_inference.json",
        "metrics_by_horizon.csv",
        "report.md",
        "_SUCCESS",
    )
    results: list[AcceptanceResult] = []
    for name in artifacts:
        path = run_dir / name
        results.append(AcceptanceResult(f"P07:{name}", path.is_file(), str(path)))
    if corpus_dir is not None:
        results.append(_check_temporal_coverage(run_dir, corpus_dir))
    return results


def _check_configs() -> list[AcceptanceResult]:
    results: list[AcceptanceResult] = []
    protocol = PROJECT_ROOT / "configs/campaigns/iti_v2/protocol.yaml"
    raw = yaml.safe_load(protocol.read_text(encoding="utf-8"))
    results.append(
        AcceptanceResult(
            "P04:index_version",
            raw.get("index", {}).get("version") == "iti_v2",
            str(raw.get("index", {}).get("version")),
        )
    )
    try:
        load_analysis_plan(
            PROJECT_ROOT / "configs/campaigns/iti_v2/analysis_plan.yaml"
        )
        results.append(AcceptanceResult("P05:analysis_plan", True, "loader ok"))
    except Exception as error:
        results.append(AcceptanceResult("P05:analysis_plan", False, str(error)))
    return results


def run_acceptance(
    *,
    corpus_dir: Path,
    run_id: str | None = None,
) -> tuple[bool, list[AcceptanceResult]]:
    corpus_dir = corpus_dir if corpus_dir.is_absolute() else PROJECT_ROOT / corpus_dir
    results: list[AcceptanceResult] = []
    results.extend(_check_configs())
    results.extend(_check_p02(corpus_dir))
    results.append(_check_lock(corpus_dir))
    if run_id:
        run_dir = PROJECT_ROOT / "outputs/campaigns/iti_v2" / run_id
        pred = run_dir / "predictions.csv"
        results.extend(_check_predictions(pred))
        results.extend(_check_run(run_id, corpus_dir=corpus_dir))
    ok = all(item.ok for item in results)
    return ok, results


def format_report(results: list[AcceptanceResult]) -> str:
    lines = ["# Aceite ITI-v2", ""]
    for item in results:
        mark = "OK" if item.ok else "FALHA"
        lines.append(f"- [{mark}] **{item.name}** — {item.detail}")
    lines.append("")
    lines.append(
        f"**Resumo:** {sum(1 for r in results if r.ok)}/{len(results)} critérios atendidos."
    )
    return "\n".join(lines)
