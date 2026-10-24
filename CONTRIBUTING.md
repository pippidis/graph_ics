# Contributing

Use Python 3.11-3.15 and install `requirements_dev.txt` in a virtual environment. The package uses a flat `src/` directory, installed as `graph_ics`; avoid adding a second package layer.

Keep interfaces typed, validate user input at the boundary, and test behavior rather than implementation details. Long lines are fine when they keep a coherent operation readable. Changes to geometry or rendering need visual examples as well as automated checks.

```console
python -m pytest
python -m ruff check .
python -m scripts.typecheck
python -m build
python -m scripts.check_wheel
```

The checked-in `docs/` is the public website and works offline. To refresh presentation and manuals without regenerating expensive artwork:

```console
python -m scripts.prepare_site
```

To regenerate the artwork first, run `graph-ics gallery`, then the refresh command. The website has a Home page, a separate Gallery, a nine-chapter Guide and About. Chapter composition lives in `src/site_structure.py`; reference manuals are generated from `scripts/site_content/*.md` (release instructions stay in the repository). Update those sources, not their HTML copies. The documentation build requires the development dependencies. The logo and homepage banner are under `docs/logo/figures/`; regenerate them with `python -m scripts.generate_logos`.

For bug reports, include the Python/platform versions, the command or scene file, random seed, expected result and actual result. Attach a small image for visual problems. Do not include confidential input data.

Before contributing, read [the licensing scope](LICENSING.md). Commercial permissions are offered separately by the rights holder; contributions must not introduce code or assets whose terms conflict with that arrangement.

## Public development

Open an issue or pull request in [graph_ics](https://github.com/pippidis/graph_ics). Keep changes focused, describe their behavior and include validation results. Add demonstrations to the [example library](examples/README.md), with a manually maintained README and reproducible output. Run `python -m scripts.generate_examples --quick` for representative visual checks; select affected examples for geometry changes. The website lives in `docs/`; generated HTML follows its Markdown sources and the page generators.
