from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from stick_analyzer.application import RecordSession, RecordSessionRequest


@dataclass(frozen=True)
class FakeControllerInfo:
    name: str = "Test Pad"
    protocol: str = "pygame"
    layout: str = "xbox"
    guid: str = "guid-1"


@dataclass(frozen=True)
class FakeState:
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    lt: float = 0.0
    rt: float = 0.0
    buttons: dict[str, bool] = field(default_factory=dict)


class FiniteController:
    def __init__(self, states):
        self._states = list(states)
        self.read_count = 0

    def read_state(self, controller_info):
        if self.read_count >= len(self._states):
            raise RuntimeError("no more frames")
        state = self._states[self.read_count]
        self.read_count += 1
        return state


class RepeatingController:
    def __init__(self, state):
        self._state = state
        self.read_count = 0

    def read_state(self, controller_info):
        self.read_count += 1
        return self._state


class FakeClock:
    def __init__(self):
        self.now_ns = 0

    def time_ns(self):
        return self.now_ns

    def sleep(self, duration_s):
        self.now_ns += int(duration_s * 1_000_000_000)


class FakeWriter:
    def __init__(self):
        self.opened = None
        self.samples = []
        self.closed = False

    def open(self, path, metadata, logical_buttons):
        self.opened = (Path(path), metadata, tuple(logical_buttons))
        self.closed = False

    def write_sample(self, sample):
        self.samples.append(sample)

    def close(self):
        self.closed = True


LOGICAL_BUTTONS = (
    "RIGHT_SHOULDER",
    "TRIGGER_LEFT",
    "DPAD_UP",
)


def _request(tmp_path, **overrides):
    values = {
        "output_path": tmp_path / "record.csv",
        "metadata": {"scene": "training"},
        "fire_button": "RIGHT_SHOULDER",
        "ads_button": "TRIGGER_LEFT",
        "mark_button": "DPAD_UP",
        "controller_info": FakeControllerInfo(),
        "perf_profile": "high",
        "noise_floor_x": 0.01,
        "noise_floor_y": 0.02,
        "logical_buttons": LOGICAL_BUTTONS,
    }
    values.update(overrides)
    return RecordSessionRequest(**values)


def test_execute_records_fire_ads_mark_edges_and_duplicate_summary(tmp_path):
    states = [
        FakeState(buttons={
            "RIGHT_SHOULDER": False,
            "TRIGGER_LEFT": False,
            "DPAD_UP": False,
        }),
        FakeState(buttons={
            "RIGHT_SHOULDER": True,
            "TRIGGER_LEFT": True,
            "DPAD_UP": True,
        }),
        FakeState(buttons={
            "RIGHT_SHOULDER": True,
            "TRIGGER_LEFT": False,
            "DPAD_UP": True,
        }),
        FakeState(rx=0.1, buttons={
            "RIGHT_SHOULDER": False,
            "TRIGGER_LEFT": False,
            "DPAD_UP": False,
        }),
    ]
    writer = FakeWriter()
    session = RecordSession(FiniteController(states), FakeClock(), writer)

    summary = session.execute(_request(tmp_path))

    assert [sample.fire for sample in writer.samples] == [False, True, True, False]
    assert [sample.ads for sample in writer.samples] == [False, True, False, False]
    assert [sample.mark for sample in writer.samples] == ["", "good", "", ""]
    assert summary.samples == 4
    assert summary.fire_count == 2
    assert summary.ads_count == 1
    assert summary.mark_count == 1
    assert summary.dup_frames == 2
    assert summary.dup_ratio == pytest.approx(0.5)
    assert summary.output == tmp_path / "record.csv"
    assert summary.noise_floor_x == 0.01
    assert summary.noise_floor_y == 0.02
    assert writer.opened[1].nominal_rate == 500
    assert writer.opened[2] == LOGICAL_BUTTONS
    assert writer.closed is True


def test_stop_from_progress_returns_summary_and_done_callback(tmp_path):
    writer = FakeWriter()
    session = RecordSession(
        RepeatingController(FakeState()),
        FakeClock(),
        writer,
    )
    progress_events = []
    done_events = []

    def on_progress(progress):
        progress_events.append(progress)
        session.stop()

    summary = session.execute(
        _request(tmp_path),
        progress=on_progress,
        done=done_events.append,
    )

    assert len(progress_events) == 1
    assert summary.samples == progress_events[0].samples
    assert summary.samples == 52
    assert summary.duration == pytest.approx(0.102)
    assert summary.dup_frames == 51
    assert done_events == [summary]
    assert writer.closed is True
