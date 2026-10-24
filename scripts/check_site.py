"""Validate local website references without requiring a server or network."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str,str | None]]) -> None:
        for key,value in attrs:
            if value is None: continue
            if key in ('href','src'): self.references.append(value)
            if key == 'id': self.ids.add(value)


def check_site(directory: Path) -> list[str]:
    failures=[]
    pages={}
    for path in directory.rglob('*.html'):
        parser=References()
        parser.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()]=parser
    for path,parser in pages.items():
        for reference in parser.references:
            url=urlsplit(reference)
            if url.scheme or url.netloc: continue
            target=(path.parent/unquote(url.path)).resolve() if url.path else path
            if target.is_dir(): target=target/'index.html'
            if not target.exists(): failures.append(f'{path}: missing {reference}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids: failures.append(f'{path}: missing anchor {reference}')
    return failures


if __name__ == '__main__':
    errors=check_site(Path('docs'))
    if errors: raise SystemExit('\n'.join(errors))
    print('All local website paths and HTML anchors resolve.')
