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
