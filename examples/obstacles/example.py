"""Irregular region and exclusions: reproducible Python factory example."""
from pathlib import Path
from examples._support import recipe_main


if __name__ == '__main__':
    recipe_main('obstacles', Path(__file__).parent)
