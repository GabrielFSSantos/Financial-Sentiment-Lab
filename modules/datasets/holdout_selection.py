"""Seleção de holdout temporal sem consultar retornos (P02/P11)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from modules.datasets.corpus_inventory import file_sha256


def _ids_sha256(news_ids: list[str]) -> str:
    payload = "\n".join(sorted(str(x) for x in news_ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_calendar_holdout(
    canonical_csv: Path,
    output_dir: Path,
    *,
    holdout_weeks: int = 12,
    date_column: str = "data",
    news_id_column: str = "news_id",
) -> dict:
    """Reserva as últimas N semanas civis do corpus; não usa mercado nem predições."""

    frame = pd.read_csv(canonical_csv)
    if news_id_column not in frame.columns and "id" in frame.columns:
        frame[news_id_column] = frame["id"]
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    frame = frame.assign(_date=dates).dropna(subset=["_date"])
    if frame.empty:
        raise ValueError("Nenhuma data válida no corpus canônico.")

    date_max = frame["_date"].max()
    cutoff = date_max - pd.Timedelta(weeks=holdout_weeks)

    development = frame.loc[frame["_date"] < cutoff]
    holdout = frame.loc[frame["_date"] >= cutoff]

    output_dir.mkdir(parents=True, exist_ok=True)
    holdout_path = output_dir / "holdout_news_ids.csv"
    holdout[[news_id_column, date_column]].to_csv(holdout_path, index=False)

    split = {
        "generated_at": datetime.now(UTC).isoformat(),
        "development": {
            "status": "active",
            "n_articles": int(len(development)),
            "date_max_exclusive": cutoff.isoformat(),
            "note": "amostra manual n=100 permanece apenas desenvolvimento",
        },
        "external_holdout": {
            "status": "selected",
            "reserved": True,
            "selection_rule": f"calendar_last_{holdout_weeks}_weeks",
            "holdout_weeks": holdout_weeks,
            "cutoff_date_inclusive": cutoff.isoformat(),
            "corpus_date_min": str(frame["_date"].min()),
            "corpus_date_max": str(date_max),
            "n_articles": int(len(holdout)),
            "news_ids_file": str(holdout_path.name),
            "news_ids_sha256": _ids_sha256(holdout[news_id_column].astype(str).tolist()),
        },
        "calibration": {"status": "not_allocated"},
    }

    manifest_path = output_dir / "split_manifest.json"
    manifest_path.write_text(
        json.dumps(split, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report = {
        "canonical_sha256": file_sha256(canonical_csv),
        "holdout_file_sha256": file_sha256(holdout_path),
        "split_manifest_sha256": file_sha256(manifest_path),
    }
    (output_dir / "holdout_selection_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return split
