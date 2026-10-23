"""Auditoria de alinhamento ITI-v2."""

import pandas as pd

from modules.research.io.alignment_audit import align_iti_v2_weekly_to_market


def test_align_emits_audit_rows() -> None:
    weekly = pd.DataFrame(
        {
            "company_id": ["Sabesp"],
            "date": ["2024-01-05"],
            "week_id": ["2024-01-05/2024-01-05"],
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
