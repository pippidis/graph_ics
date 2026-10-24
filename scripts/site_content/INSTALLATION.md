# Installation and environment setup

Use Python 3.11 through 3.15. Install from a source checkout or a locally built wheel. The installed package name is `graph-ics`, the import is `graph_ics`, and the CLI is `graph-ics` or `python -m graph_ics`.

## Windows / PowerShell

From the repository root:

```powershell
.\scripts\setup_venv.bat
```

It creates/reuses `.venv` and installs `requirements_dev.txt` by default. Pass `base` or `render` to select a smaller group. From the repository root, explicit interpreter paths avoid activation requirements:

```powershell
.\.venv\Scripts\python.exe -m graph_ics list
.\.venv\Scripts\python.exe -m graph_ics render --example typography --palette arctic --output examples/output/arctic.png
.\.venv\Scripts\python.exe -c "import cairo; print(cairo.cairo_version_string())"
```

Alternatively create the environment yourself with `py -3.13 -m venv .venv`, then install with `.\.venv\Scripts\python.exe -m pip install -r requirements_dev.txt`. The render requirements install Pycairo. If pip can use a compatible wheel, a separate Cairo build toolchain is not required. If pip falls back to a source build, follow the current [Pycairo installation instructions](https://pycairo.readthedocs.io/en/latest/getting_started.html): Cairo headers/libraries and pkg-config are required for building. Verify the active interpreter's Python version/architecture and the `import cairo` command before diagnosing rendering failures.

`. .\scripts\toggle_venv.ps1` toggles the project environment when your existing PowerShell script policy permits it. The scripts do not change machine execution policy. Direct interpreter paths always remain available.

## Linux and macOS

Create an environment with `python3 -m venv .venv`. If building Cairo bindings on Ubuntu/Debian, install `libcairo2-dev`, `pkg-config`, and `python3-dev`. On macOS/Homebrew, install `cairo` and `pkg-config`. These are the platforms/dependencies described in the [official Pycairo guide](https://pycairo.readthedocs.io/en/latest/getting_started.html).

```console
.venv/bin/python -m pip install -r requirements_dev.txt
.venv/bin/python -m graph_ics gallery --quick
```

## Requirements and optional dependencies

| File / extra | Purpose |
| --- | --- |
| `requirements.txt` | Editable base package; dependencies come from `pyproject.toml`, currently Shapely, NetworkX and PyYAML. |
| `requirements_render.txt` / `.[render]` | Base package plus Pycairo for rendering/text measurement and Pillow for GIF export. |
| `requirements_dev.txt` | Render installation plus testing, strict typing, linting, stubs, and build tools. |

The short requirements files deliberately reference project extras rather than duplicate version constraints. Geometry-only import, graph generation, validation, event logging, and playback timing do not import Cairo. Text specifications can be created without Cairo; measuring them requires it.

For an installed wheel, use `python -m pip install path/to/graph_ics-...whl` for base use, then install Pycairo for rendering. The wheel contains the CLI and `py.typed`. `python -m scripts.check_wheel` creates a fresh environment and verifies base-only operation; its dependency installation needs network access or a configured local package source.

The optional `.[data]` extra installs Pillow for `scripts/prepare_uk_data.py`. It is only needed to refresh the public-source UK and Spain inputs; the bundled example itself works offline with the normal render installation. Development extras include this preparation dependency.

## Refreshing an environment after a Python upgrade

A virtual environment is tied to the interpreter used to create it. Replacing that interpreter can break the old environment. Recreate `.venv` with the chosen installed Python, then reinstall `requirements_dev.txt`; do not copy old site-packages into the new environment.

On Windows with Python 3.15, PyYAML may need its pure-Python build if no compatible wheel is available. This project uses its safe Python loader and does not require the optional LibYAML extension:

```powershell
$env:PYYAML_FORCE_LIBYAML = "0"
.venv\Scripts\python.exe -m pip install -r requirements_dev.txt
Remove-Item Env:PYYAML_FORCE_LIBYAML
```

The setup helper and CI use this option for reproducible installation without a YAML C compiler. The interpreter path can also be supplied to the setup helper through `GRAPH_ICS_PYTHON` when `python` is not on PATH.
