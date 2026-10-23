"""Pipeline campanha ITI-v2 (índices)."""

from pathlib import Path

import pandas as pd

from modules.experiment.campaign.iti_v2_pipeline import build_indices


def test_build_indices_smoke(tmp_path: Path, project_root: Path) -> None:
    preds = pd.DataFrame(
        {
            "news_id": ["n1"],
            "company_id": ["sabesp"],
            "date": ["2024-01-03"],
            "p_negative": [0.1],
            "p_neutral": [0.2],
            "p_positive": [0.7],
        }
    )
    pred_path = tmp_path / "pred.csv"
    preds.to_csv(pred_path, index=False)
    paths = build_indices(
        pred_path,
        "test_run_smoke",
        protocol_path=project_root / "configs/campaigns/iti_v2/protocol.yaml",
        analysis_plan_path=project_root / "configs/campaigns/iti_v2/analysis_plan.yaml",
    )
    assert paths["iti_daily"].is_file()
    assert paths["iti_weekly"].is_file()
