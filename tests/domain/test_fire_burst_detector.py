from __future__ import annotations

import numpy as np

from stick_analyzer.domain.services.fire_burst_detector import FireBurstDetector


class FakeColumn:
    def __init__(self, values):
        self.values = np.asarray(values)

    def astype(self, dtype):
        return FakeColumn(self.values.astype(dtype))


class FakeFrame:
    def __init__(self, columns):
        self._columns = columns

    def __getitem__(self, key):
        return FakeColumn(self._columns[key])


def _fire_frame(fire_ranges, end_s=2.5, step_s=0.05):
    times = np.round(np.arange(0.0, end_s + step_s / 2, step_s), 3)
    fire = [
        any(start_s <= t <= stop_s for start_s, stop_s in fire_ranges)
        for t in times
    ]
    return FakeFrame({"elapsed_s": times, "fire": fire})


def test_detect_fire_bursts_filters_short_taps_and_splits_large_gaps():
    frame = _fire_frame(
        [
            (0.10, 0.12),
            (0.65, 0.80),
            (1.35, 1.50),
            (2.05, 2.20),
        ],
        end_s=2.5,
    )

    bursts = FireBurstDetector().detect_fire_bursts(frame, min_duration_s=0.1)

    assert bursts == [
        (0.65, 0.80),
        (1.35, 1.50),
        (2.05, 2.20),
    ]


def test_detect_fire_bursts_keeps_segments_joined_within_gap_threshold():
    frame = _fire_frame([(0.20, 0.30), (0.60, 0.75)])

    bursts = FireBurstDetector().detect_fire_bursts(frame, min_duration_s=0.05)

    assert bursts == [(0.20, 0.75)]

