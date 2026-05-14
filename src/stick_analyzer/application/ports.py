from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .dto import AnalysisProgress


ProgressCallback = Callable[[AnalysisProgress], None]


class AnalyzerFunctions(Protocol):
    def load_csv(self, path: Path) -> tuple[Any, Mapping[str, Any]]:
        ...

    def get_stability_thresholds(self, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
        ...

    def detect_fire_bursts(
        self,
        df: Any,
        min_duration_s: float,
    ) -> Sequence[tuple[float, float]]:
        ...

    def detect_weapon_rpm(self, weapons_str: str) -> int:
        ...

    def rpm_to_during_window_ms(self, rpm: int) -> int:
        ...

    def analyze_burst(
        self,
        df: Any,
        burst_start: float,
        burst_end: float,
        noise_floor_x: float = 0.0,
        noise_floor_y: float = 0.0,
        weapon_rpm: int = 0,
    ) -> Mapping[str, Any] | None:
        ...

    def classify_burst(self, metrics: Mapping[str, Any]) -> str:
        ...

    def plot_burst(
        self,
        metrics: Mapping[str, Any],
        output_path: Path,
        title: str,
    ) -> None:
        ...

    def plot_summary(
        self,
        events: Sequence[Mapping[str, Any]],
        output_path: Path,
    ) -> None:
        ...

    def generate_report(
        self,
        events: Sequence[Mapping[str, Any]],
        csv_path: Path,
        metadata: Mapping[str, Any],
        thresholds: Mapping[str, Any],
    ) -> str:
        ...


class ReportWriter(Protocol):
    def write_text(self, path: Path, content: str) -> None:
        ...

