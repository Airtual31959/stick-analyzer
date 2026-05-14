from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..dto import AnalysisProgress, AnalysisResult, AnalyzeRecordingRequest
from ..ports import AnalyzerFunctions, ProgressCallback, ReportWriter


class AnalysisInputError(ValueError):
    pass


class MissingFireColumnError(AnalysisInputError):
    pass


class NoFireBurstsError(AnalysisInputError):
    pass


class _LegacyAnalyzerAdapter:
    def __init__(self, module_name: str = "analyzer") -> None:
        self._module_name = module_name
        self._module: Any | None = None

    @property
    def module(self) -> Any:
        if self._module is None:
            self._module = importlib.import_module(self._module_name)
        return self._module

    def load_csv(self, path: Path) -> tuple[Any, Mapping[str, Any]]:
        return self.module.load_csv(path)

    def get_stability_thresholds(self, metadata: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.module.get_stability_thresholds(metadata)

    def detect_fire_bursts(
        self,
        df: Any,
        min_duration_s: float,
    ) -> Sequence[tuple[float, float]]:
        return self.module.detect_fire_bursts(df, min_duration_s)

    def detect_weapon_rpm(self, weapons_str: str) -> int:
        return self.module.detect_weapon_rpm(weapons_str)

    def rpm_to_during_window_ms(self, rpm: int) -> int:
        return self.module.rpm_to_during_window_ms(rpm)

    def analyze_burst(
        self,
        df: Any,
        burst_start: float,
        burst_end: float,
        noise_floor_x: float = 0.0,
        noise_floor_y: float = 0.0,
        weapon_rpm: int = 0,
    ) -> Mapping[str, Any] | None:
        return self.module.analyze_burst(
            df,
            burst_start,
            burst_end,
            noise_floor_x=noise_floor_x,
            noise_floor_y=noise_floor_y,
            weapon_rpm=weapon_rpm,
        )

    def classify_burst(self, metrics: Mapping[str, Any]) -> str:
        return self.module.classify_burst(metrics)

    def plot_burst(
        self,
        metrics: Mapping[str, Any],
        output_path: Path,
        title: str,
    ) -> None:
        self.module.plot_burst(metrics, output_path, title)

    def plot_summary(
        self,
        events: Sequence[Mapping[str, Any]],
        output_path: Path,
    ) -> None:
        self.module.plot_summary(events, output_path)

    def generate_report(
        self,
        events: Sequence[Mapping[str, Any]],
        csv_path: Path,
        metadata: Mapping[str, Any],
        thresholds: Mapping[str, Any],
    ) -> str:
        return self.module.generate_report(events, csv_path, metadata, thresholds)


class _PathReportWriter:
    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")


class AnalyzeRecording:
    def __init__(
        self,
        analyzer: AnalyzerFunctions | None = None,
        report_writer: ReportWriter | None = None,
    ) -> None:
        self._analyzer = analyzer or _LegacyAnalyzerAdapter()
        self._report_writer = report_writer or _PathReportWriter()

    def execute(
        self,
        request: AnalyzeRecordingRequest,
        progress: ProgressCallback | None = None,
    ) -> AnalysisResult:
        csv_path = Path(request.csv_path)
        self._publish(progress, "load_csv", f"正在读取 CSV：{csv_path.name}")
        df, metadata = self._analyzer.load_csv(csv_path)

        self._publish(progress, "thresholds", "正在计算稳定度阈值")
        thresholds = self._analyzer.get_stability_thresholds(metadata)
        self._ensure_fire_column(df)

        bursts = self._detect_bursts(df, request, progress)
        noise_floor_x, noise_floor_y = self._read_noise_floor(metadata, progress)
        weapon_rpm = self._detect_weapon_rpm(metadata, progress)

        base = csv_path.stem
        out_dir = csv_path.parent
        events, event_image_paths = self._analyze_events(
            df, bursts, base, out_dir, noise_floor_x, noise_floor_y,
            weapon_rpm, progress)

        summary_path = out_dir / f"{base}_summary.png"
        self._publish(progress, "summary", f"正在生成汇总图：{summary_path.name}")
        self._analyzer.plot_summary(events, summary_path)

        report_path = out_dir / f"{base}_report.txt"
        self._publish(progress, "report", f"正在生成报告：{report_path.name}")
        report_text = self._analyzer.generate_report(
            events, csv_path, metadata, thresholds)
        self._report_writer.write_text(report_path, report_text)

        self._publish(progress, "done", "分析完成")
        return AnalysisResult(
            source_path=csv_path,
            events=tuple(events),
            report_text=report_text,
            report_path=report_path,
            summary_image_path=summary_path,
            event_image_paths=tuple(event_image_paths),
        )

    def _detect_bursts(
        self,
        df: Any,
        request: AnalyzeRecordingRequest,
        progress: ProgressCallback | None,
    ) -> Sequence[tuple[float, float]]:
        bursts = list(self._analyzer.detect_fire_bursts(
            df, request.min_duration_s))
        self._publish(progress, "detect_bursts", f"检测到 {len(bursts)} 次开火爆发")
        if not bursts:
            raise NoFireBurstsError("没有检测到任何开火事件，请检查录制时按键设置")
        if len(bursts) > request.max_events:
            self._publish(
                progress,
                "truncate_bursts",
                f"事件过多，仅分析最后 {request.max_events} 次",
            )
            bursts = bursts[-request.max_events:]
        return bursts

    def _analyze_events(
        self,
        df: Any,
        bursts: Sequence[tuple[float, float]],
        base: str,
        out_dir: Path,
        noise_floor_x: float,
        noise_floor_y: float,
        weapon_rpm: int,
        progress: ProgressCallback | None,
    ) -> tuple[list[Mapping[str, Any]], list[Path]]:
        events: list[Mapping[str, Any]] = []
        event_image_paths: list[Path] = []
        total = len(bursts)
        for index, (burst_start, burst_end) in enumerate(bursts, 1):
            self._publish(
                progress,
                "analyze_burst",
                f"正在分析第 {index}/{total} 次开火",
                current=index,
                total=total,
            )
            metrics = self._analyzer.analyze_burst(
                df,
                burst_start,
                burst_end,
                noise_floor_x=noise_floor_x,
                noise_floor_y=noise_floor_y,
                weapon_rpm=weapon_rpm,
            )
            if metrics is None:
                continue
            classification = self._analyzer.classify_burst(metrics)
            event = {
                "index": index,
                "metrics": metrics,
                "classification": classification,
            }
            events.append(event)
            event_image_paths.append(self._plot_event(
                event, base, out_dir, burst_start, index))
        return events, event_image_paths

    def _plot_event(
        self,
        event: Mapping[str, Any],
        base: str,
        out_dir: Path,
        burst_start: float,
        index: int,
    ) -> Path:
        metrics = event["metrics"]
        classification = str(event["classification"])
        png_path = out_dir / f"{base}_event_{index:02d}.png"
        title = (
            f"开火 #{index} @ {burst_start:.2f}s 持续{metrics['duration']:.2f}s | "
            f"{'ADS' if metrics['is_ads'] else '腰射'} | {classification}"
        )
        self._analyzer.plot_burst(metrics, png_path, title)
        return png_path

    def _detect_weapon_rpm(
        self,
        metadata: Mapping[str, Any],
        progress: ProgressCallback | None,
    ) -> int:
        weapons = str(metadata.get("weapons", ""))
        weapon_rpm = self._analyzer.detect_weapon_rpm(weapons)
        if weapon_rpm > 0:
            window_ms = self._analyzer.rpm_to_during_window_ms(weapon_rpm)
            if window_ms <= 0:
                message = f"武器识别：{weapons}（{weapon_rpm} RPM，跳过开火中稳定度分析）"
            else:
                message = f"武器识别：{weapons}（{weapon_rpm} RPM，开火中窗口={window_ms}ms）"
            self._publish(progress, "weapon", message)
        return weapon_rpm

    def _read_noise_floor(
        self,
        metadata: Mapping[str, Any],
        progress: ProgressCallback | None,
    ) -> tuple[float, float]:
        try:
            noise_floor_x = float(metadata.get("noise_floor_x", "0") or 0)
            noise_floor_y = float(metadata.get("noise_floor_y", "0") or 0)
        except (TypeError, ValueError):
            noise_floor_x = noise_floor_y = 0.0
        if noise_floor_x > 0 or noise_floor_y > 0:
            self._publish(
                progress,
                "noise_floor",
                f"应用硬件本底校准：X={noise_floor_x:.5f}  Y={noise_floor_y:.5f}",
            )
        return noise_floor_x, noise_floor_y

    def _ensure_fire_column(self, df: Any) -> None:
        columns = getattr(df, "columns", ())
        if "fire" not in columns:
            raise MissingFireColumnError("CSV 缺少 fire 列，请用本工具重新录制")

    def _publish(
        self,
        progress: ProgressCallback | None,
        step: str,
        message: str,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        if progress is not None:
            progress(AnalysisProgress(
                step=step,
                message=message,
                current=current,
                total=total,
            ))

