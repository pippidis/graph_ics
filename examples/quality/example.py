"""Junction quality and cleanup: reproducible Python factory example."""
from pathlib import Path
from examples._support import recipe_main


if __name__ == '__main__':
    recipe_main('quality', Path(__file__).parent)
