# Changelog

## 1.0.0 - 2026-11-07

Establishes the stable baseline for the Python API and CLI: graph generation, JSON/YAML scenes, rendering and recorded growth replay. No intentional API or CLI compatibility changes from 0.0.1.

- Make PyPI installation and package naming consistent across the READMEs, website and installation manual.
- Validate tests, lint and typing before the publishing workflow builds distributions.
- Extend isolated wheel/source installation checks with PNG and SVG rendering checks.
- Fix gallery generation to look up the published `graph-graphics` package metadata.

Finite growth budgets, font-dependent output, experimental boundary following and terminal anchoring remain documented limitations.

## 0.0.1 - 2026-10-24

A Python library and CLI for generative network artwork, with reproducible recipes, spatial density and colour fields, polygon boundaries, text contours, multiple colonies and replay exports. Includes a visual option guide, offline gallery, UK/Spain population examples, JSON/YAML scenes and PNG/SVG/GIF output.

This is an early release. Boundary following and terminal anchoring remain experimental. Area filling uses bounded searches and can leave gaps in narrow or disconnected regions; node budgets are caps, not guaranteed achieved counts. Font availability and rasterization can affect text output across systems. See the manuals for units, constraints and data attribution.

Published on [PyPI as graph-graphics](https://pypi.org/project/graph-graphics/0.0.1/), with the gallery and documentation at [graph-ics.pippidis.no](https://graph-ics.pippidis.no).

The documentation website is consolidated under `docs/`. Runnable demonstrations each have an example folder, maintained instructions and local outputs, with a selective batch runner. Wheel/source packages exclude repository-only artwork and use a dedicated PyPI description.
