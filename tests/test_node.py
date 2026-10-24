import pytest
import cairo
from tempfile import NamedTemporaryFile
import os

def test_node_creation(node):
    n = node()
    assert isinstance(n, node)
    assert n.center.x == 0
    assert n.center.y == 0
    assert n.is_seed_node == False
    assert n.color == '#545454'
    assert n.opacity == 1.0
    assert n.outer_radius == 2
    assert n.inner_radius == 1
    assert n.buffer == 1
    assert n.buffer_radius == 3
    assert n.min_edge_length == 1
    assert n.id.startswith('node_')  # test if id is correctly generated

@pytest.mark.parametrize("x1, y1, x2, y2, radius1, buffer1, radius2, buffer2, expected", [
    (0, 0, 0, 0, 10, 1, 10, 1, True),
    (0, 0, 100, 100, 10, 1, 10, 1, False),
    (0, 0, 10, 0, 10, 1, 10, 1, True)
])
def test_node_overlap(node, x1, y1, x2, y2, radius1, buffer1, radius2, buffer2, expected):
    n1 = node(x1, y1, outer_radius=radius1, buffer=buffer1)
    n2 = node(x2, y2, outer_radius=radius2, buffer=buffer2)
    assert n1.overlap(n2) == expected

def test_node_eq(node):
    n1 = node()
    n2 = node()
    assert n1 == n2
    n3 = node(1,1)
    assert n1 != n3
    assert n1 != 1.0

@pytest.mark.parametrize("x1, y1, x2, y2, expected", [
    (0, 0, 10, 0, 10),
    (0, 0, 0, 0, 0),
])
def test_node_distance_to(node, x1, y1, x2, y2, expected):
    n1 = node(x1, y1)
    n2 = node(x2, y2)
    assert n1.distance_to(n2) == expected

def test_node_draw(node, tmp_path):
    n = node(5,5)
    path = str(tmp_path / 'node.svg') # Need to create a temp svg for testing the draw function
    with cairo.SVGSurface(path, 10, 10) as surface:
        context = cairo.Context(surface)
        n.draw(context)
    os.remove(path)
