"""Generate a seeded historical-style graph: python -m examples.basic_graph.example."""

from pathlib import Path

from graph_ics import Graph, export_graph


def main() -> None:
    graph = Graph.historical(seed=7)
    graph.build()
    output = Path(__file__).parent/'output'
    for suffix in ('svg', 'png'):
        export_graph(graph, output / f'historical.{suffix}', margin=12, background='#141a20', frame='region')
    print(f'Generated {len(graph.nodes)} nodes and {len(graph.edges)} edges in {output}')


if __name__ == '__main__':
    main()
