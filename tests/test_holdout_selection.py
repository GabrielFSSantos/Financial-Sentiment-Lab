"""Holdout temporal P02."""

from pathlib import Path

import pandas as pd

from modules.datasets.holdout_selection import select_calendar_holdout


def test_select_holdout_deterministic(tmp_path: Path) -> None:
    csv = tmp_path / "canon.csv"
    pd.DataFrame(
        {
            "news_id": ["a", "b", "c"],
            "data": ["2024-01-01", "2024-03-01", "2024-04-15"],
        }
    ).to_csv(csv, index=False)
    s1 = select_calendar_holdout(csv, tmp_path / "out", holdout_weeks=8)
    s2 = select_calendar_holdout(csv, tmp_path / "out2", holdout_weeks=8)
    assert s1["external_holdout"]["news_ids_sha256"] == s2["external_holdout"]["news_ids_sha256"]
