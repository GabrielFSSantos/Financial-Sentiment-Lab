"""Congelamento de protocolo ITI-v2 (P11)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from modules.datasets.corpus_inventory import file_sha256
from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.iti_v2_protocol import load_iti_v2_protocol
from modules.research.config.analysis_plan import load_analysis_plan


class ProtocolLockError(RuntimeError):
    """Pré-requisitos de lock ausentes ou inválidos."""


def _git_head(project_root: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=project_root,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _model_weights_sha(project_root: Path, model_key: str = "finbert_ptbr") -> str | None:
    models_path = project_root / "configs/models.yaml"
    data = yaml.safe_load(models_path.read_text(encoding="utf-8"))
    model = data.get("models", {}).get(model_key, {})
    source = model.get("source", {})
    return source.get("weights_sha256")


def build_protocol_lock(
    *,
    corpus_dir: Path,
    protocol_path: Path,
    analysis_plan_path: Path,
    project_root: Path = PROJECT_ROOT,
    primary_hypothesis: str = (
        "Correlação de Spearman entre ITI-v2 (meia-vida primária) e retorno log futuro semanal"
    ),
    execution_mode: str = "exploratory",
    model_key: str = "finbert_ptbr",
) -> dict[str, Any]:
    """Monta payload de lock a partir de artefatos P02 e configs normativas."""

    manifest_path = corpus_dir / "corpus_manifest.json"
    canonical_path = corpus_dir / "articles_canonical.csv"
    split_path = corpus_dir / "split_manifest.json"
    for required in (manifest_path, canonical_path, split_path):
        if not required.is_file():
            raise ProtocolLockError(f"Artefato P02 ausente: {required}")

    protocol = load_iti_v2_protocol(protocol_path)
    analysis = load_analysis_plan(analysis_plan_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    lock: dict[str, Any] = {
        "schema_version": "iti_v2_protocol_lock_1",
        "locked_at": datetime.now(UTC).isoformat(),
        "execution_mode": execution_mode,
        "primary_hypothesis": primary_hypothesis,
        "git_commit": _git_head(project_root),
        "hashes": {
            "corpus_source_sha256": manifest.get("sha256"),
            "articles_canonical_sha256": file_sha256(canonical_path),
            "corpus_manifest_sha256": file_sha256(manifest_path),
            "split_manifest_sha256": file_sha256(split_path),
            "protocol_sha256": protocol.content_sha256,
            "analysis_plan_sha256": file_sha256(analysis_plan_path),
            f"{model_key}_weights_sha256": _model_weights_sha(project_root, model_key),
        },
        "references": {
            "corpus_dir": str(corpus_dir),
            "protocol_path": str(protocol_path),
            "analysis_plan_path": str(analysis_plan_path),
            "protocol_version": protocol.raw.get("protocol_version"),
            "index_version": protocol.index_version,
            "primary_half_life_days": protocol.raw.get("index", {}).get(
                "primary_half_life_days"
            ),
            "analysis_primary_metric": analysis.primary_metric,
            "analysis_primary_horizon_weeks": analysis.primary_horizon_weeks,
        },
        "holdout_status": json.loads(split_path.read_text(encoding="utf-8")).get(
            "external_holdout", {}
        ),
    }
    return lock


def write_protocol_lock(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def require_protocol_lock(corpus_dir: Path) -> dict[str, Any]:
    path = corpus_dir / "protocol_lock.json"
    if not path.is_file():
        raise ProtocolLockError(
            f"protocol_lock.json ausente em {corpus_dir}. Rode lock-protocol após prepare."
        )
    return json.loads(path.read_text(encoding="utf-8"))
