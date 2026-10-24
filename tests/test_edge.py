import pytest
import cairo
import os

def test_edge_creation(node, edge):
    n1 = node(0,0)
    n2 = node(0,20)
    e1 = edge(n1, n2)

    with pytest.raises(ValueError):
        e2 = edge(n1, n1)

def test_edge_overlap(node, edge):
    n1 = node(0,0)
    n2 = node(0,20)
    n3 = node(0,10)
    e1 = edge(n1, n2)
    assert e1.overlap(n3) == True # Overlappin with node

    n4 = node(10,10)
    assert e1.overlap(n4) == False #  Not overlapping with node

    n5 = node(30,10)
    e2 = edge(n4, n5)
    assert e1.overlap(e2) == False # Not overlapping with edge

    n6 = node(-10,10)
    n7 = node(10,10)
    e3 = edge(n6, n7)
    assert e1.overlap(e3) == True # Overlapping with edge

def test_edge_draw(node, edge, tmp_path):
    n1 = node(10,10)
    n2 = node(90,90)
    e1 = edge(n1, n2)

    path = str(tmp_path / 'edge.svg') # Need to create a temp svg for testing the draw function
    with cairo.SVGSurface(path, 100, 100) as surface:
        context = cairo.Context(surface)
        n1.draw(context)
        n2.draw(context)
        e1.draw(context)
    os.remove(path)
