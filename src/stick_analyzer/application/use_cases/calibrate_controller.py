from __future__ import annotations

from math import sqrt

from ..dto import CalibrationRequest, CalibrationResult
from ..ports import ClockPort, ControllerReader


class CalibrateController:
    def __init__(self, controller: ControllerReader, clock: ClockPort) -> None:
        self._controller = controller
        self._clock = clock

    def execute(self, request: CalibrationRequest) -> CalibrationResult:
        duration_ns = max(0, int(request.duration_s * 1_000_000_000))
        sample_interval_s = max(0.0, float(request.sample_interval_s))
        start_ns = self._clock.time_ns()
        end_ns = start_ns + duration_ns
        rx_samples: list[float] = []
        ry_samples: list[float] = []

        while self._clock.time_ns() < end_ns:
            state = self._controller.read_state(request.controller_info)
            rx_samples.append(float(state.rx))
            ry_samples.append(float(state.ry))
            if sample_interval_s <= 0:
                break
            self._clock.sleep(sample_interval_s)

        return CalibrationResult(
            noise_floor_x=_population_std(rx_samples),
            noise_floor_y=_population_std(ry_samples),
            sample_count=len(rx_samples),
        )


def _population_std(values: list[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    mean = sum(values) / count
    return sqrt(sum((value - mean) ** 2 for value in values) / count)
