from reel_studio.manifest import build_timing_contract, load_manifest


def test_example_manifest_validates():
    data = load_manifest("reel_studio/examples/news-reel.json")
    contract = build_timing_contract(
        data,
        {
            "hook": {"start": 0.0, "end": 4.0},
            "body": {"start": 4.0, "end": 14.0},
            "ending": {"start": 14.0, "end": 19.0},
        },
    )
    assert contract["duration"] == 19.0
    assert len(contract["scenes"]) == 3
