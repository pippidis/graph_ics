# Parameter guide

Use `build_example(name, palette="arctic", seed=7)` for a ready-configured, unbuilt graph. Call `build()` to finish it. Recipes demonstrate combinations; the Python API exposes the individual controls below. [The sample library](EXAMPLES.md) maps controls to figures and runnable commands. Unless explicitly marked, lengths are world units, not pixels.

## Geometry and style

`Graph` accepts `target_nodes` (including seeds), `target_seed_nodes`, `input_nodes`, and `target_extra_edges`. Targets are requests: obstacles, spacing and bounded retries can prevent reaching them. `seed` controls its local random generator. Supplied nodes are copied. `outline_polygon` contains the graph; `illegal_areas` exclude geometry. `region` is the richer alternative described below. `texts` adds measured text exclusions.

`node_inner_radius`, `node_outer_radius`, and `node_buffer` control rings and clearance. `edge_length_min`, `edge_length_max`, `edge_thickness`, and `edge_node_distance` control visible connections and their separation from unrelated rings. `extra_edge_elongation_factor` controls additional-edge reach. `node_color`, `edge_color`, their opacity controls, and `draw_border` affect appearance. See constructor signatures for defaults; the historical style deliberately uses different artwork dimensions from the minimal `Graph` defaults.

`GraphStyle.historical()`, `.light()`, and `.named(name)` return immutable presets. `.palette_names()` lists all ten palettes. Use `dataclasses.replace(style, ...)` for custom radii, lengths, thickness, colours, background, text colour or colony colours, then `style.create_graph(...)`. The sample factories apply the text/colony colours to their objects; background is passed separately to export.

`node_direction_function(parent)` returns radians; `node_length_function(parent)` returns a positive visible edge length. Legacy `node_radius_scale_map`, `edge_length_scale_map`, and `edge_thickness_scale_map` accept a Point. Prefer `SpatialFields` for new code. `spatial_backend="hash"` uses local queries; `"brute"` is the reference implementation. `cell_size` tunes indexing, not geometry rules.

## Growth, coverage and quality

Configure `graph.growth(settings=GrowthSettings(...), policy=...)` before building. The default random frontier spreads growth; `NewestTip` favours the latest branch. Custom policies implement the policy protocol; they cannot be combined with built-in coverage or colony scheduling.

| GrowthSettings option | Meaning |
| --- | --- |
| failures_per_parent | Accumulated local failures (success does not reset this counter) before retiring a parent (30) |
| seed_attempts | Initial seed-placement budget (100) |
| total_attempts | Global attempt cap; None selects an automatically bounded budget |
| coverage | Optional CoverageSettings; None uses ordinary frontier selection |
| max_degree | Maximum incident edges per node (6) |
| loop_attempts / loop_distance | Budget (1000) and search radius (40) for extra connections |
| remove_isolated_nodes | Remove degree-zero nodes at completion (True) |
| refill_passes / refill_attempts | Bounded cleanup/refill rounds (0) and their attempt budget (1000) |

`CoverageSettings` uses `tile_size=25`, `max_tiles=4096`, and `parent_choices=8` to favour underfilled tiles. `allow_components=True` permits reseeding; `reseed_attempts=200` bounds it. Colonies disable automatic unowned reseeding. `boundary_weight=1`, `boundary_band=10`, `narrow_weight=1`, and `narrow_width=20` bias difficult regions; narrow-region weighting requires contour information. Coverage does not guarantee filling every pocket.

`AngleSettings(minimum=0, preferred=0, penalty=0)` measures the smaller angle between outward incident directions in degrees: a straight continuation is 180. The hard minimum bans candidates; the preferred angle and penalty provide soft rejection below the preference. Zero penalty disables soft rejection. The quality recipe uses 40/75/0.85. Strong restrictions can reduce coverage. Cleanup only removes isolated dots, not connected leaves or small components.

## Density and variable scale

`SpatialFields` independently accepts `radius`, `length`, `thickness`, `density`, and `coordinated_scale` scalar fields. Multipliers change local geometry; density is requested nodes per square world unit, converted to preferred spacing `1/sqrt(density)`. Collision constraints still win. `scale_limits=(0.1, 10)`, `spacing_limits=(0.1, 10000)`, `ring_ratio=None`, and `refinement_steps=6` bound adaptation.

```python
from graph_ics import CallableField, ImageField, SpatialFields
fields = SpatialFields(density=CallableField(lambda x, y: 1 / (17 + 25*x/600)**2))
raster = ImageField(((0.0007, 0.003, 0.0007), (0.0007, 0.003, 0.0007)), bounds=(0, 0, 600, 400))
```

`ConstantField(value)` is uniform; `CallableField(function)` receives x and y. `ImageField` interpolates rectangular rows across `(min_x, min_y, max_x, max_y)`. Row zero maps to minimum y (the top in rendered coordinates). `outside="clamp"` repeats edge values; `"constant"` returns `outside_value`; `"error"` rejects out-of-bounds samples. The PNG loader supports red, green, blue, alpha and luminance channels and a mapped value range; loading PNG requires Cairo. Density changes placement; coordinated scale changes geometry; export scale changes output pixels only.

## Regions and experimental contours

`RegionSpec(shape, mode="inside", padding=0, canvas=None, band_width=20)` supports inside, outside and boundary-band regions. Outside mode needs a finite canvas. Shapes may contain holes; illegal areas remain additional exclusions.

