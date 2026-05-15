from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Mapping

from ..dto import (
    RecordedSample,
    RecordingFileMetadata,
    RecordingProgress,
    RecordingSummary,
    RecordSessionRequest,
)
from ..ports import (
    ClockPort,
    ControllerReader,
    RecordingDoneCallback,
    RecordingProgressCallback,
    RecordingWriter,
)


class RecordingInputError(ValueError):
    pass


@dataclass(frozen=True)
class _PerfProfile:
    rate: int
    gui_interval_s: float


@dataclass
class _RecordingCounters:
    sample_count: int = 0
    fire_count: int = 0
    ads_count: int = 0
    dup_frames: int = 0
    mark_count: int = 0
    last_signature: tuple[float, float, float, float] | None = None
    last_mark_pressed: bool = False

    def capture_mark(self, buttons: Mapping[str, bool], mark_button: str | None) -> str:
        if not mark_button:
            return ""
        current_pressed = bool(buttons.get(mark_button, False))
        mark = "good" if current_pressed and not self.last_mark_pressed else ""
        if mark:
            self.mark_count += 1
        self.last_mark_pressed = current_pressed
        return mark

    def record_sample(self, sample: RecordedSample) -> None:
        self.sample_count += 1
        self.fire_count += int(sample.fire)
        self.ads_count += int(sample.ads)
        signature = (
            round(sample.rx, 6),
            round(sample.ry, 6),
            round(sample.lx, 6),
            round(sample.ly, 6),
        )
        if self.last_signature is not None and signature == self.last_signature:
            self.dup_frames += 1
        self.last_signature = signature

    def to_progress(self, sample: RecordedSample) -> RecordingProgress:
        rate = self.sample_count / max(sample.elapsed_s, 1e-6)
        dup_ratio = self.dup_frames / max(self.sample_count, 1)
        return RecordingProgress(
            elapsed=sample.elapsed_s,
            samples=self.sample_count,
            rate=rate,
            effective_rate=rate * (1.0 - dup_ratio),
            dup_ratio=dup_ratio,
            fire_pct=100 * self.fire_count / max(self.sample_count, 1),
            ads_pct=100 * self.ads_count / max(self.sample_count, 1),
            lx=sample.lx,
            ly=sample.ly,
            rx=sample.rx,
            ry=sample.ry,
            lt=sample.lt,
            rt=sample.rt,
            fire=sample.fire,
            ads=sample.ads,
            mark_count=self.mark_count,
            just_marked=sample.mark == "good",
        )

    def to_summary(
        self,
        duration_s: float,
        output_path: Path,
        noise_floor_x: float,
        noise_floor_y: float,
    ) -> RecordingSummary:
        rate = self.sample_count / max(duration_s, 1e-6)
        dup_ratio = self.dup_frames / max(self.sample_count, 1)
        return RecordingSummary(
            duration=duration_s,
            samples=self.sample_count,
            rate=rate,
            effective_rate=rate * (1.0 - dup_ratio),
            dup_frames=self.dup_frames,
            dup_ratio=dup_ratio,
            fire_count=self.fire_count,
            ads_count=self.ads_count,
            mark_count=self.mark_count,
            output=output_path,
            noise_floor_x=noise_floor_x,
            noise_floor_y=noise_floor_y,
        )


