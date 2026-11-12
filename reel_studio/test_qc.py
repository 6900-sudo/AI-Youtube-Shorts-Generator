from pathlib import Path

import pytest

from reel_studio import qc


@pytest.fixture
def output_file(tmp_path):
    path = tmp_path / "sample.mp4"
    path.write_bytes(b"not-empty")
    return str(path)


@pytest.fixture
def valid_probe():
    return {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920,
             "avg_frame_rate": "24/1", "r_frame_rate": "24/1", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": "19.0"},
    }


def test_validate_mp4_passes_when_all_quality_gates_pass(monkeypatch, output_file, valid_probe):
    monkeypatch.setattr(qc, "_probe", lambda _: valid_probe)
    monkeypatch.setattr(qc, "_measure_true_peak", lambda _: -2.0)
    result = qc.validate_mp4(output_file)
    assert result["ok"] is True
    assert result["fps"] == 24
    assert result["true_peak_db"] == -2.0


def test_validate_mp4_rejects_wrong_frame_rate(monkeypatch, output_file, valid_probe):
    valid_probe["streams"][0]["avg_frame_rate"] = "30/1"
    monkeypatch.setattr(qc, "_probe", lambda _: valid_probe)
    monkeypatch.setattr(qc, "_measure_true_peak", lambda _: -2.0)
    with pytest.raises(ValueError, match="Wrong frame rate"):
        qc.validate_mp4(output_file)


def test_validate_mp4_rejects_true_peak_above_limit(monkeypatch, output_file, valid_probe):
    monkeypatch.setattr(qc, "_probe", lambda _: valid_probe)
    monkeypatch.setattr(qc, "_measure_true_peak", lambda _: -1.0)
    with pytest.raises(ValueError, match="Audio true peak too high"):
        qc.validate_mp4(output_file)


def test_validate_mp4_fails_closed_if_true_peak_cannot_be_measured(monkeypatch, output_file, valid_probe):
    monkeypatch.setattr(qc, "_probe", lambda _: valid_probe)
    def unavailable(_):
        raise RuntimeError("FFmpeg did not report an audio true-peak measurement.")
    monkeypatch.setattr(qc, "_measure_true_peak", unavailable)
    with pytest.raises(RuntimeError, match="true-peak measurement"):
        qc.validate_mp4(output_file)
