"""Generate the public wordmark variants."""
from pathlib import Path
from graph_ics.logo import generate_logos

if __name__ == '__main__': print(generate_logos(Path('docs/logo')))