class RecordSession:
    PERF_PROFILES: ClassVar[dict[str, _PerfProfile]] = {
        "high": _PerfProfile(rate=500, gui_interval_s=0.1),
        "normal": _PerfProfile(rate=250, gui_interval_s=0.2),
        "low": _PerfProfile(rate=125, gui_interval_s=0.5),
    }

    def __init__(
        self,
        controller: ControllerReader,
        clock: ClockPort,
        writer: RecordingWriter,
    ) -> None:
        self._controller = controller
        self._clock = clock
        self._writer = writer
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def execute(
        self,
        request: RecordSessionRequest,
        progress: RecordingProgressCallback | None = None,
        done: RecordingDoneCallback | None = None,
    ) -> RecordingSummary:
        if request.controller_info is None:
            raise RecordingInputError("未选择手柄")

        profile = self._resolve_profile(request.perf_profile)
        # stop() 可能先于 execute() 抵达（GUI 线程竞态），本轮必须保留该请求；
        # 执行结束后再清理，避免影响同一个 session 后续复用。
        try:
            self._writer.open(
                request.output_path,
                _build_file_metadata(request, profile.rate),
                request.logical_buttons,
            )
            start_ns = self._clock.time_ns()
            counters = _RecordingCounters()

            try:
                self._record_samples(request, profile, start_ns, counters, progress)
            finally:
                self._writer.close()

            duration_s = (self._clock.time_ns() - start_ns) / 1_000_000_000
            summary = counters.to_summary(
                duration_s,
                request.output_path,
                request.noise_floor_x,
                request.noise_floor_y,
            )
            if done is not None:
                done(summary)
            return summary
        finally:
            self._stop_requested = False

    def _record_samples(
        self,
        request: RecordSessionRequest,
        profile: _PerfProfile,
        start_ns: int,
        counters: _RecordingCounters,
        progress: RecordingProgressCallback | None,
    ) -> None:
        sample_interval_ns = int(1_000_000_000 / profile.rate)
        next_sample_ns = start_ns
        last_update_ns = start_ns

        while not self._stop_requested:
            now_ns = self._wait_until(next_sample_ns)
            try:
                state = self._controller.read_state(request.controller_info)
            except Exception:
                break
            sample = self._build_sample(request, counters, start_ns, now_ns, state)
            self._writer.write_sample(sample)
            counters.record_sample(sample)
            if _should_publish_progress(now_ns, last_update_ns, profile.gui_interval_s):
                if progress is not None:
                    progress(counters.to_progress(sample))
                last_update_ns = now_ns
            next_sample_ns = _next_sample_time(next_sample_ns, now_ns, sample_interval_ns)

    def _wait_until(self, target_ns: int) -> int:
        now_ns = self._clock.time_ns()
        wait_ns = target_ns - now_ns
        if wait_ns > 1_000_000:
            self._clock.sleep(wait_ns / 1_000_000_000)
            now_ns = self._clock.time_ns()
        return now_ns

    def _build_sample(
        self,
        request: RecordSessionRequest,
        counters: _RecordingCounters,
        start_ns: int,
        now_ns: int,
        state: Any,
    ) -> RecordedSample:
        buttons = dict(getattr(state, "buttons", {}) or {})
        fire = bool(buttons.get(request.fire_button, False))
        ads = bool(buttons.get(request.ads_button, False))
        mark = counters.capture_mark(buttons, request.mark_button)
        return RecordedSample(
            timestamp_ns=now_ns,
            elapsed_s=(now_ns - start_ns) / 1_000_000_000,
            lx=float(state.lx),
            ly=float(state.ly),
            rx=float(state.rx),
            ry=float(state.ry),
            lt=float(state.lt),
            rt=float(state.rt),
            buttons=buttons,
            fire=fire,
            ads=ads,
            mark=mark,
        )

    def _resolve_profile(self, name: str) -> _PerfProfile:
        return self.PERF_PROFILES.get(name, self.PERF_PROFILES["high"])


def _build_file_metadata(
    request: RecordSessionRequest,
    nominal_rate: int,
) -> RecordingFileMetadata:
    return RecordingFileMetadata(
        values=request.metadata,
        fire_button=request.fire_button,
        ads_button=request.ads_button,
        controller_name=_controller_text(request.controller_info, "name"),
        controller_protocol=_controller_text(request.controller_info, "protocol"),
        controller_layout=_controller_text(request.controller_info, "layout"),
        controller_guid=_controller_text(request.controller_info, "guid", default=""),
        noise_floor_x=float(request.noise_floor_x),
        noise_floor_y=float(request.noise_floor_y),
        nominal_rate=nominal_rate,
    )


def _controller_text(controller_info: object, attr: str, default: str = "unknown") -> str:
    value = getattr(controller_info, attr, default)
    if value is None:
        return default
    text = str(value)
    return text if text else default


def _should_publish_progress(
    now_ns: int,
    last_update_ns: int,
    interval_s: float,
) -> bool:
    return (now_ns - last_update_ns) / 1_000_000_000 > interval_s


def _next_sample_time(next_sample_ns: int, now_ns: int, interval_ns: int) -> int:
    next_sample_ns += interval_ns
    if next_sample_ns < now_ns:
        return now_ns + interval_ns
    return next_sample_ns
