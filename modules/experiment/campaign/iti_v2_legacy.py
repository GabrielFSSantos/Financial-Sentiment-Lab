"""LEGACY-C: fórmula legada (EWMA α) sobre a mesma entrada ``soft_input`` do ITI-v2."""

from __future__ import annotations

import pandas as pd

from modules.experiment.indexing.temporal_index import compute_iti_daily_series


def attach_legacy_c_daily(
    daily_v2: pd.DataFrame,
    *,
    alpha: float = 0.7,
    horizon_mode: str = "ewma_alpha",
    company_col: str = "company_id",
) -> pd.DataFrame:
    """Adiciona ``legacy_c_iti`` diário (``iti_liquido`` legado) por empresa."""

    if daily_v2.empty:
        return daily_v2.assign(legacy_c_iti=pd.Series(dtype=float))

    pieces: list[pd.DataFrame] = []
    for company, group in daily_v2.groupby(company_col, sort=False):
        g = group.sort_values("date").copy()
        g["date"] = pd.to_datetime(g["date"], errors="coerce").dt.normalize()
        impact = pd.DataFrame(
            {
                "date": g["date"],
                "company": str(company),
                "sector": "campaign",
                "impacto_dia": g["soft_input"].astype(float),
                "risco_dia": 0.0,
                "news_count": g.get("n_articles", 0).astype(float),
                "mean_horizon": 1.0,
            }
        )
        legacy = compute_iti_daily_series(
            impact,
            alpha=float(alpha),
            initial_value=0.0,
            horizon_mode=horizon_mode,
        )
        legacy["date"] = pd.to_datetime(legacy["date"], errors="coerce").dt.normalize()
        merged = g.merge(
            legacy[["date", "iti_liquido"]].rename(columns={"iti_liquido": "legacy_c_iti"}),
            on="date",
            how="left",
        )
        pieces.append(merged)

    return pd.concat(pieces, ignore_index=True)
