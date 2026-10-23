"""Inferência ITI-v2: corpus canônico P02 + views textuais (P03)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

import os

from modules.datasets.text_views import build_document_view, build_entity_context_view
from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.protocol_lock import require_protocol_lock
from modules.models.config.loader import load_models_configuration
from modules.models.inference_cache import (
    append_cache_entry,
    inference_cache_key,
    read_cache_hits,
    write_batch_parquet,
)
from modules.models.iti_v2_contract import validate_iti_v2_prediction
from modules.models.registry import create_model_registry

ITI_V2_PREDICTION_COLUMNS: tuple[str, ...] = (
    "news_id",
    "article_version_id",
    "company_id",
    "date",
    "view_id",
    "view_hash",
    "model_key",
    "model_revision_sha",
    "p_negative",
    "p_neutral",
    "p_positive",
    "predicted_label",
    "continuous_sentiment",
    "token_count_original",
    "token_count_used",
    "truncated",
    "target_visible",
    "status",
)


def _entity_key_from_company(company_id: str) -> str:
    return str(company_id).strip().lower().split()[0]


def _configured_view_ids(protocol: dict[str, object]) -> list[str]:
    text = protocol.get("text", {})
    primary = str(text.get("primary_view", "entity_context_v1"))
    comparison = str(text.get("comparison_view", "document_v1"))
    override = os.environ.get("ITI_V2_VIEWS", "").strip()
    if override:
        return [part.strip() for part in override.split(",") if part.strip()]
    views = [primary]
    if comparison and comparison not in views:
        views.append(comparison)
    return views


def _build_view(
    view_id: str,
    title: str,
    body: str,
    company_id: str,
    *,
    neighbors: int,
):
    if view_id == "document_v1":
        return build_document_view(title, body)
    return build_entity_context_view(
        title,
        body,
        _entity_key_from_company(company_id),
        neighbors=neighbors,
    )


def _model_revision_sha(model_configuration: object) -> str:
    source = getattr(model_configuration, "source", None) or {}
    return str(source.get("weights_sha256", "unknown"))


def run_iti_v2_inference(
    run_id: str,
    *,
    corpus_dir: Path,
    output_path: Path | None = None,
    model_key: str = "finbert_ptbr",
    limit: int | None = None,
    batch_size: int = 32,
    use_cache: bool = True,
) -> Path:
    """Gera predictions.csv no contrato ITI-v2 a partir de articles_canonical."""

    require_protocol_lock(corpus_dir)
    canonical_path = corpus_dir / "articles_canonical.csv"
    if not canonical_path.is_file():
        raise FileNotFoundError(f"Execute prepare antes de infer: {canonical_path}")

    out_dir = PROJECT_ROOT / "outputs/campaigns/iti_v2" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path or (out_dir / "predictions.csv")
    cache_dir = out_dir / "inference_cache"

    protocol_path = PROJECT_ROOT / "configs/campaigns/iti_v2/protocol.yaml"
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    neighbors = int(protocol.get("text", {}).get("context_neighbors", 1))
    max_length = int(protocol.get("text", {}).get("max_length", 512))

    frame = pd.read_csv(canonical_path)
    rows: list[dict[str, Any]] = []
    view_ids = _configured_view_ids(protocol)
    done_pairs: set[tuple[str, str]] = set()
    if output_path.is_file():
        existing = pd.read_csv(output_path)
        if "news_id" in existing.columns and not existing.empty:
            rows = existing.to_dict(orient="records")
            if "view_id" in existing.columns:
                done_pairs = {
                    (str(n), str(v))
                    for n, v in zip(
                        existing["news_id"].astype(str),
                        existing["view_id"].astype(str),
                        strict=True,
                    )
                }
            else:
                done_pairs = {
                    (str(n), view_ids[0]) for n in existing["news_id"].astype(str)
                }

    if limit is not None and limit > 0:
        frame = frame.head(limit)

    models_configuration = load_models_configuration(project_root=PROJECT_ROOT)
    model_configuration = next(
        (m for m in models_configuration.models if m.key == model_key and m.enabled),
        None,
    )
    if model_configuration is None:
        raise ValueError(f"Modelo {model_key} não habilitado em models.yaml")
    if not model_configuration.model_dir.is_dir():
        raise FileNotFoundError(f"model_dir ausente: {model_configuration.model_dir}")

    revision_sha = _model_revision_sha(model_configuration)
    registry = create_model_registry(models_configuration)
    registered = registry.create(model_configuration, load=True)

    pending_texts: list[str] = []
    pending_meta: list[dict[str, Any]] = []

    def flush_batch() -> None:
        if not pending_texts:
            return
        predictions = registered.predict(pending_texts)
        for meta, prediction in zip(pending_meta, predictions, strict=True):
            validate_iti_v2_prediction(prediction)
            row = dict(meta)
            row.update(
                {
                    "p_negative": prediction.prob_negative,
                    "p_neutral": prediction.prob_neutral,
                    "p_positive": prediction.prob_positive,
                    "predicted_label": prediction.predicted_label,
                    "continuous_sentiment": prediction.continuous_sentiment,
                    "status": "ok",
                }
            )
            rows.append(row)
            if use_cache and meta.get("_cache_key"):
                append_cache_entry(
                    cache_dir,
                    meta["_cache_key"],
                    {
                        "p_negative": row["p_negative"],
                        "p_neutral": row["p_neutral"],
                        "p_positive": row["p_positive"],
                        "predicted_label": row["predicted_label"],
                    },
                )
        pending_texts.clear()
        pending_meta.clear()

    for record in frame.itertuples(index=False):
        news_id = str(getattr(record, "news_id", getattr(record, "id", "")))
        company_id = str(getattr(record, "company_id", getattr(record, "empresa", "")))
        date = str(getattr(record, "data", ""))
        title = str(getattr(record, "titulo", ""))
        body = str(getattr(record, "noticia", ""))
        article_version_id = str(
            getattr(record, "article_version_id", news_id)
        )

        for view_id in view_ids:
            if (news_id, view_id) in done_pairs:
                continue

            view = _build_view(
                view_id,
                title,
                body,
                company_id,
                neighbors=neighbors,
            )
            base_row: dict[str, Any] = {
                "news_id": news_id,
                "article_version_id": article_version_id,
                "company_id": company_id,
                "date": date,
                "view_id": view.view_id,
                "view_hash": view.view_hash,
                "model_key": model_key,
                "model_revision_sha": revision_sha,
                "token_count_original": view.token_count_original,
                "token_count_used": min(view.token_count_original or 0, max_length),
                "truncated": bool(
                    (view.token_count_original or 0) > max_length
                ),
                "target_visible": view.target_visible,
            }

            if view.status != "ok" or not view.target_visible or not view.text.strip():
                base_row.update(
                    {
                        "p_negative": pd.NA,
                        "p_neutral": pd.NA,
                        "p_positive": pd.NA,
                        "predicted_label": pd.NA,
                        "continuous_sentiment": pd.NA,
                        "status": "not_evaluable",
                    }
                )
                rows.append(base_row)
                continue

            cache_key = inference_cache_key(
                effective_text_hash=view.view_hash,
                view_id=view.view_id,
                model_key=model_key,
                model_revision_sha=revision_sha,
            )
            base_row["_cache_key"] = cache_key

            if use_cache:
                hits = read_cache_hits(cache_dir, [cache_key])
                if cache_key in hits:
                    hit = hits[cache_key]
                    base_row.update(
                        {
                            "p_negative": hit["p_negative"],
                            "p_neutral": hit["p_neutral"],
                            "p_positive": hit["p_positive"],
                            "predicted_label": hit["predicted_label"],
                            "continuous_sentiment": float(hit["p_positive"])
                            - float(hit["p_negative"]),
                            "status": "ok",
                        }
                    )
                    rows.append({k: v for k, v in base_row.items() if k != "_cache_key"})
                    continue

            pending_meta.append(base_row)
            pending_texts.append(view.text)
            if len(pending_texts) >= batch_size:
                flush_batch()

    flush_batch()
    registered.unload()

    result = pd.DataFrame(rows)
    for col in ITI_V2_PREDICTION_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA
    result = result[list(ITI_V2_PREDICTION_COLUMNS)]
    tmp = output_path.with_suffix(".tmp.csv")
    result.to_csv(tmp, index=False)
    tmp.replace(output_path)

    meta = {
        "run_id": run_id,
        "n_rows": int(len(result)),
        "n_ok": int((result["status"] == "ok").sum()),
        "n_not_evaluable": int((result["status"] == "not_evaluable").sum()),
        "view_ids": sorted(result["view_id"].dropna().astype(str).unique().tolist())
        if "view_id" in result.columns
        else view_ids,
        "model_key": model_key,
        "corpus_dir": str(corpus_dir),
    }
    (out_dir / "inference_manifest.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    write_batch_parquet(cache_dir, run_id, result.loc[result["status"] == "ok"])
    return output_path
