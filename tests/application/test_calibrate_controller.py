from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

import pytest

from stick_analyzer.application import CalibrationRequest, CalibrateController


@dataclass(frozen=True)
class FakeState:
    rx: float
    ry: float
    lx: float = 0.0
    ly: float = 0.0
    lt: float = 0.0
    rt: float = 0.0
    buttons: dict[str, bool] = field(default_factory=dict)


class FakeController:
    def __init__(self, states):
        self._states = list(states)
        self.read_infos = []

    def read_state(self, controller_info):
        self.read_infos.append(controller_info)
        return self._states[len(self.read_infos) - 1]


class FakeClock:
    def __init__(self):
        self.now_ns = 0
        self.sleeps = []

    def time_ns(self):
        return self.now_ns

    def sleep(self, duration_s):
        self.sleeps.append(duration_s)
        self.now_ns += int(duration_s * 1_000_000_000)


def test_calibration_collects_samples_and_returns_population_noise_floor():
    controller_info = object()
    controller = FakeController([
        FakeState(rx=0.0, ry=2.0),
        FakeState(rx=2.0, ry=2.0),
        FakeState(rx=4.0, ry=2.0),
    ])
    clock = FakeClock()

    result = CalibrateController(controller, clock).execute(
        CalibrationRequest(
            controller_info=controller_info,
            duration_s=0.012,
            sample_interval_s=0.004,
        )
    )

    assert result.sample_count == 3
    assert result.noise_floor_x == pytest.approx(sqrt(8 / 3))
    assert result.noise_floor_y == 0.0
    assert controller.read_infos == [controller_info, controller_info, controller_info]
    assert clock.sleeps == [0.004, 0.004, 0.004]
