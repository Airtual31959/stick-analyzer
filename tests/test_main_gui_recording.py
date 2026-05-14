from pathlib import Path
from types import SimpleNamespace

import main_gui
from stick_analyzer.application import (
    RecordingProgress,
    RecordingSummary,
    RecordSessionRequest,
)


class FakeSession:
    def __init__(self):
        self.requests = []
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1

    def execute(self, request, progress=None, done=None):
        self.requests.append(request)
        if progress is not None:
            progress(
                RecordingProgress(
                    elapsed=1.25,
                    samples=100,
                    rate=500.0,
                    effective_rate=450.0,
                    dup_ratio=0.1,
                    fire_pct=20.0,
                    ads_pct=30.0,
                    lx=0.1,
                    ly=-0.1,
                    rx=0.2,
                    ry=-0.2,
                    lt=0.3,
                    rt=0.4,
                    fire=True,
                    ads=False,
                    mark_count=2,
                    just_marked=True,
                )
            )
        summary = RecordingSummary(
            duration=2.5,
            samples=200,
            rate=500.0,
            effective_rate=475.0,
            dup_frames=10,
            dup_ratio=0.05,
            fire_count=80,
            ads_count=60,
            mark_count=2,
            output=request.output_path,
            noise_floor_x=request.noise_floor_x,
            noise_floor_y=request.noise_floor_y,
        )
        if done is not None:
            done(summary)
        return summary


def test_stick_recorder_delegates_to_record_session_and_converts_callbacks(
    monkeypatch,
    tmp_path,
):
    logical_buttons = ("RIGHT_SHOULDER", "TRIGGER_LEFT", "BACK")
    monkeypatch.setattr(
        main_gui,
        "cb",
        SimpleNamespace(LOGICAL_BUTTONS=logical_buttons),
    )
    session = FakeSession()
    writer = object()
    clock = object()
    controller_manager = object()
    controller_info = SimpleNamespace(
        name="Test Pad",
        protocol="pygame",
        layout="xbox",
        guid="guid-1",
    )
    constructed = {}

    def session_factory(controller_arg, clock_arg, writer_arg):
        constructed["controller"] = controller_arg
        constructed["clock"] = clock_arg
        constructed["writer"] = writer_arg
        return session

    updates = []
    done = []
    output_path = tmp_path / "record.csv"

    recorder = main_gui.StickRecorder(
        output_path=output_path,
        metadata={"weapon": "r301"},
        fire_button="RIGHT_SHOULDER",
        ads_button="TRIGGER_LEFT",
        controller_info=controller_info,
        controller_manager=controller_manager,
        on_update=updates.append,
        on_done=lambda ok, info: done.append((ok, info)),
        perf_profile="normal",
        noise_floor_x=0.01,
        noise_floor_y=0.02,
        mark_button="BACK",
        session_factory=session_factory,
        writer_factory=lambda: writer,
        clock=clock,
    )

    recorder._run()

    assert constructed == {
        "controller": controller_manager,
        "clock": clock,
        "writer": writer,
    }
    assert len(session.requests) == 1
    request = session.requests[0]
    assert isinstance(request, RecordSessionRequest)
    assert request.output_path == output_path
    assert request.metadata == {"weapon": "r301"}
    assert request.fire_button == "RIGHT_SHOULDER"
    assert request.ads_button == "TRIGGER_LEFT"
    assert request.mark_button == "BACK"
    assert request.controller_info is controller_info
    assert request.perf_profile == "normal"
    assert request.noise_floor_x == 0.01
    assert request.noise_floor_y == 0.02
    assert request.logical_buttons == logical_buttons

    assert updates == [
        {
            "elapsed": 1.25,
            "samples": 100,
            "rate": 500.0,
            "effective_rate": 450.0,
            "dup_ratio": 0.1,
            "fire_pct": 20.0,
            "ads_pct": 30.0,
            "lx": 0.1,
            "ly": -0.1,
            "rx": 0.2,
            "ry": -0.2,
            "lt": 0.3,
            "rt": 0.4,
            "fire": True,
            "ads": False,
            "mark_count": 2,
            "just_marked": True,
        }
    ]
    assert done == [
        (
            True,
            {
                "duration": 2.5,
                "samples": 200,
                "rate": 500.0,
                "effective_rate": 475.0,
                "dup_frames": 10,
                "dup_ratio": 0.05,
                "fire_count": 80,
                "ads_count": 60,
                "mark_count": 2,
                "output": str(output_path),
                "noise_floor_x": 0.01,
                "noise_floor_y": 0.02,
            },
        )
    ]


