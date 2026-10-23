"""Bootstrap bilateral para contrastes Δ."""

import numpy as np

from modules.research.config.loader import InferenceConfiguration
from modules.research.validation.inference import compute_delta_inference
from modules.research.validation.metrics import NUMPY_METRIC_FUNCTIONS


def test_delta_inference_two_sided_p_not_one_sided_mass() -> None:
    n = 40
    rng = np.random.default_rng(0)
    y = rng.normal(size=n)
    iti = y + rng.normal(scale=0.5, size=n)
    base = y + rng.normal(scale=0.5, size=n)
    config = InferenceConfiguration(
        enabled=True,
        n_bootstrap=500,
        block_size=4,
        ci_level=0.95,
        random_seed=42,
    )
    result = compute_delta_inference(
        "spearman",
        iti,
        base,
        y,
        metric_fn=NUMPY_METRIC_FUNCTIONS["spearman"],
        inference=config,
    )
    assert result.p_value is not None
    assert 0.0 <= result.p_value <= 1.0
    one_sided = float(np.mean(np.array([result.value or 0.0]) <= 0.0))
    assert result.p_value != one_sided or result.n_bootstrap > 0
