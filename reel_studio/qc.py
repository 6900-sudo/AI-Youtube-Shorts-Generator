"""Machine-readable quality gates for finished reels."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict


def _probe(path: str) -> Dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", path,
    ]
    return json.loads(subprocess.check_output(cmd, text=True))


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

    return {
        "ok": True,
        "path": str(p),
        "size_bytes": p.stat().st_size,
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("r_frame_rate"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "duration": float(meta.get("format", {}).get("duration", 0)),
        "true_peak_target_db": max_true_peak_db,
    }
