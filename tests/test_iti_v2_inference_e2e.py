"""Retomada de inferência ITI-v2 com classificador determinístico (sem GPU)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.common.paths import PROJECT_ROOT

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


def _clear_run_cache(output_path: Path) -> None:
    run_dir = PROJECT_ROOT / "outputs/campaigns/iti_v2" / f"run_e2e_{output_path.stem}"
    if run_dir.is_dir():
        shutil.rmtree(run_dir)


def _write_corpus(corpus_dir: Path, rows: list[dict[str, str]]) -> None:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(corpus_dir / "articles_canonical.csv", index=False)


def _infer_with_fake(
    corpus_dir: Path,
    project_root: Path,
    output_path: Path,
    *,
    use_cache: bool = False,
    predictor: _FakeRegistered | _CountingFake | None = None,
) -> pd.DataFrame:
    model_dir = project_root / "model_store/FinBERT-PT-BR"
    if not model_dir.is_dir():
        pytest.skip("model_store ausente para tokenização")

    model_cfg = MagicMock()
    model_cfg.key = "finbert_ptbr"
    model_cfg.enabled = True
    model_cfg.model_dir = model_dir
    model_cfg.source = {"weights_sha256": "test-sha-e2e"}

    fake_config = MagicMock()
    fake_config.models = [model_cfg]
    registered_impl = predictor or _FakeRegistered()

    class _StubRegistry:
        def create(self, *_args: object, **_kwargs: object) -> object:
            return registered_impl

    fake_registry = _StubRegistry()

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
        run_id = f"run_e2e_{output_path.stem}"
        path = run_iti_v2_inference(
            run_id,
            corpus_dir=corpus_dir,
            output_path=output_path,
            use_cache=use_cache,
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


class _CountingFake:
    def __init__(self) -> None:
        self.calls = 0
        self._inner = _FakeRegistered()

    def predict(self, texts: list[str]) -> list[ModelPrediction]:
        self.calls += 1
        return self._inner.predict(texts)

    def unload(self) -> None:
        self._inner.unload()


def test_cache_hit_skips_second_predict_call(
    project_root: Path, tmp_path: Path
) -> None:
    model_dir = project_root / "model_store/FinBERT-PT-BR"
    if not model_dir.is_dir():
        pytest.skip("model_store ausente para tokenização")
    corpus = tmp_path / "corpus_cache"
    _write_corpus(
        corpus,
        [
            {
                "news_id": "n1",
                "article_version_id": "v1",
                "company_id": "Sabesp",
                "data": "2024-01-01",
                "titulo": "Sabesp",
                "noticia": "Sabesp anunciou resultados operacionais no período.",
            }
        ],
    )
    out = tmp_path / "pred_cache.csv"
    _clear_run_cache(out)
    counter = _CountingFake()
    _infer_with_fake(corpus, project_root, out, use_cache=True, predictor=counter)
    assert counter.calls >= 1
    calls_after_first = counter.calls
    _infer_with_fake(corpus, project_root, out, use_cache=True, predictor=counter)
    assert counter.calls == calls_after_first


def test_cache_off_recomputes_with_predict(
    project_root: Path, tmp_path: Path
) -> None:
    model_dir = project_root / "model_store/FinBERT-PT-BR"
    if not model_dir.is_dir():
        pytest.skip("model_store ausente para tokenização")
    corpus = tmp_path / "corpus_nocache"
    row = {
        "news_id": "n1",
        "article_version_id": "v1",
        "company_id": "Sabesp",
        "data": "2024-01-01",
        "titulo": "Sabesp",
        "noticia": "Sabesp registrou desempenho no trimestre.",
    }
    _write_corpus(corpus, [row])
    out = tmp_path / "pred_nocache.csv"
    _clear_run_cache(out)
    counter = _CountingFake()
    _infer_with_fake(corpus, project_root, out, use_cache=True, predictor=counter)
    calls_warmed = counter.calls
    row["article_version_id"] = "v2"
    row["noticia"] = "Sabesp revisou projeções de investimento."
    _write_corpus(corpus, [row])
    _infer_with_fake(corpus, project_root, out, use_cache=False, predictor=counter)
    assert counter.calls > calls_warmed


def test_interrupted_write_leaves_prior_csv_intact(
    project_root: Path, tmp_path: Path
) -> None:
    model_dir = project_root / "model_store/FinBERT-PT-BR"
    if not model_dir.is_dir():
        pytest.skip("model_store ausente para tokenização")
    corpus = tmp_path / "corpus_interrupt"
    _write_corpus(
        corpus,
        [
            {
                "news_id": "n1",
                "article_version_id": "v1",
                "company_id": "Sabesp",
                "data": "2024-01-01",
                "titulo": "Sabesp",
                "noticia": "Sabesp comunicou indicadores financeiros.",
            }
        ],
    )
    out = tmp_path / "pred_int.csv"
    first = _infer_with_fake(corpus, project_root, out)
    before = first.to_csv(index=False)

    real_to_csv = pd.DataFrame.to_csv

    def _fail_tmp(self: pd.DataFrame, path: object, *args: object, **kwargs: object) -> None:
        if str(path).endswith(".tmp.csv"):
            raise OSError("simulated interrupt")
        real_to_csv(self, path, *args, **kwargs)

    with patch.object(pd.DataFrame, "to_csv", _fail_tmp):
        with pytest.raises(OSError):
            _infer_with_fake(corpus, project_root, out)
    after = pd.read_csv(out).to_csv(index=False)
    assert before == after
    second = _infer_with_fake(corpus, project_root, out)
    assert len(second) == 1
