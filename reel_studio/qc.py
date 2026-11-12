"""Machine-readable quality gates for finished reels."""

from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict


def _probe(path: str) -> Dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", path,
    ]
    return json.loads(subprocess.check_output(cmd, text=True))


def _measure_true_peak(path: str) -> float:
    """Measure audio true peak in dBFS using FFmpeg's EBU R128 filter."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", path,
        "-filter_complex", "ebur128=peak=true", "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = (result.stderr or "") + "\n" + (result.stdout or "")
    matches = re.findall(r"True peak:\\s*(-?(?:\\d+(?:\\.\\d+)?|inf))\\s*dBFS", output, re.IGNORECASE)
    if not matches:
        raise RuntimeError("FFmpeg did not report an audio true-peak measurement.")
    value = matches[-1].lower()
    if value == "-inf":
        return float("-inf")
    if value == "inf":
        return float("inf")
    return float(value)


def validate_mp4(
    path: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
    max_true_peak_db: float = -1.5,
) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        raise ValueError(f"Output does not exist or is empty: {path}")

    meta = _probe(str(p))
    streams = meta.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video:
        raise ValueError("No video stream found.")
    if video.get("width") != width or video.get("height") != height:
        raise ValueError(f"Wrong dimensions: {video.get('width')}x{video.get('height')}")
    if not audio:
        raise ValueError("No audio stream found.")

    rate = video.get("avg_frame_rate") or video.get("r_frame_rate")
    try:
        actual_fps = float(Fraction(rate))
    except (TypeError, ValueError, ZeroDivisionError):
        raise ValueError(f"Could not determine video frame rate: {rate!r}") from None
    if abs(actual_fps - fps) > 0.01:
        raise ValueError(f"Wrong frame rate: expected {fps} fps, found {actual_fps:g} fps")

    true_peak = _measure_true_peak(str(p))
    if true_peak > max_true_peak_db:
        raise ValueError(
            f"Audio true peak too high: {true_peak:.2f} dBFS "
            f"(maximum allowed {max_true_peak_db:.2f} dBFS)"
        )

    return {
        "ok": True,
        "path": str(p),
        "size_bytes": p.stat().st_size,
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": actual_fps,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "duration": float(meta.get("format", {}).get("duration", 0)),
        "true_peak_db": true_peak,
        "true_peak_limit_db": max_true_peak_db,
    }
