"""World sampling, field validation, density trends, and variable-size geometry."""

from pathlib import Path
import cairo
import pytest
from shapely.geometry import box

from graph_ics import CallableField, ConstantField, Graph, GrowthSettings, ImageField, SpatialFields
from tests.geometry_assertions import validate


def test_bilinear_mapping_and_outside() -> None:
    image = ImageField(((1, 3), (5, 7)), (-10, -20, 10, 20))
    assert image.sample(0, 0) == 4
    assert image.sample(-10, -20) == 1
    assert image.sample(10, 20) == 7
    assert image.sample(100, 100) == 7
    assert ImageField(((2,),), (0, 0, 1, 1)).sample(0.5, 0.5) == 2
    assert ImageField(((2,),), (0, 0, 1, 1), 'constant', 8).sample(2, 2) == 8
    with pytest.raises(ValueError): ImageField(((2,),), (0, 0, 1, 1), 'error').sample(2, 2)
    with pytest.raises(ValueError): ImageField(((1, 2), (3,)), (0, 0, 1, 1))


def test_png_channels(tmp_path: Path) -> None:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2)
    context = cairo.Context(surface)
    context.set_source_rgba(1, 0, 0, 0.5)
    context.paint()
    surface.write_to_png(str(tmp_path/'map.png'))
    assert ImageField.from_png(tmp_path/'map.png', (0, 0, 10, 10), channel='red').sample(5, 5) == 1
    assert ImageField.from_png(tmp_path/'map.png', (0, 0, 10, 10), channel='alpha').sample(5, 5) == pytest.approx(128/255)


def test_constant_equivalence_and_legacy_adapter() -> None:
    graphs = [Graph(seed=7, target_nodes=50), Graph(seed=7, target_nodes=50, fields=SpatialFields(radius=ConstantField(1), length=ConstantField(1), thickness=ConstantField(1))),
              Graph(seed=7, target_nodes=50, node_radius_scale_map=lambda point: 1)]
    for graph in graphs: graph.build()
    assert [[n.center.wkt for n in g.nodes] for g in graphs] == [[n.center.wkt for n in graphs[0].nodes]]*3


@pytest.mark.parametrize('value', [-1, 0, float('inf'), float('nan')])
def test_invalid_sample(value: float) -> None:
    graph = Graph(fields=SpatialFields(radius=CallableField(lambda x, y: value)))
    with pytest.raises(ValueError): graph.build()


def test_variable_geometry_and_index_equivalence() -> None:
    fields = SpatialFields(radius=CallableField(lambda x, y: 0.4+x/100), thickness=CallableField(lambda x, y: 0.4+y/100),
                           density=CallableField(lambda x, y: 1/(8+x/10)**2), ring_ratio=0.4)
    graphs = [Graph(target_nodes=120, seed=21, fields=fields), Graph(target_nodes=120, seed=21, fields=fields, spatial_backend='brute')]
    for graph in graphs:
        graph.build()
        validate(graph)
        assert all(n.inner_radius == pytest.approx(n.outer_radius*0.4) for n in graph.nodes)
        assert all(a.distance_to(b) > max(a.preferred_spacing, b.preferred_spacing) for i, a in enumerate(graph.nodes) for b in graph.nodes[:i])
    assert [n.center.wkt for n in graphs[0].nodes] == [n.center.wkt for n in graphs[1].nodes]


def test_density_ordering_over_seeds_and_conflicts() -> None:
    totals = []
    for spacing in (10, 25):
        count = 0
        for seed in (0, 7, 21):
            graph = Graph(outline_polygon=box(0, 0, 150, 150), target_nodes=1000, target_seed_nodes=5, seed=seed,
                          fields=SpatialFields(density=ConstantField(1/spacing**2)))
            graph.growth(settings=GrowthSettings(failures_per_parent=8, total_attempts=5000))
            graph.build()
            count += len(graph.nodes)
        totals.append(count)
    assert totals[0] > totals[1]*2
    graph = Graph(fields=SpatialFields(density=ConstantField(1000)))
    graph.build()
    assert graph.density_conflicts > 0


def test_field_steps_and_extreme_limits() -> None:
    fields = SpatialFields(coordinated_scale=CallableField(lambda x, y: 0.5+x/100))
    first, second = Graph(seed=7, target_nodes=60, fields=fields), Graph(seed=7, target_nodes=60, fields=fields)
    first.build()
    engine = second.growth()
    while not engine.done: engine.step(1)
    assert [n.center.wkt for n in first.nodes] == [n.center.wkt for n in second.nodes]
    limited = SpatialFields(radius=ConstantField(1e100), density=ConstantField(1e-100), spacing_limits=(1, 100))
    assert limited.scale(limited.radius, 0, 0) == 10
    assert limited.spacing(0, 0) == 100
    with pytest.raises(ValueError): SpatialFields(scale_limits=(0, 1))
    with pytest.raises(ValueError): SpatialFields(ring_ratio=1)
    with pytest.raises(ValueError): SpatialFields(refinement_steps=0)
