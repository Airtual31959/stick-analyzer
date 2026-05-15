"""存储适配器。"""

__all__ = ["CsvRecordingWriter"]


def __getattr__(name: str):
    if name == "CsvRecordingWriter":
        from .csv_recording_writer import CsvRecordingWriter

        return CsvRecordingWriter
    raise AttributeError(name)
