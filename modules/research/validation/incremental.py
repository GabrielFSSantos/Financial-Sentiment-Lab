"""Validação incremental ITI vs baselines."""

from __future__ import annotations

import pandas as pd

from modules.research.common import BASELINE_COLUMNS
from modules.research.config.loader import ResearchConfiguration
from modules.research.validation.metrics import compute_metric


PREDICTOR_COLUMNS = {
    **BASELINE_COLUMNS,
    "iti": None,
}


def _predictor_column(
    predictor_key: str,
    configuration: ResearchConfiguration,
) -> str:
    if predictor_key == "iti":
        return configuration.iti_column
    return BASELINE_COLUMNS[predictor_key]


def _target_column(
    horizon: int,
    configuration: ResearchConfiguration,
) -> str:
    return f"future_{configuration.return_column}_{horizon}"


def run_incremental_validation(
    panel: pd.DataFrame,
    configuration: ResearchConfiguration,
) -> pd.DataFrame:
    """Compara ITI e baselines contra retornos futuros por horizonte."""

    rows: list[dict[str, object]] = []
    predictors = list(configuration.baselines) + ["iti"]

    for horizon in configuration.horizons:
        target_column = _target_column(horizon, configuration)
        if target_column not in panel.columns:
            continue
        target = panel[target_column]

        for predictor_key in predictors:
            column = _predictor_column(predictor_key, configuration)
            if column not in panel.columns:
                continue
            predictor = panel[column]

            for metric_name in configuration.metrics:
                value = compute_metric(metric_name, predictor, target)
                if value is None:
                    continue
                rows.append(
                    {
                        "model_key": panel["model_key"].iloc[0],
                        "dataset_key": panel["dataset_key"].iloc[0],
                        "horizon": horizon,
                        "predictor": predictor_key,
                        "predictor_column": column,
                        "metric": metric_name,
                        "value": value,
                        "n": int(predictor.notna().sum()),
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "model_key",
                "dataset_key",
                "horizon",
                "predictor",
                "predictor_column",
                "metric",
                "value",
                "n",
            ]
        )

    frame = pd.DataFrame(rows)
    iti_rows = frame[frame["predictor"] == "iti"]
    baseline_rows = frame[frame["predictor"] != "iti"]

    deltas: list[dict[str, object]] = []
    for _, iti_row in iti_rows.iterrows():
        matching = baseline_rows[
            (baseline_rows["horizon"] == iti_row["horizon"])
            & (baseline_rows["metric"] == iti_row["metric"])
        ]
        for _, baseline_row in matching.iterrows():
            if iti_row["metric"] == "mse":
                delta = float(baseline_row["value"]) - float(iti_row["value"])
            else:
                delta = float(iti_row["value"]) - float(baseline_row["value"])
            deltas.append(
                {
                    "model_key": iti_row["model_key"],
                    "dataset_key": iti_row["dataset_key"],
                    "horizon": iti_row["horizon"],
                    "baseline": baseline_row["predictor"],
                    "metric": iti_row["metric"],
                    "iti_value": iti_row["value"],
                    "baseline_value": baseline_row["value"],
                    "delta": delta,
                }
            )

    if deltas:
        frame.attrs["deltas"] = pd.DataFrame(deltas)

    return frame


__all__ = [
    "run_incremental_validation",
]
