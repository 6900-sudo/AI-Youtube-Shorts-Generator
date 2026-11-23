from reel_studio.manifest import build_timing_contract, load_manifest
from reel_studio.router import (
    build_camera_plan,
    resolve_environment,
    route_manifest,
    route_scene,
)


def test_resolve_environment_picks_variant_by_outfit():
    rules = {
        "liverpool_skyline": {
            "variants": {"day": ["light_blazer"], "night": ["dark_jacket"]},
            "default": "day",
        }
    }
    assert resolve_environment("liverpool_skyline", "light_blazer", rules) == "liverpool_skyline_day"
    assert resolve_environment("liverpool_skyline", "dark_jacket", rules) == "liverpool_skyline_night"


def test_resolve_environment_falls_back_to_default():
    rules = {"liverpool_skyline": {"variants": {"day": ["light_blazer"]}, "default": "day"}}
    assert resolve_environment("liverpool_skyline", "unknown_outfit", rules) == "liverpool_skyline_day"
    assert resolve_environment("liverpool_skyline", None, rules) == "liverpool_skyline_day"


def test_resolve_environment_passes_through_unknown_environment():
    assert resolve_environment("cinematic_broll", "light_blazer", {}) == "cinematic_broll"
    assert resolve_environment("cinematic_broll", None, None) == "cinematic_broll"


def test_build_camera_plan_covers_duration_with_no_gaps_or_overlaps():
    cuts = build_camera_plan(10.0, cut_interval=(2.0, 3.0), seed=1)
    assert cuts[0].start == 0.0
    assert cuts[-1].end == 10.0
    for prev, nxt in zip(cuts, cuts[1:]):
        assert prev.end == nxt.start
    for cut in cuts:
        length = cut.end - cut.start
        assert 0 < length <= 3.0 + 1e-9
        assert cut.move in {
            "slow_push", "slow_pull", "pan_left", "pan_right",
            "zoom_in", "zoom_out", "close", "documentary_wide",
        }


def test_build_camera_plan_rejects_bad_input():
    import pytest

    with pytest.raises(ValueError):
        build_camera_plan(0)
    with pytest.raises(ValueError):
        build_camera_plan(10, cut_interval=(3.0, 2.0))


def test_route_scene_resolves_presenter_environment_and_outfit():
    scene = {
        "id": "scene_01",
        "role": "presenter",
        "outfit": "dark_jacket",
        "unreal": {"environment": "liverpool_skyline", "camera": "close", "presenter": "colin_reader"},
    }
    rules = {"liverpool_skyline": {"variants": {"night": ["dark_jacket"]}, "default": "day"}}

    route = route_scene(scene, duration=5.0, environment_rules=rules, seed=1)

    assert route.scene_id == "scene_01"
    assert route.role == "presenter"
    assert route.environment == "liverpool_skyline_night"
    assert route.presenter == {"id": "colin_reader", "outfit": "dark_jacket"}
    assert route.camera_cuts[-1].end == 5.0


def test_route_scene_without_presenter_defaults_to_broll_role():
    scene = {"id": "scene_02", "unreal": {"environment": "cinematic_broll"}}
    route = route_scene(scene, duration=4.0, seed=1)
    assert route.role == "broll"
    assert route.presenter is None


def test_route_manifest_end_to_end_on_colin_reader_example():
    manifest = load_manifest("reel_studio/examples/colin-reader.json")
    timing = build_timing_contract(
        manifest,
        {
            "hook": {"start": 0.0, "end": 4.0},
            "body": {"start": 4.0, "end": 14.0},
            "ending": {"start": 14.0, "end": 19.0},
        },
    )

    routes = route_manifest(manifest, timing, seed=1)
    by_id = {r.scene_id: r for r in routes}

    assert by_id["scene_01"].environment == "liverpool_skyline_day"
    assert by_id["scene_03"].environment == "liverpool_skyline_night"
    assert by_id["scene_02"].role == "broll"
    assert by_id["scene_02"].overlays[0]["type"] == "ugc_caption"
    assert by_id["scene_02"].camera_cuts[-1].end == 10.0


def test_route_manifest_raises_on_missing_scene_timing():
    manifest = {
        "scenes": [{"id": "scene_01", "unreal": {"environment": "liverpool_skyline"}}],
    }
    timing = {"scenes": []}
    import pytest

    with pytest.raises(ValueError):
        route_manifest(manifest, timing)
