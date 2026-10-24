# Changelog

## 0.0.1 - initial release candidate

A Python library and CLI for generative network artwork, with reproducible recipes, spatial density and colour fields, polygon boundaries, text contours, multiple colonies and replay exports. Includes a visual option guide, offline gallery, UK/Spain population examples, JSON/YAML scenes and PNG/SVG/GIF output.

This is an early release. Boundary following and terminal anchoring remain experimental. Area filling uses bounded searches and can leave gaps in narrow or disconnected regions; node budgets are caps, not guaranteed achieved counts. Font availability and rasterization can affect text output across systems. See the manuals for units, constraints and data attribution.

Release artifacts and hosting are prepared locally; this note does not imply a PyPI upload or live website.

The documentation website is consolidated under `docs/`. Runnable demonstrations each have an example folder, maintained instructions and local outputs, with a selective batch runner. Wheel/source packages exclude repository-only artwork and use a dedicated PyPI description.
