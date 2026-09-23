"""Validation and timing helpers for speech-first reel manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


REQUIRED_TOP_LEVEL = {"version", "id", "format", "audio", "voice", "script", "scenes", "output"}


def load_manifest(path: str | Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(data)
    return data


def validate_manifest(data: Dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing:
        raise ValueError(f"Manifest missing required fields: {sorted(missing)}")

    fmt = data["format"]
    if fmt.get("width") != 1080 or fmt.get("height") != 1920:
        raise ValueError("Reel Studio currently requires 1080x1920 output.")

    if int(fmt.get("fps", 0)) not in (24, 25, 30, 50, 60):
        raise ValueError("Unsupported frame rate.")

    audio = data["audio"]
    if float(audio.get("voice_lufs", 0)) > -12:
        raise ValueError("Voice target is unexpectedly hot; use approximately -15 LUFS.")

    if float(audio.get("true_peak_db", 0)) > -1.0:
        raise ValueError("True peak ceiling is too high; use <= -1.5 dBTP.")

    if not isinstance(data["scenes"], list) or not data["scenes"]:
        raise ValueError("At least one scene is required.")


def scene_keys(data: Dict[str, Any]) -> list[str]:
    return [str(scene["id"]) for scene in data["scenes"]]


def build_timing_contract(data: Dict[str, Any], speech_timing: Dict[str, Any]) -> Dict[str, Any]:
    """Bind scene durations to narration timing.

    speech_timing maps script keys to {start, end}. This deliberately avoids
    hard-coded scene lengths and makes narration the master clock.
    """
    scenes = []
    for scene in data["scenes"]:
        key = scene["speech_key"]
        if key not in speech_timing:
            raise ValueError(f"Missing speech timing for scene {scene['id']}: {key}")
        timing = speech_timing[key]
        start = float(timing["start"])
        end = float(timing["end"])
        if end <= start:
            raise ValueError(f"Invalid timing for {key}: {start}..{end}")
        scenes.append({**scene, "start": start, "end": end, "duration": end - start})
    return {"duration": max(s["end"] for s in scenes), "scenes": scenes}
