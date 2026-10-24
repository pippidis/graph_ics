"""UK / colour only: reproducible Python factory example."""
from pathlib import Path
from examples._support import recipe_main


if __name__ == '__main__':
    recipe_main('uk_colors', Path(__file__).parent)
