"""Estatística ITI-v2 (Holm)."""

import pytest

from modules.experiment.campaign.iti_v2_statistics import holm_adjust


def test_holm_known_values() -> None:
    adjusted = holm_adjust([0.01, 0.04, 0.03], alpha=0.05)
    holm_p = [row["p_holm"] for row in adjusted]
    assert holm_p == pytest.approx([0.03, 0.06, 0.06])
    assert [row["significant_at_alpha"] for row in adjusted] == [True, False, False]


def test_holm_empty() -> None:
    assert holm_adjust([], alpha=0.05) == []
