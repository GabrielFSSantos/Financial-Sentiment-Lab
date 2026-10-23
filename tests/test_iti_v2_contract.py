import pytest

from modules.models.base import ModelPrediction, ModelPredictionError
from modules.models.iti_v2_contract import validate_iti_v2_prediction


def test_strict_requires_all_probs():
    with pytest.raises(ModelPredictionError):
        validate_iti_v2_prediction(
            ModelPrediction(
                predicted_label="POSITIVE",
                prob_positive=0.7,
                prob_negative=0.2,
                prob_neutral=None,
            )
        )


def test_strict_sum_tolerance():
    with pytest.raises(ModelPredictionError):
        validate_iti_v2_prediction(
            ModelPrediction(
                predicted_label="POSITIVE",
                prob_positive=0.5,
                prob_negative=0.3,
                prob_neutral=0.1,
            )
        )
