"""Reusable production controller.

This is intentionally deterministic at the orchestration boundary:
manifest -> speech timing -> Unreal scene jobs -> post-production command.
Actual TTS and Remotion implementations can be swapped without changing the
manifest format.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .manifest import build_timing_contract, load_manifest
from .router import SceneRoute, route_manifest
from .unreal import UnrealClaude


def prepare(manifest_path: str, speech_timing_path: str) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    speech_timing = json.loads(Path(speech_timing_path).read_text(encoding="utf-8"))
    contract = build_timing_contract(manifest, speech_timing)
    return {"manifest": manifest, "timing": contract}


def route(
    prepared: dict[str, Any],
    cut_interval: tuple[float, float] = (2.0, 3.0),
    seed: int | None = None,
) -> list[SceneRoute]:
    """Resolve the scene jobs step: background variants and camera cuts per scene.

    Takes the output of `prepare()` so the pipeline stays manifest -> speech
    timing -> scene jobs -> Unreal/post-production, with narration timing as
    the only source of scene duration.
    """
    return route_manifest(prepared["manifest"], prepared["timing"], cut_interval=cut_interval, seed=seed)


def check_unreal(base_url: str = "http://localhost:3000") -> dict[str, Any]:
    return UnrealClaude(base_url).status()


def run_postproduction(command: list[str], cwd: str | None = None) -> None:
    if not command:
        raise ValueError("Post-production command cannot be empty.")
    subprocess.run(command, cwd=cwd, check=True)
