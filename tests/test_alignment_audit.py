"""Auditoria de alinhamento ITI-v2."""

import math

import pandas as pd
import pytest

from modules.research.io.alignment_audit import align_iti_v2_weekly_to_market


def test_align_emits_audit_rows() -> None:
    weekly = pd.DataFrame(
        {
            "company_id": ["Sabesp"],
            "date": ["2024-01-05"],
            "period_end": ["2024-01-05"],
            "week_id": ["2024-01-01/2024-01-07"],
            "iti_v2_h7": [0.2],
            "n_articles": [3],
        }
    )
    prices = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-02", periods=10, freq="B"),
            "ticker": ["SBSP3.SA"] * 10,
            "adj_close": [10.0 + i * 0.1 for i in range(10)],
        }
    )
    panel, audit = align_iti_v2_weekly_to_market(
        weekly,
        prices,
        company_to_ticker={"Sabesp": "SBSP3.SA"},
        horizons=(1,),
        signal_column="iti_v2_h7",
    )
    assert not audit.empty
    assert "loss_reason" in audit.columns
    assert "join_status" in audit.columns
    assert "week_key" in audit.columns
    assert not panel.empty


def test_join_week_with_friday_holiday() -> None:
    """Último pregão na quinta; week_key W-FRI ainda é sexta civil."""

    prices = pd.DataFrame(
        {
            "date": [
                "2024-03-25",
                "2024-03-26",
                "2024-03-27",
                "2024-03-28",
                "2024-04-01",
                "2024-04-02",
                "2024-04-03",
                "2024-04-04",
                "2024-04-05",
            ],
            "ticker": ["SBSP3.SA"] * 9,
            "adj_close": [100, 101, 102, 103, 104, 105, 106, 107, 108],
        }
    )
    weekly = pd.DataFrame(
        {
            "company_id": ["Sabesp"],
            "date": ["2024-03-29"],
            "period_end": ["2024-03-28"],
            "week_id": ["2024-03-22/2024-03-29"],
            "signal_cutoff_at": ["2024-03-27"],
            "iti_v2_h7": [0.2],
            "n_articles": [3],
        }
    )
    panel, audit = align_iti_v2_weekly_to_market(
        weekly,
        prices,
        company_to_ticker={"Sabesp": "SBSP3.SA"},
        horizons=(1,),
        signal_column="iti_v2_h7",
    )
    assert len(panel) == 1
    assert panel.iloc[0]["period_end"] == "2024-03-28"
    assert panel.iloc[0]["future_log_return_1"] == pytest.approx(math.log(108 / 103))
    ok_rows = audit.loc[audit["join_status"] == "ok"]
    assert len(ok_rows) >= 1
