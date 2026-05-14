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

