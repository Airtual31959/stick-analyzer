from __future__ import annotations

from app.adapters.storage import CsvRecordingWriter
from app.application.dto import RecordedSample, RecordingFileMetadata


def test_csv_recording_writer_preserves_legacy_metadata_header_and_row_format(tmp_path):
    path = tmp_path / "record.csv"
    writer = CsvRecordingWriter()

    writer.open(
        path,
        RecordingFileMetadata(
            values={"rc_hipfire": "-3", "scene": "training"},
            fire_button="RIGHT_SHOULDER",
            ads_button="TRIGGER_LEFT",
            controller_name="Test Pad",
            controller_protocol="pygame",
            controller_layout="xbox",
            controller_guid="guid-1",
            noise_floor_x=0.01,
            noise_floor_y=0.02,
            nominal_rate=500,
        ),
        ["RIGHT_SHOULDER", "TRIGGER_LEFT"],
    )
    writer.write_sample(
        RecordedSample(
            timestamp_ns=123,
            elapsed_s=0.1234567,
            lx=0.1,
            ly=-0.2,
            rx=0.333333,
            ry=-0.444444,
            lt=0.5,
            rt=0.6,
            buttons={"RIGHT_SHOULDER": True, "TRIGGER_LEFT": False},
            fire=True,
            ads=False,
            mark="good",
        )
    )
    writer.close()

    lines = path.read_text(encoding="utf-8").splitlines()

    assert "# meta: rc_hipfire=-3" in lines
    assert "# meta: scene=training" in lines
    assert "# meta: fire_button=RIGHT_SHOULDER" in lines
    assert "# meta: ads_button=TRIGGER_LEFT" in lines
    assert "# meta: controller_name=Test Pad" in lines
    assert "# meta: controller_protocol=pygame" in lines
    assert "# meta: controller_layout=xbox" in lines
    assert "# meta: controller_guid=guid-1" in lines
    assert "# meta: noise_floor_x=0.010000" in lines
    assert "# meta: noise_floor_y=0.020000" in lines
    assert "# meta: nominal_rate=500" in lines
    assert any(line.startswith("# meta: started=") for line in lines)
    assert lines[-2] == (
        "timestamp_ns,elapsed_s,lx,ly,rx,ry,lt,rt,"
        "btn_right_shoulder,btn_trigger_left,fire,ads,mark"
    )
    assert lines[-1] == (
        "123,0.123457,0.10000,-0.20000,0.33333,-0.44444,"
        "0.5000,0.6000,1,0,1,0,good"
    )
