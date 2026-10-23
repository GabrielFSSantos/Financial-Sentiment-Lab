"""Inventário e manifesto de corpus (P02)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from modules.datasets import PROJECT_ROOT


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_corpus_manifest(
    csv_path: Path,
    *,
    rules_version: str = "iti_v2_p02",
    tz_name: str = "America/Sao_Paulo",
) -> dict:
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    frame = pd.read_csv(csv_path)
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_path": str(
            csv_path.relative_to(PROJECT_ROOT)
            if csv_path.is_relative_to(PROJECT_ROOT)
            else csv_path
        ),
        "sha256": file_sha256(csv_path),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
        "rules_version": rules_version,
        "timezone": tz_name,
    }
    if "data" in frame.columns:
        dates = pd.to_datetime(frame["data"], errors="coerce")
        manifest["date_min"] = str(dates.min())
        manifest["date_max"] = str(dates.max())
    return manifest


def write_inventory(output_dir: Path, manifest: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "corpus_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
