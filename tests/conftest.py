import random
import pytest

# python -m pytest tests/

# Tests import the installed package, without changing sys.path.

@pytest.fixture(autouse=True)
def reproducible_legacy_randomness() -> None:
    random.seed(0)

# Main classes
from graph_ics import Obj
from graph_ics import Vector
from graph_ics import Node
from graph_ics import Edge

from graph_ics import Graph



# Tools: 
@pytest.fixture(scope='module')
def obj():
    fixture = Obj
    return fixture

@pytest.fixture(scope='module')
def vector():
    fixture = Vector
    return fixture   

@pytest.fixture(scope='module')
def node():
    fixture = Node
    return fixture

@pytest.fixture(scope='module')
def edge():
    fixture = Edge
    return fixture


@pytest.fixture(scope='module')
def graph():
    fixture = Graph
    return fixture
