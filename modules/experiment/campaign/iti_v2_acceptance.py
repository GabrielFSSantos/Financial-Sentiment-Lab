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


def _check_run(run_id: str) -> list[AcceptanceResult]:
    run_dir = PROJECT_ROOT / "outputs/campaigns/iti_v2" / run_id
    artifacts = (
        "iti_daily.csv",
        "iti_weekly_signals.csv",
        "aligned_panel.csv",
        "alignment_audit.csv",
        "metrics_primary.json",
        "metrics_inference.json",
        "metrics_by_horizon.csv",
        "report.md",
        "_SUCCESS",
    )
    results: list[AcceptanceResult] = []
    for name in artifacts:
        path = run_dir / name
        results.append(AcceptanceResult(f"P07:{name}", path.is_file(), str(path)))
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
        results.extend(_check_run(run_id))
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