def test_stick_recorder_stop_calls_active_session(tmp_path):
    session = FakeSession()
    recorder = main_gui.StickRecorder(
        output_path=Path(tmp_path) / "record.csv",
        metadata={},
        fire_button="RIGHT_SHOULDER",
        ads_button="TRIGGER_LEFT",
        controller_info=object(),
        controller_manager=object(),
        on_update=lambda _progress: None,
        on_done=lambda _ok, _info: None,
    )
    recorder._session = session

    recorder.stop()

    assert session.stop_calls == 1


def test_app_calibrate_then_record_delegates_success_without_tk(
    monkeypatch,
    tmp_path,
):
    class FakeWidget:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.configures = []

        def pack(self, *args, **kwargs):
            self.pack_args = args
            self.pack_kwargs = kwargs

        def configure(self, **kwargs):
            self.configures.append(kwargs)

    class FakeDialog(FakeWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.destroyed = False
            self.geometry_calls = []

        def title(self, value):
            self.title_value = value

        def geometry(self, value):
            self.geometry_calls.append(value)

        def transient(self, owner):
            self.owner = owner

        def resizable(self, width, height):
            self.resizable_value = (width, height)

        def protocol(self, name, callback):
            self.protocol_value = (name, callback)

        def update_idletasks(self):
            self.updated = True

        def destroy(self):
            self.destroyed = True

    class FakeStatusText:
        def __init__(self):
            self.delete_calls = []

        def delete(self, start, end):
            self.delete_calls.append((start, end))

    class SyncThread:
        def __init__(self, target, *args, **kwargs):
            self.target = target
            self.args = args
            self.kwargs = kwargs

        def start(self):
            self.target()

    captured = {}

    class FakeCalibrateController:
        def __init__(self, controller_reader, clock):
            captured["controller_reader"] = controller_reader
            captured["clock"] = clock

        def execute(self, request):
            captured["request"] = request
            return SimpleNamespace(
                noise_floor_x=0.01,
                noise_floor_y=0.02,
                sample_count=123,
            )

    class FakeOwner:
        def __init__(self, controller_manager):
            self.start_btn = {"state": "normal"}
            self.status_text = FakeStatusText()
            self.controller_mgr = controller_manager
            self.logs = []
            self.start_calls = []

        def winfo_rootx(self):
            return 20

        def winfo_rooty(self):
            return 40

        def winfo_width(self):
            return 900

        def winfo_height(self):
            return 700

        def after(self, _delay_ms, callback, *args):
            callback(*args)

        def _log(self, message):
            self.logs.append(message)

        def _actually_start_recording(
            self, output_path, metadata, fire_btn, ads_btn, mark_btn,
            ctrl, nfx, nfy,
        ):
            self.start_calls.append(
                SimpleNamespace(
                    output_path=output_path,
                    metadata=metadata,
                    fire_btn=fire_btn,
                    ads_btn=ads_btn,
                    mark_btn=mark_btn,
                    ctrl=ctrl,
                    nfx=nfx,
                    nfy=nfy,
                )
            )

    monkeypatch.setattr(main_gui.tk, "Toplevel", FakeDialog)
    monkeypatch.setattr(main_gui.tk, "Label", FakeWidget)
    monkeypatch.setattr(main_gui.ttk, "Label", FakeWidget)
    monkeypatch.setattr(main_gui.threading, "Thread", SyncThread)
    monkeypatch.setattr(main_gui, "CalibrateController", FakeCalibrateController)

    controller_manager = object()
    owner = FakeOwner(controller_manager)
    output_path = tmp_path / "record.csv"
    metadata = {"weapon": "r301"}
    ctrl = SimpleNamespace(name="Test Pad")

    main_gui.App._calibrate_then_record(
        owner,
        output_path,
        metadata,
        "RIGHT_SHOULDER",
        "TRIGGER_LEFT",
        "BACK",
        ctrl,
    )

    assert captured["controller_reader"]._reader is controller_manager
    assert hasattr(captured["clock"], "time_ns")
    assert captured["request"] == main_gui.CalibrationRequest(
        controller_info=ctrl,
        duration_s=3.0,
        sample_interval_s=0.004,
    )
    assert metadata["noise_floor_x"] == "0.010000"
    assert metadata["noise_floor_y"] == "0.020000"
    assert any("校准完成" in line and "采样 123 帧" in line for line in owner.logs)

    assert len(owner.start_calls) == 1
    start_call = owner.start_calls[0]
    assert start_call.output_path == output_path
    assert start_call.metadata is metadata
    assert start_call.fire_btn == "RIGHT_SHOULDER"
    assert start_call.ads_btn == "TRIGGER_LEFT"
    assert start_call.mark_btn == "BACK"
    assert start_call.ctrl is ctrl
    assert start_call.nfx == 0.01
    assert start_call.nfy == 0.02