`ContourSettings` exposes `mode="contain"`, `"follow"`, or `"terminate"`: containment prevents crossing; follow biases tangent growth without requiring a closed loop; terminate aims ends at boundary anchors. Letter/country silhouette recognition is **not complete**. These are heuristics, not contour tracing or exact boundary coverage.

| Contour control | Purpose and default |
| --- | --- |
| adaptive / minimum_radius | Adapt to local width (True), with minimum radius 1 |
| maximum_neighbor_ratio | Limit adjacent size changes (2) |
| width_resolution / width_samples / width_divisor | Width sampling resolution (10), cap (10000), and conversion to local scale (4) |
| anchor_spacing / max_anchors | Boundary sampling spacing (15) and cap (2000) |
| boundary_fraction | Fraction of growth influenced toward boundary targets (0.6) |
| tangent_window / guidance | Tangent measurement window (10) and bias strength (0.85) |
| tolerance / strict_terminals | Output-space tolerance (0.5) and strict feasibility handling (False) |
| readability | Readability for intended output |

`Readability` uses `output_scale=1`, `stroke=0.5`, `hole_diameter=1`, `edge_gap=0.75`, and `separation=0.75`. These constrain geometry during construction. Exporting below the design scale is rejected; enlarging an export does not retroactively improve coverage. Inspect contour diagnostics for infeasible narrow regions.

## Cooperating and competing colonies

`Colony(id, seeds, weight=1, color="#a6b7c8")` supplies ownership and starting positions. `Interaction(first, second, attraction=0, allow_join=False, clearance=0)` configures each pair. Attraction ranges from -1 (repulsion) to +1 (attraction). Soft repulsion steers growth; hard clearance keeps rival geometry separated. Positive clearance and joining are incompatible. Joining connects ownership groups without relabelling them. Existing nodes do not move.

`ColonySettings` takes colonies and interactions plus `influence_distance=100`, `target_bridges=0`, `bridge_attempts=1000`, and `bridge_distance=40`. Bridge attempts remain bounded and collision checked. Weight affects growth scheduling; influence distance limits steering reach. Strong repulsion can leave intentional empty territory.

## Text, export and animation

`Text(content, x, y, size=32, font="sans-serif", padding=8, color="#e04e3b", opacity=1, align="left", bold=False, italic=False, padding_em=0)` uses a baseline position. Effective exclusion padding is absolute padding plus size times padding_em. Cairo measures the actual font path; font substitution changes output. Text defaults to a rectangular exclusion; set `exclusion_mode="glyph"` to hug the individual outlines. `measure().glyph_region` provides a polygonal region for graph lettering.

`export_graph(graph, path, margin=5, scale=1, background=None, frame="artwork")` exports PNG or SVG. None means transparent. Region framing preserves the canvas; artwork framing crops to visible geometry. Text and border strokes contribute to bounds. Sample commands use region framing with margin 16.

Attach `EventRecorder(graph, path=None, retain=True)` **before** building. `EventLog.load(path)` reads versioned JSONL. `Playback(log, seconds_per_event=0.1, speed=1)` supports advance, seek, pause and resume. `ReplayRenderer` accepts scale, margin, background and frame; `export_sequence(..., fps=24, max_frames=10000)` limits frame export. `LiveGrowth` advances under attempt/time budgets. Replay reveals recorded geometry; it is not a moving-node simulation. See [the animation guide](ANIMATION.md) for its workflow and limitations.

Inspect growth stop status and attempts, quality, coverage, contour and colony reports rather than assuming target counts were attained. `built` means construction stopped, not that every target was met. `to_networkx()` returns a topology copy; `directed=True` includes directed relationships. Parent lineage, connected components and colony ownership express different things.


## Shape and line controls

`Graph(node_shape=..., edge_style=...)`, `GraphStyle`, `build_example`, and the CLI support `circle`, `square`, `diamond`, `triangle`, `hexagon` nodes and `solid`, `dashed`, `dotted`, `double` connections. Direct `Node` uses `shape`; direct `Edge` uses `style`. Polygon vertices fit inside outer_radius; inner_radius defines a similar inner polygon. A zero inner radius fills the shape. Rotation is fixed (square axis-aligned, diamond point-up).

Node collision and endpoint clipping reserve the entire circumscribed disk for every shape. This conservative choice preserves safety and identical layouts when changing shape, though polygon attachment gaps can look larger. Lines remain straight: dash gaps and the centre of a double line remain reserved. Double strokes each use one third of the full thickness with a one-third gap. Dotted lines place circular dots inside the stroke corridor. Curves and arrows are not implemented.

Contour readability uses the polygon's inscribed radius for wall/hole dimensions and one-third thickness for each double stroke. Replay records these choices; older logs without style fields retain circle/solid defaults. Partial animation reveals the actual styled stroke through a clip.

`graph-ics render --help` and `frames --help` explain each flag. The visual controls page (`docs/guide/controls.html`, included in the checkout) includes the complete CLI table, runnable commands and paired figures. The UK input page (`docs/guide/population.html`) documents coordinates, source year, units and the logarithmic density mapping.


See [scene files, dimensions, glyph contours and spatial colour maps](SCENES.md) for JSON/YAML input and complete visual comparisons.
