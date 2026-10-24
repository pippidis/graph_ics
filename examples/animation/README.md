# Animation and replay

Records four seeded scenes: branches, cleanup/refill, joining colonies, and text composition.

```console
python -m examples.animation.example
```

Open `output/index.html` for play/pause, scrubbing and speed controls. Each scene has an event log, static PNG and 49 frames. `output/manifest.json` records timings and counts. Edit the scene settings in `scripts/generate_animation.py`; playback reuses accepted geometry rather than rerunning growth. This fixed comparison does not accept runner seed/node overrides.

[Replay guide](../../scripts/site_content/ANIMATION.md) | [Example index](../README.md)
