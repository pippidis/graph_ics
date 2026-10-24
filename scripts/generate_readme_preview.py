"""Regenerate the README wordmark using the public logo function."""
from pathlib import Path
from graph_ics import make_logo


def main() -> None:
    make_logo(Path('docs/images/preview.png'),scale=2)


if __name__ == '__main__': main()
