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
    assert result.n_bootstrap == 500
    assert result.ci_low is not None
    assert result.ci_high is not None
    if result.value is not None and result.ci_low is not None and result.ci_high is not None:
        assert result.ci_low <= result.value <= result.ci_high
    rng2 = np.random.default_rng(0)
    y2 = rng2.normal(size=n)
    iti2 = y2.copy()
    base2 = y2.copy()
    null_result = compute_delta_inference(
        "spearman",
        iti2,
        base2,
        y2,
        metric_fn=NUMPY_METRIC_FUNCTIONS["spearman"],
        inference=config,
    )
    assert null_result.p_value is not None
    assert null_result.p_value >= 0.05
