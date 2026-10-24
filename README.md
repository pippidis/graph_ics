
# graph_ics

graph_ics is a long-running visual art project, developed into a Python package for growing sprawling graph compositions. It explores how small connections fill space, respond to contours, and form patterns.

Generate sprawling graph artwork with hollow nodes, clipped connections, and room for text. Guide growth with density maps, polygon boundaries, angle limits, and cooperating or competing colonies. Export PNG, SVG, or a recorded growth sequence.

![graph_ics wordmark in a continuing graph network](docs/images/preview.png)

[Gallery website](https://graph-ics.pippidis.no) | [User guide](https://graph-ics.pippidis.no/guide/) | [Logo](docs/logo/index.html) | [Install](scripts/site_content/INSTALLATION.md) | [Runnable examples](examples/README.md) | [Examples and CLI](scripts/site_content/EXAMPLES.md) | [Parameters](scripts/site_content/PARAMETERS.md) | [Animation](scripts/site_content/ANIMATION.md) | [API](scripts/site_content/API.md)

The project website, gallery and documentation are available at [graph-ics.pippidis.no](https://graph-ics.pippidis.no). For offline browsing, open [the included gallery](docs/index.html) from a downloaded checkout.

## Get started

Requires Python 3.11-3.15. The package is distributed on PyPI as `graph-graphics`, imported in Python as `graph_ics`, and accessed through the `graph-ics` command-line interface.

### Install from PyPI

Install the package with rendering support:

```console
python -m pip install "graph-graphics[render]"
```

For geometry and graph generation without the optional rendering dependencies:

```console
python -m pip install graph-graphics
```

Generate your first image:

```console
graph-ics render --example typography --palette arctic --output arctic.png
graph-ics list
```

### Install from source

To develop or modify the library, clone the repository and create a virtual environment:

```console
git clone https://github.com/pippidis/graph_ics.git
cd graph_ics
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on Linux/macOS, then:

```console
python -m pip install -e ".[dev,render]"
```

The image is written to the path you choose. `python -m graph_ics` also works if the console command is not on your PATH. See [installation](scripts/site_content/INSTALLATION.md) for PowerShell helpers, Cairo prerequisites, and geometry-only use.

## Browse the examples

```console
graph-ics gallery
```

Open [docs/index.html](docs/index.html) directly from the checkout. It is a self-contained website with a dedicated Home page, searchable Gallery, integrated visual Guide and About page. It includes recipes, large compositions, ten colour schemes, and UK/Spain population examples. The command above regenerates it. Search by subject, filter by palette, inspect full-resolution images, or copy a command to reproduce an example. PNG and SVG files live in `figures/` underneath the index.

The visual guide compares five node shapes, four connection styles, angle restrictions, density, output settings, and replay timing. Every CLI option has a short explanation and a relevant example. The Guide groups visual comparisons into chapters with previous/next navigation; the full reference manuals are generated from the Markdown documentation with `python -m scripts.prepare_site` in a source checkout. Use `graph-ics gallery --quick` for a smaller preview, or `--output PATH` to choose another folder. The public gallery and README preview are included in the checkout. Use `--all-palettes` to generate the expanded colour matrix.

```console
graph-ics list
graph-ics describe density
graph-ics render --example sprawl --palette porcelain --node-shape hexagon --edge-style dashed --output examples/output/hexagons.svg
graph-ics render --example uk_population --palette porcelain --output examples/output/uk.png
```

The UK example uses bundled WorldPop 2020 density estimates and a Natural Earth boundary, so it runs offline. Its logarithmic mapping favours readable urban detail rather than representing one person per node. [Data sources and transformations](src/data/README.md).

The documentation website is hosted through GitHub Pages and deployed from the `docs/` directory on the `main` branch. The public website is available at [graph-ics.pippidis.no](https://graph-ics.pippidis.no), while its source files remain available in the repository for offline browsing and regeneration.

## Use Python

```python
from graph_ics import GraphStyle, build_example, export_graph

graph = build_example('density', palette='arctic', seed=7)
graph.build()
export_graph(graph, 'density.svg', frame='region', margin=16,
             background=GraphStyle.named('arctic').background)
```

Example factories return configured, unbuilt graphs. For custom settings, use `Graph` or `GraphStyle.create_graph()` and configure `graph.growth(settings=...)` before the first step. [Parameters](scripts/site_content/PARAMETERS.md) describes dimensions, spatial fields, contours, coverage, colonies, text, and exports.

## Record growth

```console
graph-ics render --example sprawl --nodes 80 --output examples/output/static.png --record examples/output/growth.jsonl
graph-ics frames --log examples/output/growth.jsonl --output examples/output/frames --fps 24
```

Replay preserves accepted geometry, styles, and text paths. It does not rerun generation or move existing nodes. The [animation guide](scripts/site_content/ANIMATION.md) covers playback, seeking, bounded live growth, and frame exports.

## Limits

This is an early library. Node targets and requested density are subject to finite attempt budgets and available space. Inspect the achieved count and growth status when exact population matters.

Containment and collision rules apply to all geometry. Boundary following and terminal anchoring are experimental: complex letters, narrow coastlines, and small islands may remain incomplete. Text supports rectangular or glyph exclusions, and graphs can grow inside letter contours. Area-fill mode searches disconnected and underfilled regions while reporting caps and remaining tile gaps. Curved edges, moving-node simulation, and video encoding are not included.

## Tests and tooling

```console
python -m pip install -e ".[dev,render]"
python -m pytest --cov=graph_ics --basetemp=.pytest_tmp
python -m scripts.typecheck
python -m ruff check .
```

To build and validate the distributions for PyPI:

```console
python -m scripts.release --check
python -m scripts.check_wheel
python -m twine check dist/*
```

The release script requires an empty `dist/` directory and creates both the wheel and source distribution. The wheel-checking script installs each distribution into a fresh environment and verifies core functionality.

Source modules live directly in `src/`, installed as `graph_ics`. The package includes type information. Release validation includes behavioral tests, typing, linting, distribution builds and clean-install checks. Figures complement numerical checks: density and composition need visual review as well as collision assertions.

## Licence

The code is licensed under [PolyForm Noncommercial 1.0.0](LICENSE). Project-owned artwork and documentation are licensed under [CC BY-NC 4.0](LICENSE-ARTWORK). For commercial use, contact [Johannes Pippidis Lorentzen](https://pippidis.no) to arrange a separate paid licence. See [licensing scope and exceptions](LICENSING.md). Bundled population data retains its own [attribution and licence](src/data/README.md).

See [scene files, dimensions, glyph contours and spatial colour maps](scripts/site_content/SCENES.md) for JSON/YAML input and complete visual comparisons.

## About the project

graph_ics began in 2022, when I needed graphics for a presentation about money laundering and anti-money laundering and decided to build a generator to create them. It went through several iterations over the years before I finally had time to bring it together as a usable library and share the results.

A project by [Johannes Pippidis Lorentzen](https://pippidis.no).
