"""Boundary following experiment: reproducible Python factory example."""
from pathlib import Path
from examples._support import recipe_main


if __name__ == '__main__':
    recipe_main('follow', Path(__file__).parent)
