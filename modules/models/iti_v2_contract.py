"""Contrato ITI-v2 para predições (probabilidades obrigatórias, tolerância 1e-5)."""

from __future__ import annotations

import math

from modules.models.base import ModelPrediction, ModelPredictionError

ITI_V2_PROB_SUM_TOLERANCE = 1e-5


def validate_iti_v2_prediction(prediction: ModelPrediction) -> None:
    """Exige três probabilidades finitas em [0,1] com soma ≈ 1."""

    for name in ("prob_positive", "prob_negative", "prob_neutral"):
        value = getattr(prediction, name)
        if value is None:
            raise ModelPredictionError(
                f"ITI-v2: {name} ausente; não preencher com one-hot ou confiança."
            )
        if not math.isfinite(float(value)):
            raise ModelPredictionError(f"ITI-v2: {name} não finito.")
        if not 0.0 <= float(value) <= 1.0:
            raise ModelPredictionError(f"ITI-v2: {name} fora de [0,1]: {value}")

    total = (
        float(prediction.prob_positive)
        + float(prediction.prob_negative)
        + float(prediction.prob_neutral)
    )
    if abs(total - 1.0) > ITI_V2_PROB_SUM_TOLERANCE:
        raise ModelPredictionError(
            f"ITI-v2: soma de probabilidades inválida ({total:.8f})."
        )
