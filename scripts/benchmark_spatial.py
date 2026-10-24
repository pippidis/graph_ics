"""Compare indexed and exhaustive generation separately from rendering."""

from dataclasses import asdict
from math import sqrt
from pathlib import Path
from time import perf_counter
from typing import Literal
import json
import platform
import tracemalloc

from shapely.geometry import box

from graph_ics import Graph, GrowthSettings, export_graph


def make_graph(count: int, size: float, backend: Literal['hash', 'brute']) -> Graph:
    graph = Graph(target_nodes=count, target_seed_nodes=3, seed=7, outline_polygon=box(0, 0, size, size), spatial_backend=backend,
                  edge_length_min=10, edge_length_max=20, node_inner_radius=2, node_outer_radius=4, node_buffer=1, edge_node_distance=1.4)
    graph.growth(settings=GrowthSettings(failures_per_parent=10, total_attempts=5000))
    return graph


def signature(graph: Graph) -> tuple[object, ...]:
    return (tuple((n.id, n.center.x, n.center.y) for n in graph.nodes), tuple((e.start_node.id, e.end_node.id) for e in graph.edges))


def main() -> None:
    output = Path('artifacts/spatial_benchmark')
    figures = output/'figures'
    figures.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    cards: list[str] = []
    rows: list[str] = []
    cases = [('growing', count, 300*sqrt(count/100)) for count in (100, 300, 600)] + [('crowded', count, 160.0) for count in (100, 300, 600)]
    for name, count, size in cases:
        previous: tuple[object, ...] | None = None
        backends: tuple[Literal['hash', 'brute'], ...] = ('brute', 'hash')
        for backend in backends:
            start = perf_counter()
            graph = make_graph(count, size, backend)
            graph.build()
            elapsed = perf_counter()-start
            state = signature(graph)
            if previous is not None: assert state == previous
            previous = state
            # A separate repeat measures Python allocations without contaminating timing.
            tracemalloc.start()
            measured = make_graph(count, size, backend)
            measured.build()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert signature(measured) == state
            stats = asdict(graph.collision_stats)
            record: dict[str, object] = dict(case=name, target=count, size=size, backend=backend, nodes=len(graph.nodes), attempts=graph.growth().attempts,
                                             status=graph.growth().status.value, seconds=elapsed, python_peak_bytes=peak, **stats)
            records.append(record)
            stem = f'{name}-{count}-{backend}'
            for suffix in ('png', 'svg'): export_graph(graph, figures/f'{stem}.{suffix}', frame='region', margin=12, background='#101318')
            rows.append(f'<tr><td>{name}</td><td>{count}</td><td>{backend}</td><td>{len(graph.nodes)}</td><td>{elapsed:.3f}</td><td>{stats["exact_checks"]}</td><td>{peak/1024:.0f}</td></tr>')
            cards.append(f'<article><h2>{stem}</h2><a href="figures/{stem}.svg"><img src="figures/{stem}.png" alt="{stem}"></a></article>')
            print(f'{name} {count} {backend}: {len(graph.nodes)} nodes, {elapsed:.3f}s, {stats["exact_checks"]} exact checks', flush=True)
    manifest = dict(python=platform.python_version(), platform=platform.platform(), seed=7, records=records)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Spatial index benchmark</title><style>body{background:#101318;color:#ddd;font:16px sans-serif;margin:24px}td,th{padding:8px;text-align:right}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}img{width:100%}</style><h1>Same geometry, fewer collision checks</h1><p>One timing per case, seed 7; geometry signatures match between backends. Rendering excluded. Python peak allocation measured in a separate repeat; native GEOS/Cairo memory is excluded. These small local samples do not establish asymptotic complexity.</p><table><tr><th>Case</th><th>Target</th><th>Backend</th><th>Actual</th><th>Seconds</th><th>Exact checks</th><th>Python peak KiB</th></tr>'+''.join(rows)+'</table><main>'+''.join(cards)+'</main></html>'
    (output/'index.html').write_text(html, encoding='utf-8')


if __name__ == '__main__':
    main()
