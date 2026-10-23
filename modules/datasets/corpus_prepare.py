"""Preparação P02: manifesto, deduplicação, cobertura e splits (somente leitura do CSV fonte)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pandas as pd

from modules.datasets.corpus_inventory import build_corpus_manifest, file_sha256


def _normalize_url(url: str) -> str:
    if not url or not isinstance(url, str):
        return ""
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", "", ""))


def _body_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _assign_news_ids(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "news_id" not in out.columns:
        out["news_id"] = out["id"].astype(str) if "id" in out.columns else out.index.astype(str)
    out["article_version_id"] = out["news_id"]
    if "empresa" in out.columns:
        out["company_id"] = out["empresa"].astype(str).str.strip()
    else:
        out["company_id"] = "unknown"
    return out


def build_dedup_map(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (canonical, dedup_map). Mantém primeira ocorrência por URL canônica."""

    work = _assign_news_ids(frame)
    work["_url_norm"] = work.get("url", pd.Series(dtype=str)).map(_normalize_url)
    work["_body_hash"] = work.get("noticia", pd.Series(dtype=str)).map(_body_hash)

    dedup_rows: list[dict[str, object]] = []
    keep_indices: list[int] = []
    seen_url: dict[str, str] = {}
    seen_body_title: dict[tuple[str, str], str] = {}

    for idx, row in work.iterrows():
        nid = str(row["news_id"])
        url_key = row["_url_norm"]
        title = str(row.get("titulo", ""))
        body_key = (title, row["_body_hash"])

        representative = nid
        rule = "unique"
        if url_key and url_key in seen_url:
            representative = seen_url[url_key]
            rule = "url_canonical"
        elif body_key in seen_body_title:
            representative = seen_body_title[body_key]
            rule = "title_body_hash"
        else:
            keep_indices.append(idx)
            if url_key:
                seen_url[url_key] = nid
            seen_body_title[body_key] = nid

        if representative != nid or rule != "unique":
            dedup_rows.append(
                {
                    "duplicate_news_id": nid,
                    "representative_news_id": representative,
                    "rule": rule,
                }
            )

    canonical = work.loc[keep_indices].drop(columns=["_url_norm", "_body_hash"], errors="ignore")
    dedup_map = pd.DataFrame(dedup_rows)
    return canonical, dedup_map


def build_coverage_daily(frame: pd.DataFrame) -> pd.DataFrame:
    work = _assign_news_ids(frame)
    work["date"] = pd.to_datetime(work["data"], errors="coerce").dt.date
    grouped = (
        work.groupby(["date", "fonte"], dropna=False)
        .agg(n_articles=("news_id", "nunique"))
        .reset_index()
    )
    grouped["coverage_status"] = "known"
    return grouped


def build_exclusions(frame: pd.DataFrame) -> pd.DataFrame:
    work = _assign_news_ids(frame)
    rows: list[dict[str, object]] = []
    for _, row in work.iterrows():
        reason = None
        if not str(row.get("noticia", "")).strip():
            reason = "empty_body"
        elif pd.isna(row.get("data")):
            reason = "missing_date"
        if reason:
            rows.append({"news_id": row["news_id"], "primary_reason": reason})
    return pd.DataFrame(rows)


def default_split_manifest(
    date_min: str | None,
    date_max: str | None,
    *,
    holdout_reserved: bool = False,
) -> dict:
    """Split exploratório: não define holdout sem inventário formal de inspeção."""

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "development": {"note": "amostra manual histórica n=100; não reutilizar como teste externo"},
        "external_holdout": {
            "status": "pending_selection",
            "reserved": holdout_reserved,
            "date_min": date_min,
            "date_max": date_max,
            "instruction": "Selecionar janela sem consultar retornos ou novas predições",
        },
        "calibration": {"status": "not_allocated"},
    }


def run_p02_prepare(
    csv_path: Path,
    output_dir: Path,
    *,
    tz_name: str = "America/Sao_Paulo",
) -> dict[str, Path]:
    """Gera todos os artefatos P02 em output_dir (não modifica o CSV fonte)."""

    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(csv_path)
    manifest = build_corpus_manifest(csv_path, tz_name=tz_name)
    manifest["pipeline"] = "iti_v2_p02"

    canonical, dedup_map = build_dedup_map(raw)
    coverage = build_coverage_daily(canonical)
    exclusions = build_exclusions(raw)

    paths: dict[str, Path] = {}
    paths["corpus_manifest"] = output_dir / "corpus_manifest.json"
    paths["corpus_manifest"].write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    paths["articles_canonical"] = output_dir / "articles_canonical.csv"
    canonical.to_csv(paths["articles_canonical"], index=False)

    paths["article_company"] = output_dir / "article_company.csv"
    ac = canonical[["news_id", "article_version_id", "company_id"]].drop_duplicates()
    ac.to_csv(paths["article_company"], index=False)

    paths["dedup_map"] = output_dir / "dedup_map.csv"
    dedup_map.to_csv(paths["dedup_map"], index=False)

    paths["coverage_daily"] = output_dir / "coverage_daily.csv"
    coverage.to_csv(paths["coverage_daily"], index=False)

    paths["exclusions"] = output_dir / "exclusions.csv"
    exclusions.to_csv(paths["exclusions"], index=False)

    split = default_split_manifest(manifest.get("date_min"), manifest.get("date_max"))
    paths["split_manifest"] = output_dir / "split_manifest.json"
    paths["split_manifest"].write_text(
        json.dumps(split, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    selection = {
        "source_sha256": file_sha256(csv_path),
        "rows_raw": int(len(raw)),
        "rows_canonical": int(len(canonical)),
        "duplicates_mapped": int(len(dedup_map)),
        "exclusions": int(len(exclusions)),
    }
    paths["selection_report"] = output_dir / "selection_report.json"
    paths["selection_report"].write_text(
        json.dumps(selection, indent=2), encoding="utf-8"
    )
    return paths
