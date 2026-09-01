"""Testes de buckets temporais em period_breakdown."""

from __future__ import annotations

import pandas as pd

from modules.evaluation.period_breakdown import analyze_periods, assign_temporal_bucket


def test_assign_temporal_bucket_three_way() -> None:
    assert assign_temporal_bucket(pd.Timestamp("2022-08-15")) == "pre_evento_2022"
    assert assign_temporal_bucket(pd.Timestamp("2023-02-10")) == "interregno_2023q1"
    assert assign_temporal_bucket(pd.Timestamp("2023-11-15")) == "evento_nov23_abr24"
    assert assign_temporal_bucket(pd.Timestamp("2024-04-01")) == "evento_nov23_abr24"


def test_analyze_periods_three_buckets() -> None:
    panel = pd.DataFrame(
        {
            "period_end": [
                "2022-06-03",
                "2022-06-10",
                "2022-06-17",
                "2023-02-03",
                "2023-02-10",
                "2023-02-17",
                "2023-12-01",
                "2024-01-05",
                "2024-03-01",
            ],
            "iti_liquido": [0.1, 0.2, 0.15, -0.1, 0.0, 0.05, 0.3, 0.25, 0.4],
            "future_log_return_1": [0.01, -0.02, 0.02, 0.03, -0.01, 0.0, 0.02, 0.01, 0.05],
        }
    )
    summary = analyze_periods(panel)
    buckets = set(summary["bucket"])
    assert buckets == {
        "pre_evento_2022",
        "interregno_2023q1",
        "evento_nov23_abr24",
    }
    assert len(summary) == 3
