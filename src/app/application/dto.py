from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class AnalyzeRecordingRequest:
    csv_path: Path
    max_events: int = 20
    min_duration_s: float = 0.05

    def __post_init__(self) -> None:
        object.__setattr__(self, "csv_path", Path(self.csv_path))


@dataclass(frozen=True)
class AnalysisProgress:
    step: str
    message: str
    current: int | None = None
    total: int | None = None


@dataclass(frozen=True)
class AnalysisResult:
    source_path: Path
    events: Sequence[Mapping[str, Any]]
    report_text: str
    report_path: Path
    summary_image_path: Path
    event_image_paths: Sequence[Path]


@dataclass(frozen=True)
class CalibrationRequest:
    controller_info: Any
    duration_s: float = 3.0
    sample_interval_s: float = 0.004


@dataclass(frozen=True)
class CalibrationResult:
    noise_floor_x: float
    noise_floor_y: float
    sample_count: int


@dataclass(frozen=True)
class RecordingFileMetadata:
    values: Mapping[str, Any]
    fire_button: str
    ads_button: str
    controller_name: str
    controller_protocol: str
    controller_layout: str
    controller_guid: str
    noise_floor_x: float
    noise_floor_y: float
    nominal_rate: int


@dataclass(frozen=True)
class RecordedSample:
    timestamp_ns: int
    elapsed_s: float
    lx: float
    ly: float
    rx: float
    ry: float
    lt: float
    rt: float
    buttons: Mapping[str, bool]
    fire: bool
    ads: bool
    mark: str = ""


@dataclass(frozen=True)
class RecordSessionRequest:
    output_path: Path
    metadata: Mapping[str, Any]
    fire_button: str
    ads_button: str
    mark_button: str | None
    controller_info: Any
    perf_profile: str
    noise_floor_x: float
    noise_floor_y: float
    logical_buttons: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", Path(self.output_path))
        object.__setattr__(self, "logical_buttons", tuple(self.logical_buttons))


@dataclass(frozen=True)
class RecordingProgress:
    elapsed: float
    samples: int
    rate: float
    effective_rate: float
    dup_ratio: float
    fire_pct: float
    ads_pct: float
    lx: float
    ly: float
    rx: float
    ry: float
    lt: float
    rt: float
    fire: bool
    ads: bool
    mark_count: int
    just_marked: bool


@dataclass(frozen=True)
class RecordingSummary:
    duration: float
    samples: int
    rate: float
    effective_rate: float
    dup_frames: int
    dup_ratio: float
    fire_count: int
    ads_count: int
    mark_count: int
    output: Path
    noise_floor_x: float
    noise_floor_y: float
