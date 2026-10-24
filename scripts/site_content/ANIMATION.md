# Recording and animation

Record accepted changes once, then replay them at a chosen speed. Rendering does not rerun growth or remeasure fonts. Existing nodes remain stationary.

## Export from the command line

```console
graph-ics render --example sprawl --nodes 80 --palette arctic --output examples/output/static.png --record examples/output/growth.jsonl
graph-ics frames --log examples/output/growth.jsonl --palette arctic --output examples/output/frames --fps 24 --seconds-per-event 0.04
```

Frames are numbered PNGs. Higher `--fps` samples the same timeline more frequently; larger `--seconds-per-event` slows growth. `--max-frames` rejects oversized exports before writing. Existing sequence frame names are not overwritten. Use `--gif` for a looping GIF; video encoding remains external.

`frames` can build an example directly instead of reading `--log`. A saved log preserves node shapes, line styles, colours and text paths; palette selection then changes only the background. Geometry overrides with `--log` are rejected.

## Playback in Python

```python
from graph_ics import build_example, EventRecorder, Playback, ReplayRenderer

graph = build_example('sprawl', nodes=80)
with EventRecorder(graph, path='growth.jsonl') as recorder:
    graph.build()

playback = Playback(recorder.snapshot(), seconds_per_event=0.04)
renderer = ReplayRenderer(playback, background='#0b1d2c')
renderer.render(1.0).write_to_png('one-second.png')
```

`Playback` supports pause, resume, seek and advance with caller-supplied elapsed time. Seek clamps at the end. Region framing keeps a stable viewport; artwork framing uses the final visible bounds and can crop initial nodes that cleanup later removes.

Seed nodes fade in. A branch reveals its connection during the first 75% of its interval, then its node. Loops and bridges reveal over the full interval. Cleanup removes isolated nodes; completion adds no extra visual interval. Dashed, dotted and double strokes retain their patterns during reveal.

## Live generation

```python
from graph_ics import Graph, LiveGrowth, Playback, ReplayRenderer

live = LiveGrowth(Graph(target_nodes=100, seed=7))
assert live.recorder is not None
renderer = ReplayRenderer(Playback(live.recorder.snapshot()))
try:
    while not live.generator.done:
        live.tick(max_attempts=30, time_budget_ms=8)
        renderer.update(live.recorder.snapshot())
        renderer.playback.advance(1/30)
        # Present renderer.render() in the application's UI.
finally:
    live.close()
```

Generation pause and playback pause are independent. Attempt limits are strict; elapsed-time budgets are best effort because an individual geometry operation cannot be interrupted. `renderer.update(log)` accepts an extension of the same log and requires region framing.

The graph and retained log consume memory as they grow. For streaming capture, use `EventRecorder(graph, path=..., retain=False)` and load the file afterwards. `LiveGrowth(record=False)` skips recording. Resetting a graph detaches its recorder; attach a new one for the new run.

## Log format and validation

JSONL records contain scene metadata and accepted node, edge, join, removal and completion events. Text paths are recorded so replay does not depend on matching fonts. Built-in field settings are retained; arbitrary Python callbacks are identified but not serialized as executable code. Logs are playback records, not resumable generator checkpoints.

The loader checks versions, geometry values, references, topology transitions and event ordering. Incomplete final lines are rejected rather than repaired silently. Geometry-only loading requires no Cairo; rendering does.

Run `python -m scripts.generate_animation` to generate an interactive local preview at `examples/output/animation/index.html`. It includes play/pause, seeking and speed controls. The main gallery's visual guide also compares replay timing.


## Animated GIF

Use `graph-ics frames --log docs/example-growth.jsonl --gif --palette porcelain --fps 15 --seconds-per-event 0.015 --max-frames 300 --output examples/output/growth.gif`. The GIF loops and pauses on the final image. Pillow is included in the render extra. GIF requires an opaque background; use PNG frames for alpha and full colour. Frame and aggregate pixel limits are checked before export, and existing files are not overwritten. Python: `ReplayRenderer(...).export_gif(path, fps=15)`.
