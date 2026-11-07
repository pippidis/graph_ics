"""Check isolated base installs, then PNG/SVG output with the rendering extra."""

from argparse import ArgumentParser
from pathlib import Path
import subprocess
import tempfile
import venv
import os


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=Path('dist'), help='Directory containing exactly one wheel and one source archive')
    args = parser.parse_args()
    wheels = list(args.dist.glob("graph_graphics-*.whl"))
    sources = list(args.dist.glob("graph_graphics-*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1: raise RuntimeError('Build exactly one wheel and source archive before running this check')
    for artifact in (*wheels, *sources): check_distribution(artifact.resolve())


def check_distribution(artifact: Path) -> None:
    with tempfile.TemporaryDirectory(prefix='graph-ics-wheel-') as temporary:
        root = Path(temporary)
        venv.EnvBuilder(with_pip=True).create(root / 'env')
        python = root / 'env' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        environment = os.environ.copy()
        environment['PYYAML_FORCE_LIBYAML'] = '0'
        subprocess.run([str(python), '-m', 'pip', 'install', str(artifact)], env=environment, check=True)
        code = "import graph_ics, importlib.util; assert graph_ics.Graph().build(); assert graph_ics.build_example('sprawl', nodes=8).build(); from graph_ics.uk import population_data; assert population_data()['metadata']['year'] == 2020; assert importlib.util.find_spec('cairo') is None; assert importlib.util.find_spec('colormap') is None; print(graph_ics.__file__)"
        subprocess.run([str(python), '-I', '-c', code], cwd=root, check=True)
        subprocess.run([str(python), '-I', '-m', 'graph_ics', 'list'], cwd=root, check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', f'{artifact}[render]'], env=environment, check=True)
        for suffix in ('png', 'svg'):
            output = root / f'smoke.{suffix}'
            subprocess.run([str(python), '-I', '-m', 'graph_ics', 'render', '--example', 'sprawl', '--nodes', '12', '--output', str(output)], cwd=root, check=True)
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError(f'Rendering did not produce {output.name}')
        verify = "from PIL import Image; import xml.etree.ElementTree as ET; from importlib.metadata import version; image = Image.open('smoke.png'); image.verify(); assert ET.parse('smoke.svg').getroot().tag == '{http://www.w3.org/2000/svg}svg'; print('Installed version:', version('graph-graphics'))"
        subprocess.run([str(python), '-I', '-c', verify], cwd=root, check=True)
        print(f'Installed and checked {artifact.name}', flush=True)


if __name__ == '__main__':
    main()
