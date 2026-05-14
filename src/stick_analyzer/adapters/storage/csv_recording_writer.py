from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Sequence, TextIO

from ...application.dto import RecordedSample, RecordingFileMetadata


class CsvRecordingWriter:
    def __init__(self) -> None:
        self._file: TextIO | None = None
        self._writer: csv.writer | None = None
        self._logical_buttons: tuple[str, ...] = ()

    def open(
        self,
        path: Path,
        metadata: RecordingFileMetadata,
        logical_buttons: Sequence[str],
    ) -> None:
        self.close()
        self._logical_buttons = tuple(logical_buttons)
        self._file = Path(path).open("w", newline="", encoding="utf-8")
        self._write_metadata(metadata)
        self._writer = csv.writer(self._file)
        self._writer.writerow(_header_for(self._logical_buttons))

    def write_sample(self, sample: RecordedSample) -> None:
        if self._writer is None:
            raise RuntimeError("CSV writer is not open")
        row = [
            sample.timestamp_ns,
            f"{sample.elapsed_s:.6f}",
            f"{sample.lx:.5f}",
            f"{sample.ly:.5f}",
            f"{sample.rx:.5f}",
            f"{sample.ry:.5f}",
            f"{sample.lt:.4f}",
            f"{sample.rt:.4f}",
        ]
        for button in self._logical_buttons:
            row.append(int(bool(sample.buttons.get(button, False))))
        row.extend([int(sample.fire), int(sample.ads), sample.mark])
        self._writer.writerow(row)

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
        self._file = None
        self._writer = None
        self._logical_buttons = ()

    def _write_metadata(self, metadata: RecordingFileMetadata) -> None:
        if self._file is None:
            raise RuntimeError("CSV file is not open")
        for key, value in metadata.values.items():
            self._file.write(f"# meta: {key}={value}\n")
        self._file.write(f"# meta: fire_button={metadata.fire_button}\n")
        self._file.write(f"# meta: ads_button={metadata.ads_button}\n")
        self._file.write(f"# meta: controller_name={metadata.controller_name}\n")
        self._file.write(f"# meta: controller_protocol={metadata.controller_protocol}\n")
        self._file.write(f"# meta: controller_layout={metadata.controller_layout}\n")
        if metadata.controller_guid:
            self._file.write(f"# meta: controller_guid={metadata.controller_guid}\n")
        self._file.write(f"# meta: noise_floor_x={metadata.noise_floor_x:.6f}\n")
        self._file.write(f"# meta: noise_floor_y={metadata.noise_floor_y:.6f}\n")
        self._file.write(f"# meta: nominal_rate={metadata.nominal_rate}\n")
        self._file.write(f"# meta: started={datetime.now().isoformat()}\n")


def _header_for(logical_buttons: tuple[str, ...]) -> list[str]:
    return [
        "timestamp_ns",
        "elapsed_s",
        "lx",
        "ly",
        "rx",
        "ry",
        "lt",
        "rt",
    ] + [f"btn_{button.lower()}" for button in logical_buttons] + [
        "fire",
        "ads",
        "mark",
    ]
