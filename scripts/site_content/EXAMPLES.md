# Explained sample library

The sample library is executable documentation. `python -m graph_ics list` lists recipes and palettes; `python -m graph_ics describe NAME` explains a recipe before generating it. Each gallery card includes its important options, limitations, exact command, seed, dimensions, and timings. Use the [parameter guide](PARAMETERS.md) for individual option definitions.

```console
python -m graph_ics describe density
python -m graph_ics render --example density --palette arctic --seed 7 --output examples/output/density.png
python -m graph_ics gallery
```

Open [docs/index.html](../../docs/index.html) directly from the checkout. Its curated selection includes large compositions, UK and Spain map treatments in two palettes, and all regular recipes. `--all-palettes` expands regular recipes across all ten palettes. The integrated visual guide adds dimension, shape, line, angle, boundary and spatial-field comparisons, downloadable JSON/YAML scenes, glyph wrapping, graph lettering and an animated GIF. `--quick` produces six small scenes. Every completed scene passes independent final-geometry validation, including rival gaps, hard angles, and isolated-node rules. Full-resolution PNG/SVG figures sit below the index in `figures/`. The index filters by palette, recipe, and large-only output.

| Recipe | What it demonstrates | What changing it entails |
| --- | --- | --- |
| `sprawl` | Coverage-guided branching | Tile size and parent-choice count change distribution; retry budgets change work and saturation behavior. |
| `typography` | Centered text and relative padding | Font size changes the exclusion; padding reserves extra space. Font-dependent ink becomes a fixed path. |
| `density` | Procedural left-to-right density | Density changes desired node population and spacing, not ring size unless a scale field is also supplied. |
| `raster` | A world-mapped scalar image | Pixel rows run downward from minimum y; bilinear sampling smooths the input. |
| `scale` | Coordinated geometric scaling | Node radii, gaps, buffers, lengths, and strokes grow together; feasibility still limits placement. |
| `obstacles` | Concave outline and an excluded rectangle | Full disks/strokes must fit; an edge cannot shortcut a concavity or obstacle. |
| `band` | A region around a polygon boundary | `band_width` defines usable area; thin bands can reject geometry and saturate early. |
| `follow` | Experimental boundary guidance | More guidance biases along anchors; it does not guarantee a closed silhouette. |
| `terminate` | Experimental tip anchoring | Boundary-seeking tips may still fail; strict mode reports unmet terminals rather than silently claiming success. |
| `cooperate` | Attraction plus permitted joining | Colonies retain ownership; bridges join components after growth and obey all geometry rules. |
| `compete` | Repulsion plus hard clearance | Directional repulsion is soft; the explicit gap guarantees separation between rival rings and full strokes. |
| `loops` | Bounded extra cycles | More requested loops require spare degree and legal local edges; count can remain below target. |
| `newest` | Winding newest-tip growth | Parent selection favors the latest tip; coverage and colony schedulers are not mixed with this policy. |
| `quality` | Hard/soft angle limits, cleanup, refill | Stricter angles can underfill. Cleanup removes degree-zero dots; finite refill retries survivors. |
| `arctic_atlas` | 4,000-node graph_ics composition in the Arctic palette | Larger canvas and population reveal local structure at full resolution. |
| `panorama` | 7,000-node wave-scaled panorama | Coordinated scale varies across a wide canvas; output is intended for zooming. |
| `archipelago` | 8,000-node territorial scene | Three owners grow around obstacle islands with pairwise repulsion and hard gaps. |

Palettes are `porcelain`, `linen`, `historical`, `light`, `arctic`, `aurora`, `ember`, `forest`, `orchid`, and `blueprint`. Each defines ring, edge, background, text, and colony colors. Text examples use the palette name as their label, so switching palettes there also changes the text exclusion. Other identical recipes preserve geometry under color changes.

## Runnable source examples

