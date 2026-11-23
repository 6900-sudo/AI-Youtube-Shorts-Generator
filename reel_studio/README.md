# Reel Studio Pipeline

Reusable speech-first production layer for cinematic 9:16 reels.

## Architecture

1. Story/script -> production manifest
2. TTS -> narration audio + word/sentence timing
3. Unreal Engine -> cinematic scene plates through UnrealClaude HTTP/MCP
4. Remotion -> deterministic composition, captions, graphics and audio
5. FFmpeg -> final encode and loudness finishing
6. QC -> machine checks before a render is accepted

Speech timing is the master clock. Scene durations should be derived from narration rather than guessed.

## Manifest

See `examples/news-reel.json`. A manifest is deliberately provider-neutral so TTS, Unreal and post-production implementations can be replaced without changing the story definition.

See `examples/colin-reader.json` for a presenter segment with UGC-style B-roll overlays and an `environment_rules` block that swaps a background between day/night variants based on the presenter's outfit per scene.

## Router

`router.py` resolves the "scene jobs" step between speech timing and the Unreal/post-production calls:

- `resolve_environment` — picks a background variant (e.g. `liverpool_skyline_day` vs `liverpool_skyline_night`) from a scene's `outfit` field and the manifest's optional top-level `environment_rules`. Scenes with no matching rule pass through unchanged.
- `build_camera_plan` — generates a pan/zoom cut list spanning a scene's duration, one cut every 2-3s by default, for the angle-cut/pan/zoom cadence a UGC-style segment wants.
- `route_scene` / `route_manifest` — combine the two per scene (and, via `production.route()`, per manifest) using the narration-derived durations from `build_timing_contract`. `route_manifest` passes through each scene's `role` (`presenter`/`broll`) and `overlays` so downstream rendering knows what to layer on, without the router itself calling any provider.

## Quality gates

- 1080x1920 by default
- 24 fps by default
- H.264/AAC MP4
- voice target -15 LUFS
- true peak <= -1.5 dBTP
- no missing scene outputs
- caption timing must remain inside narration duration
- render metadata must match requested dimensions and frame rate

## Unreal seam

The Unreal adapter is designed around the local UnrealClaude HTTP endpoint documented in UNREAL-SETUP.md:

POST http://localhost:3000/mcp/tool/<name>

The pipeline should prefer direct HTTP for deterministic automation and retain MCP as the agent-facing control path.

## Reuse

Do not create a new Unreal project per video. Keep one permanent StudioProject containing reusable environments, hosts, cameras, lights, materials, props and animation presets. Each new production is data in a manifest.

## Current scope

This directory is the orchestration contract. The existing Shorts Generator remains available for source-video clipping. The Reel Studio layer adds script-first production rather than replacing that capability.
