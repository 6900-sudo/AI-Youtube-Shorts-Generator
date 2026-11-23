"""Scene routing for speech-first reels.

Resolves each manifest scene to a concrete background variant and a camera
cut plan, from manifest data and rules rather than hard-coded values. This
is the piece the README's "provider-neutral" promise needs: TTS, avatar and
B-roll implementations plug in downstream of a route, so swapping providers
never touches the manifest format.

Kept deliberately free of any network/provider call: it decides *what* to
use for a scene, callers decide *how* to fetch or render it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

CAMERA_MOVES = (
    "slow_push",
    "slow_pull",
    "pan_left",
    "pan_right",
    "zoom_in",
    "zoom_out",
    "close",
    "documentary_wide",
)


@dataclass(frozen=True)
class CameraCut:
    start: float
    end: float
    move: str


@dataclass(frozen=True)
class SceneRoute:
    scene_id: str
    role: str
    environment: str
    camera_cuts: list[CameraCut]
    presenter: dict[str, Any] | None
    overlays: list[dict[str, Any]] = field(default_factory=list)


def resolve_environment(
    environment: str,
    outfit: str | None,
    environment_rules: dict[str, dict[str, Any]] | None,
) -> str:
    """Resolve a scene's base environment to a variant from the presenter's outfit.

    environment_rules maps a base environment name to a rule, e.g.:
        {"liverpool_skyline": {"variants": {"day": ["light_blazer"],
                                             "night": ["dark_jacket"]},
                                "default": "day"}}
    A scene whose environment has no matching rule passes through unchanged.
    """
    rule = (environment_rules or {}).get(environment)
    if not rule:
        return environment

    variants = rule.get("variants", {})
    if outfit:
        for variant_name, outfits in variants.items():
            if outfit in outfits:
                return f"{environment}_{variant_name}"

    default = rule.get("default")
    return f"{environment}_{default}" if default else environment


def build_camera_plan(
    duration: float,
    cut_interval: tuple[float, float] = (2.0, 3.0),
    moves: tuple[str, ...] = CAMERA_MOVES,
    seed: int | None = None,
) -> list[CameraCut]:
    """Generate a pan/zoom cut list spanning a scene's duration.

    Cuts land every `cut_interval` seconds (uniformly sampled), the default
    being the 2-3s angle/pan/zoom cadence a UGC-style news segment wants.
    """
    if duration <= 0:
        raise ValueError("duration must be positive")
    low, high = cut_interval
    if low <= 0 or high < low:
        raise ValueError("cut_interval must be a positive (min, max) pair with min <= max")
    if not moves:
        raise ValueError("moves must be non-empty")

    rng = random.Random(seed)
    cuts: list[CameraCut] = []
    t = 0.0
    while t < duration:
        step = min(rng.uniform(low, high), duration - t)
        cuts.append(CameraCut(start=t, end=t + step, move=rng.choice(moves)))
        t += step
    return cuts


def route_scene(
    scene: dict[str, Any],
    duration: float,
    environment_rules: dict[str, dict[str, Any]] | None = None,
    cut_interval: tuple[float, float] = (2.0, 3.0),
    moves: tuple[str, ...] = CAMERA_MOVES,
    seed: int | None = None,
) -> SceneRoute:
    unreal = scene.get("unreal", {})
    base_environment = unreal.get("environment", scene.get("environment", ""))
    outfit = scene.get("outfit")
    environment = resolve_environment(base_environment, outfit, environment_rules)

    presenter_id = unreal.get("presenter")
    presenter = {"id": presenter_id, "outfit": outfit} if presenter_id else None

    return SceneRoute(
        scene_id=scene["id"],
        role=scene.get("role", "presenter" if presenter_id else "broll"),
        environment=environment,
        camera_cuts=build_camera_plan(duration, cut_interval=cut_interval, moves=moves, seed=seed),
        presenter=presenter,
        overlays=scene.get("overlays", []),
    )


def route_manifest(
    manifest: dict[str, Any],
    timing: dict[str, Any],
    cut_interval: tuple[float, float] = (2.0, 3.0),
    moves: tuple[str, ...] = CAMERA_MOVES,
    seed: int | None = None,
) -> list[SceneRoute]:
    """Route every scene in a manifest, using durations from a timing contract.

    `timing` is the output of `manifest.build_timing_contract` (narration is
    the master clock, so scene durations come from speech timing, not guesses).
    `environment_rules` (day/night-style variant rules) comes from the
    manifest itself under the optional top-level "environment_rules" key.
    """
    environment_rules = manifest.get("environment_rules")
    timed_scenes = {s["id"]: s for s in timing["scenes"]}

    routes = []
    for scene in manifest["scenes"]:
        scene_id = scene["id"]
        if scene_id not in timed_scenes:
            raise ValueError(f"No timing found for scene {scene_id}")
        duration = timed_scenes[scene_id]["duration"]
        routes.append(
            route_scene(
                scene,
                duration,
                environment_rules=environment_rules,
                cut_interval=cut_interval,
                moves=moves,
                seed=seed,
            )
        )
    return routes
