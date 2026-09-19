# r2v reference-audio source output

r2v's "Use source audio" used to be silently downgraded to `generate` on the backend, and the frontend hid the audio dropdown — the output was always the model-generated audio.

## Root cause

| Layer | Problem |
|---|---|
| Backend | `VIDEO_EDIT_AUDIO_TASKS` only recognized `v2v` / `rv2v`; `resolve_audio_mode()` forced r2v's `source` to `generate` |
| Frontend | The audio dropdown was only shown for v2v / rv2v |
| Extraction | r2v has no source-video timeline, so even with `source` enabled there was no audio to extract |
| Format | When reference audio sample rates differed, the mux played back at the wrong rate (16kHz treated as 44.1kHz → ~2.75x faster) |

## Fix

- Added r2v to the source allowlist and show the audio dropdown in the frontend
- When `source` is set and no source-video audio can be extracted, mux the first available reference audio for that segment
- Normalize to 44.1kHz stereo before muxing (on failure, log a warning and mux in the original format)
- Export all: each segment's reference audio is joined along the timeline; segments without reference audio become silence (other segments are not affected)

## Two channels

| Mode | Output audio | What reference audio still does |
|---|---|---|
| `generate` (default, unchanged) | Model-generated (AV latent decode) | Conditioning, drives lip sync |
| `source` | Reference audio wav muxed as-is | Still used as conditioning; picture is timed to the original audio |

```
ref_audios → MiniMaxH3ReferenceToVideo._encode_ref_audio
           → AudioVAE(32kHz) → AV latent → drives lip sync / rhythm
```

## Usage

- **Use source audio**: output = that segment's reference audio; write `fully_copy` in the prompt's audio tag; the spoken lines must match the audio, otherwise lip sync drifts
- **Generate audio**: output = model-generated (lyrics can differ); write `reference` in the prompt. This path is unchanged from before the merge
- Reference audio format is flexible (auto-normalized); attach one per segment. Segments without reference audio are silent under `source`
