"""Baselines internos B0–B2 para comparação futura (módulo research)."""

from __future__ import annotations

import pandas as pd

from modules.experiment.common import column_series, numeric_series


def build_baselines_daily(predictions: pd.DataFrame) -> pd.DataFrame:
    """Calcula baselines diários por empresa."""

    if predictions.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "company",
                "sector",
                "b0_news_count",
                "b1_mean_sentiment",
                "b2_confidence_weighted_sentiment",
            ]
        )

    frame = predictions.copy()
    frame["date"] = pd.to_datetime(column_series(frame, "date"), errors="coerce")
    frame["company"] = column_series(frame, "company").fillna("UNKNOWN")
    frame["sector"] = column_series(frame, "sector").fillna("UNKNOWN")
    frame["d"] = numeric_series(column_series(frame, "continuous_sentiment")).astype(float)
    frame["c"] = numeric_series(column_series(frame, "confidence")).astype(float)
    frame["weighted_d"] = frame["d"] * frame["c"]

    grouped = frame.groupby(["company", "sector", "date"], dropna=False, as_index=False).agg(
        b0_news_count=("news_id", "count"),
        b1_mean_sentiment=("d", "mean"),
        weighted_d_sum=("weighted_d", "sum"),
        confidence_sum=("c", "sum"),
    )
    grouped["b2_confidence_weighted_sentiment"] = grouped.apply(
        lambda row: (
            row["weighted_d_sum"] / row["confidence_sum"]
            if row["confidence_sum"] > 0
            else row["b1_mean_sentiment"]
        ),
        axis=1,
    )
    grouped["date"] = grouped["date"].dt.date.astype(str)
    return grouped.loc[
        :,
        [
            "date",
            "company",
            "sector",
            "b0_news_count",
            "b1_mean_sentiment",
            "b2_confidence_weighted_sentiment",
        ],
    ].sort_values(["company", "date"]).reset_index(drop=True)


def resample_baselines_weekly(baselines_daily: pd.DataFrame) -> pd.DataFrame:
    """Agrega baselines diários para frequência semanal (W-FRI)."""

    if baselines_daily.empty:
        return pd.DataFrame(
            columns=[
                "period_start",
                "period_end",
                "company",
                "sector",
                "b0_news_count",
                "b1_mean_sentiment",
                "b2_confidence_weighted_sentiment",
            ]
        )

    frame = baselines_daily.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    rows: list[dict[str, object]] = []

    for (company, sector), group in frame.groupby(["company", "sector"], dropna=False):
        indexed = group.set_index("date").sort_index()
        for period_start, period_df in indexed.resample("W-FRI"):
            if period_df.empty:
                continue
            rows.append(
                {
                    "period_start": period_start.date().isoformat(),
                    "period_end": period_df.index.max().date().isoformat(),
                    "company": company,
                    "sector": sector,
                    "b0_news_count": int(period_df["b0_news_count"].sum()),
                    "b1_mean_sentiment": float(period_df["b1_mean_sentiment"].mean()),
                    "b2_confidence_weighted_sentiment": float(
                        period_df["b2_confidence_weighted_sentiment"].mean()
                    ),
                }
            )

    return pd.DataFrame(rows)
