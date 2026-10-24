"""Historical-style name surrounded by a sprawling graph."""
from pathlib import Path
from graph_ics import GraphStyle, Text, GrowthSettings, CoverageSettings, export_graph


def main() -> None:
    style = GraphStyle.historical()
    graph = style.create_graph(target_nodes=420, seed=7, texts=(Text('Graph', 300, 195, size=65, align='center', padding=15),))
    graph.growth(settings=GrowthSettings(coverage=CoverageSettings(tile_size=40, reseed_attempts=200), failures_per_parent=12, total_attempts=12000))
    graph.build()
    destination = Path(__file__).parent/'output'/'figure.png'
    export_graph(graph, destination, frame='region', margin=16, scale=2, background=style.background)
    print(destination)


if __name__ == '__main__':
    main()
