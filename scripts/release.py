"""Prepare a graph-ics release.

1. Set the version in pyproject.toml and update CHANGELOG.md. Check the package
   name on PyPI and confirm the public repository and documentation links.
2. Run pytest, ruff, scripts.typecheck and scripts.generate_examples --quick.
   Inspect affected full-size examples, including maps and text compositions.
3. Run scripts.prepare_site and scripts.check_site. Review desktop/mobile pages.
4. Run this module with --check to build and validate wheel/source distributions.
   Run scripts.check_wheel afterward for clean-install checks (network required).
5. For GitHub Pages, select Settings > Pages > Deploy from a branch > main > /docs.
   Set graph-ics.pippidis.no as the custom domain and configure DNS and HTTPS.
   The default project address is https://pippidis.github.io/graph_ics/.
6. Publish the validated distributions using PyPI's trusted publishing or Twine,
   then install the published version in a fresh environment to verify it.

This script only builds and checks local artifacts. It never uploads or deploys.
The code uses PolyForm Noncommercial; artwork/docs use CC BY-NC 4.0.
Keep third-party data attribution intact. Python 3.15 may need
PYYAML_FORCE_LIBYAML=0 during dependency installation; Cairo source builds need
system libraries. Verify CI on every supported Python/platform before release.

Packaging guide: https://packaging.python.org/en/latest/tutorials/packaging-projects/
Trusted publishing: https://docs.pypi.org/trusted-publishers/
"""
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='Build and validate distributions locally')
    args = parser.parse_args()
    if not args.check:
        parser.print_help()
        return
    root = Path(__file__).resolve().parents[1]
    destination = root/'dist'
    if destination.exists() and any(destination.iterdir()): parser.error('dist must be empty; move or remove old artifacts first')
    subprocess.run([sys.executable, '-m', 'build', '--outdir', str(destination)], cwd=root, check=True)
    archives = sorted(str(path) for path in destination.iterdir() if path.suffix in ('.whl', '.gz'))
    subprocess.run([sys.executable, '-m', 'twine', 'check', '--strict', *archives], cwd=root, check=True)


if __name__ == '__main__':
    main()
