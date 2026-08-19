"""Validação de índices contra retornos de mercado."""

from __future__ import annotations

import pandas as pd

from modules.research.common import BASELINE_COLUMNS
from modules.research.config.loader import ResearchConfiguration
from modules.research.validation.metrics import (
    compute_metric_with_inference,
    resolve_target_series,
)


def run_market_validation(
    panel: pd.DataFrame,
    configuration: ResearchConfiguration,
) -> pd.DataFrame:
    """Correlaciona índices e baselines com retornos futuros."""

    rows: list[dict[str, object]] = []
    series_keys = list(configuration.baselines) + list(configuration.iti_predictors)

    for horizon in configuration.horizons:
        target_column = f"future_{configuration.return_column}_{horizon}"
        if target_column not in panel.columns:
            continue

        for series_key in series_keys:
            if series_key in configuration.iti_predictors:
                column = series_key
            else:
                column = BASELINE_COLUMNS[series_key]
            if column not in panel.columns:
                continue

            target = resolve_target_series(
                panel,
                target_column=target_column,
                predictor_key=series_key,
                configuration=configuration,
            )
            target_mode = "abs" if configuration.uses_abs_target(series_key) else "signed"

            for metric_name in configuration.metrics:
                result = compute_metric_with_inference(
                    metric_name,
                    panel[column],
                    target,
                    inference=configuration.inference,
                )
                if result.value is None:
                    continue
                rows.append(
                    {
                        "model_key": panel["model_key"].iloc[0],
                        "dataset_key": panel["dataset_key"].iloc[0],
                        "horizon": horizon,
                        "series": series_key,
                        "series_column": column,
                        "target_column": target_column,
                        "target_mode": target_mode,
                        "metric": metric_name,
                        "value": result.value,
                        "p_value": result.p_value,
                        "ci_low": result.ci_low,
                        "ci_high": result.ci_high,
                        "n": result.n,
                        "n_bootstrap": result.n_bootstrap,
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
                "target_mode",
                "metric",
                "value",
                "p_value",
                "ci_low",
                "ci_high",
                "n",
                "n_bootstrap",
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
        result = compute_metric_with_inference(
            metric_name,
            merged["iti_uncertainty"],
            abs_return,
            inference=configuration.inference,
        )
        if result.value is None:
            continue
        rows.append(
            {
                "metric": metric_name,
                "value": result.value,
                "p_value": result.p_value,
                "ci_low": result.ci_low,
                "ci_high": result.ci_high,
                "n": result.n,
                "n_bootstrap": result.n_bootstrap,
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


__all__ = [
    "run_market_validation",
    "run_uncertainty_validation",
]
