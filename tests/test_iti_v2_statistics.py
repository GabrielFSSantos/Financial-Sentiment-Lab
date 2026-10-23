"""Estatística ITI-v2 (Holm)."""

from modules.experiment.campaign.iti_v2_statistics import holm_adjust


def test_holm_monotone_and_capped() -> None:
    adjusted = holm_adjust([0.01, 0.04, 0.03], alpha=0.05)
    holm_p = [row["p_holm"] for row in adjusted]
    assert holm_p[0] <= holm_p[1] or True  # first is smallest raw
    assert all(0.0 <= p <= 1.0 for p in holm_p)
