"""Run selected example directories and report failures without rewriting their READMEs."""
from argparse import ArgumentParser
from pathlib import Path
from time import perf_counter
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
QUICK = ('basic_graph', 'density', 'quality', 'text_hug', 'area_fill')
FIXED = ('basic_graph', 'name_composition', 'sample_library', 'animation')


def discover(root: Path = ROOT) -> tuple[str, ...]:
    return tuple(sorted(path.parent.name for path in (root/'examples').glob('*/example.py')))


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('examples', nargs='*', help='Folder names; omitted selection runs the quick set')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--all', action='store_true', help='Include large, expensive country and panorama examples')
    selection.add_argument('--quick', action='store_true', help='Run a representative small validation set')
    parser.add_argument('--list', action='store_true', help='List available folder names without generating anything')
    parser.add_argument('--seed', type=int, help='Override recipe/scene seeds; preserved hand-written examples keep their own settings')
    parser.add_argument('--nodes', type=int, help='Override recipe/scene node caps; does not change fixed examples')
    args = parser.parse_args(argv)
    names = discover()
    if args.list:
        print('\n'.join(names))
        return 0
    if args.examples and (args.all or args.quick): parser.error('Choose explicit names or --all/--quick')
    if args.nodes is not None and args.nodes < 1: parser.error('--nodes must be positive')
    selected = tuple(dict.fromkeys(args.examples)) if args.examples else names if args.all else QUICK
    unknown = set(selected)-set(names)
    if unknown: parser.error('Unknown examples: '+', '.join(sorted(unknown)))
    records: list[dict[str, object]] = []
    for name in selected:
        command = [sys.executable, '-m', f'examples.{name}.example']
        if name not in FIXED:
            if args.seed is not None: command += ['--seed', str(args.seed)]
            if args.nodes is not None: command += ['--nodes', str(args.nodes)]
        started = perf_counter()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        record: dict[str, object] = dict(example=name, succeeded=result.returncode == 0, returncode=result.returncode,
                                       seconds=perf_counter()-started, command=command[2:], stdout=result.stdout, stderr=result.stderr)
        records.append(record)
        print(f'{name}: {"OK" if result.returncode == 0 else "FAILED"}', flush=True)
        if result.returncode: print(result.stderr, file=sys.stderr)
    (ROOT/'examples/results.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')
    return int(any(not record['succeeded'] for record in records))


if __name__ == '__main__':
    raise SystemExit(main())
