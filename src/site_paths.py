"""Rebase generated pages and local references into the public website layout."""
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit, urlunsplit

PAGE_PATHS = {'examples.html': 'gallery/index.html', 'about.html': 'about/index.html',
              'controls.html': 'guide/controls.html', 'uk_population.html': 'guide/population.html'}


def arrange_pages(site: Path, *, flat: bool = False) -> None:
    """Use flat intermediate pages during generation, nested pages for the finished site."""
    mapping = {value: key for key, value in PAGE_PATHS.items()} if flat else PAGE_PATHS
    pages = list(site.rglob('*.html'))
    for page in pages:
        old = page.relative_to(site).as_posix()
        new = mapping.get(old, old)
        def reference(value: str) -> str:
            parts = urlsplit(value)
            if parts.scheme or parts.netloc or not parts.path or parts.path.startswith('/'): return value
            target = posixpath.normpath(posixpath.join(posixpath.dirname(old), parts.path))
            target = mapping.get(target, target)
            path = posixpath.relpath(target, posixpath.dirname(new) or '.')
            return urlunsplit(('', '', path, parts.query, parts.fragment))
        content = page.read_text(encoding='utf-8')
        content = re.sub(r'((?:href|src|data-poster|data-animation)=")([^"]+)(")', lambda m: m[1]+reference(m[2])+m[3], content)
        # Homepage hash redirects are script literals rather than HTML attributes.
        if old == 'index.html':
            for before, after in mapping.items(): content = content.replace("'"+before, "'"+after)
        destination = site/new
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding='utf-8')
        if destination != page: page.unlink()
