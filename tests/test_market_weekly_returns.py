"""Retornos semanais W-FRI (fechamento sobre fechamento anterior)."""

import math

import numpy as np
import pandas as pd

from modules.research.io.market_weekly_returns import (
    attach_future_weekly_log_returns,
    weekly_log_returns_from_prices,
)


def test_inter_week_gap_return_audit_example() -> None:
    """Auditoria: salto entre semanas entra em R_w, não só intra-semana."""

    prices = pd.DataFrame(
        {
            "date": [
                "2024-01-05",  # sexta semana 1 — fechamento 100
                "2024-01-08",  # segunda semana 2 — abertura 110
                "2024-01-12",  # sexta semana 2 — fechamento 121
            ],
            "ticker": ["SBSP3.SA"] * 3,
            "adj_close": [100.0, 110.0, 121.0],
        }
    )
    weekly = weekly_log_returns_from_prices(prices)
    week2 = weekly.loc[weekly["week_close_price"] == 121.0].iloc[0]
    expected = math.log(121.0 / 100.0)
    assert math.isclose(float(week2["log_return_week"]), expected, rel_tol=1e-9)

    wrong_intra = math.log(121.0 / 110.0)
    assert not math.isclose(float(week2["log_return_week"]), wrong_intra, rel_tol=1e-6)


def test_future_return_uses_civil_weeks_not_row_shift() -> None:
    prices = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-02", periods=15, freq="B"),
            "ticker": ["T"] * 15,
            "adj_close": np.linspace(100.0, 114.0, 15),
        }
    )
    weekly = weekly_log_returns_from_prices(prices)
    with_future = attach_future_weekly_log_returns(weekly, horizons=(1,))
    col = "future_log_return_week_1"
    assert col in with_future.columns
    finite = with_future[col].dropna()
    assert not finite.empty
