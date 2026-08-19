"""Derivação de baselines adicionais para validação."""

from __future__ import annotations

import pandas as pd


B3_COLUMN = "b3_daily_impact_no_memory"


def add_b3_column(frame: pd.DataFrame) -> pd.DataFrame:
    """Deriva B3 como impacto diário sem memória EWMA."""

    working = frame.copy()
    if "impacto_dia" not in working.columns:
        raise KeyError(
            "Coluna impacto_dia ausente; necessária para derivar B3."
        )
    working[B3_COLUMN] = pd.to_numeric(
        working["impacto_dia"],
        errors="coerce",
    ).fillna(0.0)
    return working


__all__ = [
    "B3_COLUMN",
    "add_b3_column",
]
