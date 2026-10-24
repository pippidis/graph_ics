"""Shared execution for the recipe and scene examples; never writes documentation."""
from argparse import ArgumentParser
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
import json
import yaml
from graph_ics import Graph, GraphStyle, build_example, export_graph, validate_graph
from graph_ics.scene import SceneConfig


def arguments() -> tuple[int | None, int | None]:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, help='Override the reproducible seed (default: recipe/config seed)')
    parser.add_argument('--nodes', type=int, help='Override the node cap; small values make faster smoke checks')
    args = parser.parse_args()
    if args.nodes is not None and args.nodes < 1: parser.error('--nodes must be positive')
    return args.seed, args.nodes


def render(graph: Graph, directory: Path, background: str | None, seed: int) -> None:
    started = perf_counter()
    graph.build()
    validation = validate_graph(graph)
    output = directory/'output'
    output.mkdir(exist_ok=True)
    for suffix in ('png', 'svg'): export_graph(graph, output/f'figure.{suffix}', frame='region', margin=16, background=background)
    result = dict(seed=seed, target_nodes=graph.target_nodes, nodes=len(graph.nodes), edges=len(graph.edges), status=graph.growth().status.value,
                  seconds=perf_counter()-started, validation=asdict(validation))
    (output/'results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'{directory.name}: {len(graph.nodes)} nodes; {output}')


def recipe_main(name: str, directory: Path) -> None:
    seed, nodes = arguments()
    seed = 7 if seed is None else seed
    render(build_example(name, palette='porcelain', seed=seed, nodes=nodes), directory, GraphStyle.named('porcelain').background, seed)


def scene_main(directory: Path) -> None:
    seed, nodes = arguments()
    data = yaml.safe_load((directory/'config.yaml').read_text(encoding='utf-8'))
    if seed is not None: data['seed'] = seed
    if nodes is not None: data['nodes'] = nodes
    scene = SceneConfig.from_mapping(data, base=directory)
    render(scene.graph, directory, scene.background, data.get('seed', 7))
