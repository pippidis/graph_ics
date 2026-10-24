import cairo
import os
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
import networkx as nx

def test_graph_creation(graph):
    g = graph()

def test_graph_str(graph):
    g = graph()
    s = g.__str__()
    assert s == 'GRAPH [Built=False, Nodes=0, Edges=0]'

def test_graph_repr(graph):
    g = graph()
    s = g.__repr__()
    assert s == '{built: False, nodes: 0, edges: 0}'

def test_graph__in_polygon(graph):
    g = graph()
    polygon = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    polygon_2 = Polygon([Point(-1,-1), Point(-2,-1), Point(-2,-2), Point(-1,-2)])
    multi_polygon = MultiPolygon([polygon, polygon_2])

    # Points
    obj_p1 = Point(50,50) # Point within 
    assert g._in_polygon(obj_p1, polygon) == True 
    assert g._in_polygon(obj_p1, multi_polygon) == True 
    obj_p2 = Point(-10,0) # Point outside 
    assert g._in_polygon(obj_p2, polygon) == False 
    
    # Polygons
    obj_a1 = Polygon([Point(1,1), Point(2,1), Point(2,2)]) # Polygon within
    assert g._in_polygon(obj_a1, polygon) == True 
    assert g._in_polygon(obj_a1, multi_polygon) == True 
    obj_a2 = Polygon([Point(-10,-10), Point(-20,-10), Point(-20,-20)]) # Polygon outside
    assert g._in_polygon(obj_a2, polygon) == False 
    assert g._in_polygon(obj_a2, multi_polygon) == False 
    obj_a3 = Polygon([Point(-1,-1), Point(10,10), Point(-2,-2)]) # Polygon partly inside
    assert g._in_polygon(obj_a3, polygon) == False
    obj_a4 = Polygon([Point(-1000,-1000), Point(1000,-1000), Point(1000,1000), Point(-1000,1000)]) # Polygon partly inside
    assert g._in_polygon(obj_a4, polygon) == False
    
    # LineStrings
    obj_l1 = LineString([Point(1,1), Point(2,2)]) # Line within
    assert g._in_polygon(obj_l1, polygon) == True 
    obj_l2 = LineString([Point(-1,-1), Point(-2,-2)]) # Line outside
    assert g._in_polygon(obj_l2, polygon) == False 
    obj_l3 = LineString([Point(-1, 1), Point(2,-2)]) # Line partly inside
    assert g._in_polygon(obj_l3, polygon) == False
    obj_l4 = LineString([Point(-1,-1), Point(200,200)]) # intersects but not within
    assert g._in_polygon(obj_l4, polygon) == False

def test_graph_in_bounds(graph, node):
    polygon = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    g = graph(outline_polygon=polygon)
    n1 = node(10,10)
    n2 = node(-100, -100)
    assert g.in_bounds(n1.center) == True
    assert g.in_bounds(n2.center) == False

def test_graph_in_illegal_areas(graph, node):
    polygon = Polygon([Point(0,0), Point(10,0), Point(10,10), Point(0,10)])
    g0 = graph()
    g1 = graph(illegal_areas=polygon)
    g2 = graph(illegal_areas=[polygon])
    n1 = node(5,5)
    n2 = node(-100, -100)

    # Checking assignment logic of illegal areas
    assert not g0._illegal_areas
    assert g1._illegal_areas == [polygon]
    assert g2._illegal_areas == [polygon]

    # Checking with nodes
    assert g0.in_illegal_areas(n1.center) == False
    assert g1.in_illegal_areas(n1.center) == True
    assert g1.in_illegal_areas(n2.center) == False
    assert g2.in_illegal_areas(n1.center) == True
    assert g2.in_illegal_areas(n2.center) == False

def test_graph_find_seed_node(graph):
    bounds = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    g = graph(outline_polygon=bounds)
    n = g.find_seed_node()
    assert bounds.contains(n.center)
    assert n.is_seed_node == True

def test_graph__build_seed_nodes(graph):
    bounds = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    g1 = graph(target_seed_nodes=1, outline_polygon=bounds)
    g1._build_seed_nodes()
    assert len(g1._nodes) == 1

    g2 = graph(target_nodes=10, target_seed_nodes=10, outline_polygon=bounds, seed=0)
    g2._build_seed_nodes()
    assert len(g2._nodes) == 10

    # A node's full disk must fit: this region has room for none.
    bounds_tiny = Polygon([Point(0,0), Point(1,0), Point(1,1), Point(0,1)])
    g3 = graph(target_seed_nodes=10, outline_polygon=bounds_tiny)
    g3._build_seed_nodes()
    assert len(g3._nodes) == 0

def test_graph_find_node_candidate(graph):
    bounds = Polygon([Point(0,0), Point(10,0), Point(10,10), Point(0,10)])
    g1 = graph(target_seed_nodes=1, outline_polygon=bounds)
    g1._build_seed_nodes()
    fn, n = g1.find_node_candidate()

def test_graph_find_next_node(graph, node, edge):
    bounds = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    g1 = graph(target_seed_nodes=2, outline_polygon=bounds)
    g1._build_seed_nodes()
    n, e = g1.find_next_node()
    assert isinstance(n, node)
    assert isinstance(e, edge)
    assert g1.in_bounds(n.center)

    # Where it cant find a possible next node:
    bounds = Polygon([Point(0,0), Point(1,0), Point(1,1), Point(0,1)])
    g2 = graph(target_seed_nodes=2, outline_polygon=bounds)
    g2._build_seed_nodes()
    n, e = g2.find_next_node()
    assert not n and not e

def test_graph__build_regular_nodes(graph, node):
    bounds = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    g1 = graph(target_seed_nodes=2, target_nodes=10, outline_polygon=bounds)
    g1._build_seed_nodes()
    g1._build_regular_nodes()
    assert len(g1._nodes) > 3
    assert len(g1._edges) > 3
    assert not nx.is_empty(g1.nx_graph)

def test_graph_draw(graph, node, tmp_path):

    bounds = Polygon([Point(0,0), Point(100,0), Point(100,100), Point(0,100)])
    input_nodes = [node(5,5)]
    g = graph(target_seed_nodes=2, target_nodes=100, outline_polygon=bounds, input_nodes=input_nodes)
    g.build()
    min_x, min_y, max_x, max_y = g.get_extent(buffer=10)
    path = str(tmp_path / 'graph.svg') # Need to create a temp svg for testing the draw function
    x, y = g.get_size(buffer=10)
    with cairo.SVGSurface(path, x, y) as surface:
        context = cairo.Context(surface)
        g.draw(context, x_shift=x/4-10, y_shift=y/4-10)
    os.remove(path)

