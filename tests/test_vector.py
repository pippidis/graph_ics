import pytest
from shapely.geometry import Point

def test_vector_creation(vector):
    p1 = Point(0,0)
    p2 = Point(10,0)
    v1 = vector(p1, p2)

    with pytest.raises(ValueError):
        v2 = vector(p1, p1)

def test_vector_get_length(vector):
    p1 = Point(0,0)
    p2 = Point(10,0)
    v1 = vector(p1, p2)
    assert v1.get_length() == 10.0

def test_vector_get_normalized(vector):
    p1 = Point(0,0)
    p2 = Point(10,0)
    v1 = vector(p1, p2)
    assert v1.get_normalized() == (-1,0)
