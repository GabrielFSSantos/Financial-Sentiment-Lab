"""Validação de índices contra retornos de mercado."""

from __future__ import annotations

import pandas as pd

from modules.research.common import BASELINE_COLUMNS
from modules.research.config.loader import ResearchConfiguration
from modules.research.validation.metrics import compute_metric


def run_market_validation(
    panel: pd.DataFrame,
    configuration: ResearchConfiguration,
) -> pd.DataFrame:
    """Correlaciona índices e baselines com retornos futuros."""

    rows: list[dict[str, object]] = []
    series_keys = list(configuration.baselines) + ["iti"]

    for horizon in configuration.horizons:
        target_column = f"future_{configuration.return_column}_{horizon}"
        if target_column not in panel.columns:
            continue
        target = panel[target_column]

        for series_key in series_keys:
            if series_key == "iti":
                column = configuration.iti_column
            else:
                column = BASELINE_COLUMNS[series_key]
            if column not in panel.columns:
                continue

            for metric_name in configuration.metrics:
                value = compute_metric(metric_name, panel[column], target)
                if value is None:
                    continue
                rows.append(
                    {
                        "model_key": panel["model_key"].iloc[0],
                        "dataset_key": panel["dataset_key"].iloc[0],
                        "horizon": horizon,
                        "series": series_key,
                        "series_column": column,
                        "target_column": target_column,
                        "metric": metric_name,
                        "value": value,
                        "n": int(panel[column].notna().sum()),
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "model_key",
                "dataset_key",
                "horizon",
                "series",
                "series_column",
                "target_column",
                "metric",
                "value",
                "n",
            ]
        )

    return pd.DataFrame(rows)


def run_uncertainty_validation(
    uncertainty: pd.DataFrame,
    panel: pd.DataFrame,
    configuration: ResearchConfiguration,
) -> pd.DataFrame | None:
    """Correlaciona incerteza multi-modelo com |retorno| (opcional)."""

    if uncertainty.empty or "iti_uncertainty" not in uncertainty.columns:
        return None

    merged = uncertainty.merge(
        panel.loc[:, ["date", "company", configuration.return_column]],
        on=["date", "company"],
        how="inner",
    )
    if merged.empty:
        return None

    abs_return = merged[configuration.return_column].abs()
    rows: list[dict[str, object]] = []
    for metric_name in configuration.metrics:
        value = compute_metric(
            metric_name,
            merged["iti_uncertainty"],
            abs_return,
        )
        if value is None:
            continue
        rows.append(
            {
                "metric": metric_name,
                "value": value,
                "n": int(merged["iti_uncertainty"].notna().sum()),
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


__all__ = [
    "run_market_validation",
    "run_uncertainty_validation",
]
