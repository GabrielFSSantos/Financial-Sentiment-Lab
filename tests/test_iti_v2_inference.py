"""Inferência ITI-v2 (requer model_store local)."""

from pathlib import Path

import pytest

from modules.experiment.campaign.iti_v2_inference import (
    ITI_V2_PREDICTION_COLUMNS,
    run_iti_v2_inference,
)
from modules.experiment.campaign.protocol_lock import build_protocol_lock, write_protocol_lock


@pytest.mark.slow
def test_run_iti_v2_inference_smoke(project_root: Path, tmp_path: Path) -> None:
    model_dir = project_root / "model_store/FinBERT-PT-BR"
    if not model_dir.is_dir():
        pytest.skip("FinBERT-PT-BR não disponível")

    corpus = project_root / "outputs/corpus_inventory/iti_v2_p02"
    if not (corpus / "articles_canonical.csv").is_file():
        pytest.skip("corpus P02 ausente")

    lock = build_protocol_lock(
        corpus_dir=corpus,
        protocol_path=project_root / "configs/campaigns/iti_v2/protocol.yaml",
        analysis_plan_path=project_root / "configs/campaigns/iti_v2/analysis_plan.yaml",
        project_root=project_root,
    )
    write_protocol_lock(corpus / "protocol_lock.json", lock)

    out = run_iti_v2_inference(
        "test_infer_smoke",
        corpus_dir=corpus,
        output_path=tmp_path / "predictions.csv",
        limit=3,
    )
    frame = __import__("pandas").read_csv(out)
    assert set(ITI_V2_PREDICTION_COLUMNS).issubset(frame.columns)
    assert (frame["status"] == "ok").any()
