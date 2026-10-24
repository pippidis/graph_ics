"""Check the flat src layout under its actual installed graph_ics package name.

Mypy does not follow setuptools' editable import finder. Use a fresh temporary
package mapping, never a stale build directory or a second source tree.
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))
    targets: list[str] = config['tool']['mypy']['files']
    with tempfile.TemporaryDirectory(prefix='graph-ics-types-') as temporary:
        package = Path(temporary)/'graph_ics'
        shutil.copytree(root/'src', package, ignore=shutil.ignore_patterns('__pycache__'))
        environment = os.environ.copy()
        environment['MYPYPATH'] = temporary
        paths = [str(package/target.removeprefix('src/')) if target.startswith('src/') else str(root/target) for target in targets]
        result = subprocess.run([sys.executable, '-m', 'mypy', '--config-file', str(root/'pyproject.toml'), *paths], cwd=root, env=environment, capture_output=True, text=True)
        print(result.stdout.replace(str(package), str(root/'src')), end='')
        print(result.stderr, file=sys.stderr, end='')
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
