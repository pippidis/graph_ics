# Source architecture

The modules in this directory are installed as `graph_ics`; setuptools maps the flat directory to that package. `__init__.py` defines the public convenience imports. `py.typed` marks the distribution as typed.

| Modules | Responsibility |
| --- | --- |
| `graph`, `node`, `edge`, `vector`, `obj` | Graph state and geometric objects |
| `growth`, `spatial`, `coverage`, `quality` | Incremental generation, collision queries, reseeding and junction constraints |
| `contours`, `text`, `colonies` | Region constraints, measured text and interactions between colonies |
| `fields`, `color_fields`, `colors`, `styles` | Spatial variation, colour interpolation and appearance |
| `drawing`, `rendering` | Rendering interface and optional Cairo PNG/SVG output |
| `replay`, `animation` | Event recording, deterministic playback and frame/GIF export |
| `scene`, `cli`, `__main__` | Validated JSON/YAML configuration and command-line entry points |
| `validation` | Independent final-geometry checks |
| `samples`, `uk`, `data/` | Reproducible factories and attributed offline map data |
| `gallery`, `option_gallery`, `scene_gallery`, `gallery_page`, `site_structure`, `logo` | Visual demonstrations, website generation and identity artwork |

Geometry and event logging work without Cairo. Rendering and text measurement load it only when needed. See the [algorithm](../scripts/site_content/ALGORITHM.md), [API](../scripts/site_content/API.md) and [contributor guide](../CONTRIBUTING.md) before changing generation rules. Changes should retain numerical invariants and be checked visually using the example library.
