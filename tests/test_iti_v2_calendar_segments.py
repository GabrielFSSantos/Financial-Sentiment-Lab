"""Segmentação civil para bootstrap ITI-v2."""

import pandas as pd

from modules.experiment.campaign.iti_v2_contrasts import _calendar_segment_ids


def test_calendar_segment_ids_breaks_on_gap() -> None:
    ends = pd.to_datetime(
        [
            "2024-01-05",
            "2024-01-12",
            "2024-01-19",
            "2024-02-09",
        ]
    )
    seg = _calendar_segment_ids(ends, max_gap_days=10)
    assert seg.tolist() == [0, 0, 0, 1]
