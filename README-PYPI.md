# graph_ics

A visual art project and Python library for growing sprawling graph compositions. Shape networks with text, polygon boundaries, density maps, angle constraints and cooperating or competing colonies. Export PNG, SVG and recorded growth animations.

[Website and gallery](https://graph-ics.pippidis.no) · [User guide](https://graph-ics.pippidis.no/guide/) · [Source and runnable examples](https://github.com/pippidis/graph_ics)

## Installation

Requires Python 3.11–3.15. Install `graph-ics` for geometry and graph generation, or `graph-ics[render]` for images, text measurement and GIF export:

```console
python -m pip install "graph-ics[render]"
graph-ics render --example sprawl --palette porcelain --output graph.png
graph-ics list
```

Pycairo may need system Cairo development libraries when a compatible wheel is unavailable. Python 3.15 users may need `PYYAML_FORCE_LIBYAML=0` during installation to use PyYAML without its optional C extension. See the [installation guide](https://graph-ics.pippidis.no/manuals/INSTALLATION.html).

```python
from graph_ics import GraphStyle, build_example, export_graph

graph = build_example('density', palette='porcelain', seed=7)
graph.build()
export_graph(graph, 'density.svg', frame='region', background=GraphStyle.named('porcelain').background)
```

Run `graph-ics gallery --quick --output my-gallery` to generate local visual examples. The complete documentation website and extensive pre-generated artwork are maintained in the source repository rather than bundled in the wheel.

## Scope and limits

This is an early library. Generation uses finite budgets and cannot guarantee complete packing. Narrow contours and small islands may remain incomplete; boundary following and terminal anchoring are experimental. Font availability affects glyph geometry. Population maps are artistic logarithmic mappings, not one node per person.

## Licensing

Code: **PolyForm Noncommercial 1.0.0**. Project-owned artwork and documentation: **CC BY-NC 4.0**. Third-party data retains its own terms. Commercial use requires separate permission from [Johannes Pippidis Lorentzen](https://pippidis.no). Read the [licensing scope](https://github.com/pippidis/graph_ics/blob/main/LICENSING.md).

Started in 2022 to create graphics for a presentation about money laundering and anti-money laundering, graph_ics developed through several iterations into this generative art library.
