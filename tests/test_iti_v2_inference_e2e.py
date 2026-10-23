"""Retomada de inferência ITI-v2 com classificador determinístico (sem GPU)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from modules.experiment.campaign.iti_v2_inference import (
    expected_corpus_pairs,
    prune_prediction_rows,
    run_iti_v2_inference,
)
from modules.models.base import ModelPrediction


@dataclass
class _FakeRegistered:
    def predict(self, texts: list[str]) -> list[ModelPrediction]:
        return [
            ModelPrediction(
                prob_negative=0.1,
                prob_neutral=0.2,
                prob_positive=0.7,
                predicted_label="POSITIVE",
                continuous_sentiment=0.6,
            )
            for _ in texts
        ]

    def unload(self) -> None:
        return None


def _write_corpus(corpus_dir: Path, rows: list[dict[str, str]]) -> None:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(corpus_dir / "articles_canonical.csv", index=False)


def _infer_with_fake(
    corpus_dir: Path,
    project_root: Path,
    output_path: Path,
) -> pd.DataFrame:
    model_dir = project_root / "model_store/FinBERT-PT-BR"
    if not model_dir.is_dir():
        pytest.skip("model_store ausente para tokenização")

    fake_model = MagicMock()
    fake_model.key = "finbert_ptbr"
    fake_model.enabled = True
    fake_model.model_dir = model_dir
    fake_model.source = {"weights_sha256": "test-sha-e2e"}

    fake_config = MagicMock()
    fake_config.models = [fake_model]
    fake_registry = MagicMock()
    fake_registry.create.return_value = _FakeRegistered()

    with (
        patch(
            "modules.experiment.campaign.iti_v2_inference.require_protocol_lock",
            return_value={},
        ),
        patch(
            "modules.experiment.campaign.iti_v2_inference.load_models_configuration",
            return_value=fake_config,
        ),
        patch(
            "modules.experiment.campaign.iti_v2_inference.create_model_registry",
            return_value=fake_registry,
        ),
        patch(
            "modules.experiment.campaign.iti_v2_inference._configured_view_ids",
            return_value=["entity_context_v1"],
        ),
    ):
        path = run_iti_v2_inference(
            "run_e2e_test",
            corpus_dir=corpus_dir,
            output_path=output_path,
            use_cache=False,
        )
    return pd.read_csv(path)


def test_prune_drops_removed_news_from_corpus() -> None:
    rows = [
        {"news_id": "a", "view_id": "v1"},
        {"news_id": "b", "view_id": "v1"},
    ]
    frame = pd.DataFrame([{"news_id": "a"}])
    pruned = prune_prediction_rows(rows, expected_corpus_pairs(frame, ["v1"]))
    assert len(pruned) == 1
    assert pruned[0]["news_id"] == "a"


def test_resume_recomputes_when_article_version_changes(
    project_root: Path, tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus"
    rows = [
        {
            "news_id": "n1",
            "article_version_id": "v1",
            "company_id": "Sabesp",
            "data": "2024-01-01",
            "titulo": "Sabesp investe",
            "noticia": "A Sabesp anunciou investimentos relevantes hoje.",
        },
        {
            "news_id": "n2",
            "article_version_id": "v1",
            "company_id": "Sabesp",
            "data": "2024-01-02",
            "titulo": "Sabesp tarifa",
            "noticia": "Sabesp comentou revisão tarifária.",
        },
    ]
    _write_corpus(corpus, rows)
    out = tmp_path / "predictions.csv"

    first = _infer_with_fake(corpus, project_root, out)
    assert len(first) == 2
    hash_n1_first = first.loc[first["news_id"] == "n1", "view_hash"].iloc[0]

    rows[0]["noticia"] = "A Sabesp revisou o plano de investimentos de forma ampla."
    rows[0]["article_version_id"] = "v2"
    _write_corpus(corpus, rows)

    second = _infer_with_fake(corpus, project_root, out)
    assert len(second) == 2
    hash_n1_second = second.loc[second["news_id"] == "n1", "view_hash"].iloc[0]
    assert hash_n1_first != hash_n1_second


def test_resume_updates_date_without_duplicating_rows(
    project_root: Path, tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus2"
    row = {
        "news_id": "n1",
        "article_version_id": "v1",
        "company_id": "Sabesp",
        "data": "2024-01-01",
        "titulo": "Sabesp",
        "noticia": "Sabesp registrou resultado positivo no período.",
    }
    _write_corpus(corpus, [row])
    out = tmp_path / "pred2.csv"
    _infer_with_fake(corpus, project_root, out)
    row["data"] = "2024-01-15"
    _write_corpus(corpus, [row])
    second = _infer_with_fake(corpus, project_root, out)
    assert len(second) == 1
    assert str(second.loc[0, "date"]).startswith("2024-01-15")


def test_unknown_model_revision_sha_blocks_inference(
    project_root: Path, tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus_unknown"
    _write_corpus(
        corpus,
        [
            {
                "news_id": "n1",
                "article_version_id": "v1",
                "company_id": "Sabesp",
                "data": "2024-01-01",
                "titulo": "Sabesp",
                "noticia": "Sabesp anunciou resultados.",
            }
        ],
    )
    out = tmp_path / "pred_unknown.csv"
    fake_model = MagicMock()
    fake_model.key = "finbert_ptbr"
    fake_model.enabled = True
    fake_model.model_dir = project_root / "model_store/FinBERT-PT-BR"
    fake_model.source = {}
    fake_config = MagicMock()
    fake_config.models = [fake_model]
    with (
        patch(
            "modules.experiment.campaign.iti_v2_inference.require_protocol_lock",
            return_value={},
        ),
        patch(
            "modules.experiment.campaign.iti_v2_inference.load_models_configuration",
            return_value=fake_config,
        ),
        patch(
            "modules.experiment.campaign.iti_v2_inference._configured_view_ids",
            return_value=["entity_context_v1"],
        ),
    ):
        if not fake_model.model_dir.is_dir():
            pytest.skip("model_store ausente")
        with pytest.raises(ValueError, match="weights_sha256"):
            run_iti_v2_inference(
                "run_unknown_sha",
                corpus_dir=corpus,
                output_path=out,
                use_cache=False,
            )


def test_prune_after_corpus_shrink(project_root: Path, tmp_path: Path) -> None:
    corpus = tmp_path / "corpus3"
    rows = [
        {
            "news_id": "n1",
            "article_version_id": "v1",
            "company_id": "Sabesp",
            "data": "2024-01-01",
            "titulo": "Sabesp",
            "noticia": "Sabesp anunciou resultados.",
        },
        {
            "news_id": "n2",
            "article_version_id": "v1",
            "company_id": "Sabesp",
            "data": "2024-01-02",
            "titulo": "Sabesp",
            "noticia": "Sabesp comentou tarifas.",
        },
    ]
    _write_corpus(corpus, rows)
    out = tmp_path / "pred3.csv"
    first = _infer_with_fake(corpus, project_root, out)
    assert len(first) == 2
    _write_corpus(corpus, [rows[0]])
    second = _infer_with_fake(corpus, project_root, out)
    assert len(second) == 1
    assert second.iloc[0]["news_id"] == "n1"
