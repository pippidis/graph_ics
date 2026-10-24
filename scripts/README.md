# Supporting scripts

Run Python modules from the repository root after installing `requirements_dev.txt`.

| Command | Purpose |
| --- | --- |
| `python -m scripts.generate_examples --quick` | Run representative examples; use names or `--all` for other selections |
| `python -m scripts.prepare_site` | Refresh `docs/` presentation and Markdown manuals using existing artwork |
| `python -m scripts.check_site` | Check local HTML links, assets and anchors under `docs/` |
| `graph-ics gallery --output docs` | Regenerate the full website artwork; expensive country and large examples included |
| `python -m scripts.generate_logos` | Regenerate `docs/logo/` assets |
| `python -m scripts.generate_readme_preview` | Refresh the repository banner |
| `python -m scripts.generate_animation` | Generate the animation example's logs, frames and playback page |
| `python -m scripts.benchmark_spatial` | Compare collision-query performance |
| `python -m scripts.typecheck` | Run strict typing with the flat source mapped to `graph_ics` |
| `python -m scripts.check_wheel --dist dist` | Install each built distribution in an isolated environment and check base operation |
| `python -m scripts.prepare_uk_data uk` | Prepare population inputs (`uk` or `spain`); follow the data provenance instructions |

`setup_venv.bat` installs the requested dependency group on Windows. Dot-source `toggle_venv.ps1` to toggle activation when local PowerShell policy permits it. Neither changes machine execution policy. See [installation](../scripts/site_content/INSTALLATION.md).

Example generation never writes README files. Full website regeneration and example regeneration are separate operations so a small change need not rerun every country map. No script here uploads packages or creates a release ZIP.

The `site_content/` directory holds the Markdown sources for website manuals. `prepare_site` renders them into `docs/manuals/`; the published `docs/` tree contains only website files and its README. Release instructions and local packaging checks live in [scripts/release.py](../scripts/release.py).

Run `python -m scripts.release --help` for the release checklist, or `python -m scripts.release --check` to build and validate distributions locally.