The repository also contains a [folder-based example library](https://github.com/pippidis/graph_ics/tree/main/examples): each folder includes code, instructions, configuration where relevant, and local outputs. Run `python -m scripts.generate_examples --list` to list demonstrations, `--quick` for a small validation set, or select names such as `density text_hug`. Full runs include large country maps and may take several minutes. README files are maintained by hand.

## Generate one example from Python

```python
from graph_ics import build_example, describe_example, GraphStyle, export_graph

recipe = describe_example('raster')
print(recipe.explanation)
print(recipe.options)
print(recipe.limitation)
graph = build_example(recipe.name, palette='arctic', seed=7, nodes=500)
graph.build()
export_graph(graph, 'raster.svg', frame='region', margin=16,
             background=GraphStyle.named('arctic').background)
```

`python -m examples.sample_library` runs a complete explanatory example and writes PNG/SVG plus a replay log. It can be edited as a small starting script. The installed factories live in `graph_ics.samples`; they do not depend on repository-only scripts.

Factories return a graph with growth settings already configured. Use `graph.growth().step(...)`, `graph.build()`, or attach `EventRecorder` immediately. To choose every parameter yourself, use `Graph` or `GraphStyle.create_graph()` and `GrowthSettings` rather than modifying a configured run in place. `dataclasses.replace(GraphStyle.named('arctic'), node_outer_radius=5)` is a typed way to customize a style.

## CLI reference

| Command | Options |
| --- | --- |
| `list` | Lists recipe names and palettes. |
| `describe NAME` | Prints description, key controls, limitation, target count, and dimensions as JSON. |
| `render` | `--example`, `--palette`, `--seed`, `--nodes`, required `--output` ending in PNG/SVG; `--margin`, `--scale`, `--transparent`, optional `--record` JSONL; `--force` permits replacement. |
| `frames` | Build an example with the same selection options, or pass `--log` to replay stored geometry. Required output directory, `--fps`, `--seconds-per-event`, `--max-frames`; margin, scale, transparency, and palette background also apply. |
| `gallery` | `--output` directory (default `gallery`), `--quick` for six scenes, `--all-palettes` for the full colour matrix. Regenerates known gallery outputs in that directory. |

A saved log already contains geometry and colors; when `frames --log` is used, example/seed/node settings are not applied. Palette selection then only supplies the background. Frame export refuses existing sequence frame filenames. Commands return status 2 for invalid options or expected installation/output errors. Node targets are goals and are not forced by disabling collision rules.

The CLI uses the same Python factories as the library. Replay JSONL is an animation record, not a user-code configuration format.


## Visual controls and new recipes

Open the visual guide on the gallery home page for direct comparisons: five hollow node shapes, four line patterns, unrestricted/hard/soft/strict angles, ten palettes, random seeds, population targets, output resolution, whitespace, alpha, and replay timing. Every CLI option links to a relevant visual demonstration. File-management switches are explained beside their output files because they do not change appearance.

Additional recipes are `angles_free`, `angles_hard`, `angles_soft`, `angles_strict`, `shapes`, `lines`, and `uk_population`. Porcelain adds a pure white background; Linen adds a warm near-white alternative. The gallery index includes the examples, guide, and UK explanation together. Standalone guide pages remain available, with figures underneath in `figures/`. The curated public gallery is tracked. Additional local outputs belong in `examples/output/` or `artifacts/`, which are ignored.

```console
graph-ics render --example sprawl --node-shape diamond --edge-style dashed --minimum-angle 45 --preferred-angle 80 --angle-penalty 0.8 --palette porcelain --output examples/output/styled.png
graph-ics render --example uk_population --palette porcelain --output examples/output/uk.png
```

`--node-shape` and `--edge-style` override recipe defaults. Angle flags override the corresponding recipe setting; leave unspecified values at their recipe defaults. Set all three when comparing angle policies. Saved logs retain shapes, patterns and angles; geometry overrides with `frames --log` are rejected. The additional white palettes preserve non-text layouts.

See [UK data provenance](../../src/data/README.md). The population map is deliberately an artistic compression of measured density, not one dot per person or an exact statistical map.


See [scene files, dimensions, glyph contours and spatial colour maps](SCENES.md) for JSON/YAML input and complete visual comparisons.
