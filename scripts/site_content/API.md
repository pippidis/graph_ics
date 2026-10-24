# Python API

Import public types and functions from `graph_ics`. Dimensions use world units; export scale converts them to output units. The [parameter reference](PARAMETERS.md) documents individual controls.

| Area | Entry points |
| --- | --- |
| Geometry | `Graph`, `Node`, `Edge`, `Text`, `GraphStyle`, `NodeShape`, `EdgeStyle` |
| Generation | `GrowthSettings`, `RandomFrontier`, `NewestTip`, `CoverageSettings`, `AngleSettings` |
| Spatial inputs | `SpatialFields`, `ConstantField`, `CallableField`, `ImageField`, `RegionSpec`, `ContourSettings`, `Readability` |
| Colonies | `Colony`, `Interaction`, `ColonySettings` |
| Export | `export_graph`, `validate_graph` |
| Animation | `EventRecorder`, `EventLog`, `Playback`, `ReplayRenderer`, `LiveGrowth` |
| Examples | `build_example`, `describe_example`, `example_names` |

## Construction and growth

```python
from graph_ics import GraphStyle, GrowthSettings, AngleSettings

graph = GraphStyle.named('linen').create_graph(target_nodes=300, seed=7,
                                              angles=AngleSettings(35, 70, 0.5))
run = graph.growth(settings=GrowthSettings(total_attempts=12000))
graph.build()
print(run.status, len(graph.nodes), run.quality_report())
```

Configure growth once, before the first step. `build()` runs until the generator stops; its return value does not guarantee the target count. Use `run.step(...)` for incremental work, or `LiveGrowth` for bounded UI ticks. Example factories already configure growth, so their returned graph is ready for `build()` or recording.

Accepted geometry is immutable in practice: changing coordinates or dimensions after insertion invalidates the spatial index and replay assumptions. `to_networkx()` returns a copy for analysis, not an editing handle. Parent lineage, connected components and colony ownership have distinct meanings.

## Compatibility and dependencies

The package is typed and uses a flat source layout mapped to `graph_ics` at installation. Import from the package rather than depending on internal spatial-index implementations.

Point-callable scale-map arguments remain supported; new code can use `SpatialFields` for constant, callable and image inputs. Cairo is optional for geometry and event logs, and required for text measurement and rendering. The bundled UK dataset does not require network access or Pillow at runtime.

Replay JSONL is versioned. Geometry is authoritative; a log is not a general configuration file or a persistent generator checkpoint. Logs missing optional shape/style fields default to circles and solid lines. New fields may not be readable by older versions. See [animation](ANIMATION.md) for validation and lifecycle details.

The API is still evolving. Boundary-following and terminal-anchoring controls are experimental; see [limits and parameters](PARAMETERS.md).


See [scene files, dimensions, glyph contours and spatial colour maps](SCENES.md) for JSON/YAML input and complete visual comparisons.


## Wordmark

`make_logo(path, width=600, height=250, zoom=1.15, palette="porcelain", seed=7, scale=1)` generates the graph_ics wordmark as PNG or SVG. It builds a larger graph and crops the frame, leaving partial rings and connections at all edges. Width/height choose the composition, zoom changes the network texture, and scale changes output resolution. Returns output dimensions. [Logo downloads](../../docs/logo/index.html) include landscape, wide banner, square and portrait variants with SVG, PNG and 2x PNG. Regenerate with `python -m scripts.generate_logos`.


`make_icon(path, size=256)` draws the five-node branching website mark with one red junction. PNG and SVG accept sizes from 16 to 2048; ICO includes 16, 24, 32, 48, 64, 128 and 256 pixel entries. The logo generator also creates the website icon downloads and gallery favicon links.
