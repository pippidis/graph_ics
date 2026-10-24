"""graph_ics / large: reproducible Python factory example."""
from pathlib import Path
from examples._support import recipe_main


if __name__ == '__main__':
    recipe_main('arctic_atlas', Path(__file__).parent)
