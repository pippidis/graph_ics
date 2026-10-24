"""Choose an explained factory, generate it, and save static artwork plus a replay log."""
from pathlib import Path
from graph_ics import GraphStyle, EventRecorder, build_example, describe_example, export_graph, validate_graph


def main() -> None:
    name, palette = 'density', 'arctic'
    description = describe_example(name)
    print(description.explanation)
    print('Controls: '+', '.join(description.options))
    print('Limit: '+description.limitation)
    graph = build_example(name, palette=palette, seed=7)
    output = Path(__file__).parent/'output'
    with EventRecorder(graph, path=output/'growth.jsonl'): graph.build()
    validate_graph(graph)
    for suffix in ('png', 'svg'): export_graph(graph, output/'figures'/f'{name}.{suffix}', frame='region', margin=16, background=GraphStyle.named(palette).background)
    print(output)


if __name__ == '__main__':
    main()
