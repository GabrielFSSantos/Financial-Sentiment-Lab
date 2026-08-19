"""Validação incremental ITI vs baselines."""

from __future__ import annotations

import pandas as pd

from modules.research.common import BASELINE_COLUMNS
from modules.research.config.loader import ResearchConfiguration
from modules.research.validation.inference import (
    compute_delta_inference,
    is_significant_favorable_delta,
)
from modules.research.validation.metrics import (
    NUMPY_METRIC_FUNCTIONS,
    compute_metric_with_inference,
    resolve_target_series,
)


def _predictor_column(
    predictor_key: str,
    configuration: ResearchConfiguration,
) -> str:
    if predictor_key in configuration.iti_predictors:
        return predictor_key
    return BASELINE_COLUMNS[predictor_key]


def _target_column(
    horizon: int,
    configuration: ResearchConfiguration,
) -> str:
    return f"future_{configuration.return_column}_{horizon}"


def _append_metric_row(
    rows: list[dict[str, object]],
    *,
    panel: pd.DataFrame,
    horizon: int,
    predictor_key: str,
    column: str,
    metric_name: str,
    result,
    target_mode: str,
) -> None:
    if result.value is None:
        return
    rows.append(
        {
            "model_key": panel["model_key"].iloc[0],
            "dataset_key": panel["dataset_key"].iloc[0],
            "horizon": horizon,
            "predictor": predictor_key,
            "predictor_column": column,
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


def run_incremental_validation(
    panel: pd.DataFrame,
    configuration: ResearchConfiguration,
) -> pd.DataFrame:
    """Compara ITI e baselines contra retornos futuros por horizonte."""

    rows: list[dict[str, object]] = []
    iti_predictors = list(configuration.iti_predictors)
    predictors = list(configuration.baselines) + iti_predictors

    for horizon in configuration.horizons:
        target_column = _target_column(horizon, configuration)
        if target_column not in panel.columns:
            continue

        for predictor_key in predictors:
            column = _predictor_column(predictor_key, configuration)
            if column not in panel.columns:
                continue
            predictor = panel[column]
            target = resolve_target_series(
                panel,
                target_column=target_column,
                predictor_key=predictor_key,
                configuration=configuration,
            )
            target_mode = "abs" if configuration.uses_abs_target(predictor_key) else "signed"

            for metric_name in configuration.metrics:
                result = compute_metric_with_inference(
                    metric_name,
                    predictor,
                    target,
                    inference=configuration.inference,
                )
                _append_metric_row(
                    rows,
                    panel=panel,
                    horizon=horizon,
                    predictor_key=predictor_key,
                    column=column,
                    metric_name=metric_name,
                    result=result,
                    target_mode=target_mode,
                )

    columns = [
        "model_key",
        "dataset_key",
        "horizon",
        "predictor",
        "predictor_column",
        "target_mode",
        "metric",
        "value",
        "p_value",
        "ci_low",
        "ci_high",
        "n",
        "n_bootstrap",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(rows)
    iti_rows = frame[frame["predictor"].isin(configuration.iti_predictors)]
    baseline_rows = frame[~frame["predictor"].isin(configuration.iti_predictors)]

    deltas: list[dict[str, object]] = []
    for _, iti_row in iti_rows.iterrows():
        matching = baseline_rows[
            (baseline_rows["horizon"] == iti_row["horizon"])
            & (baseline_rows["metric"] == iti_row["metric"])
            & (baseline_rows["target_mode"] == iti_row["target_mode"])
        ]
        for _, baseline_row in matching.iterrows():
            metric_name = str(iti_row["metric"])
            iti_column = str(iti_row["predictor_column"])
            baseline_column = str(baseline_row["predictor_column"])
            target_column = _target_column(int(iti_row["horizon"]), configuration)
            target = resolve_target_series(
                panel,
                target_column=target_column,
                predictor_key=str(iti_row["predictor"]),
                configuration=configuration,
            )

            delta_result = compute_delta_inference(
                metric_name,
                panel[iti_column].astype(float).to_numpy(),
                panel[baseline_column].astype(float).to_numpy(),
                target.astype(float).to_numpy(),
                metric_fn=NUMPY_METRIC_FUNCTIONS[metric_name],
                inference=configuration.inference,
            )
            if delta_result.value is None:
                continue

            deltas.append(
                {
                    "model_key": iti_row["model_key"],
                    "dataset_key": iti_row["dataset_key"],
                    "horizon": iti_row["horizon"],
                    "iti_predictor": iti_row["predictor"],
                    "baseline": baseline_row["predictor"],
                    "target_mode": iti_row["target_mode"],
                    "metric": metric_name,
                    "iti_value": iti_row["value"],
                    "baseline_value": baseline_row["value"],
                    "delta": delta_result.value,
                    "p_value": delta_result.p_value,
                    "ci_low": delta_result.ci_low,
                    "ci_high": delta_result.ci_high,
                    "n": delta_result.n,
                    "n_bootstrap": delta_result.n_bootstrap,
                    "significant": is_significant_favorable_delta(
                        metric_name=metric_name,
                        delta=float(delta_result.value),
                        ci_low=delta_result.ci_low,
                        ci_high=delta_result.ci_high,
                        p_value=delta_result.p_value,
                    ),
                }
            )

    if deltas:
        frame.attrs["deltas"] = pd.DataFrame(deltas)

    return frame


__all__ = [
    "run_incremental_validation",
]
