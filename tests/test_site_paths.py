"""Website relocation preserves relative links and supports repeated generation."""
from pathlib import Path
from graph_ics.site_paths import arrange_pages
from scripts.check_site import check_site


def test_nested_pages_and_roundtrip(tmp_path: Path) -> None:
    (tmp_path/'figures').mkdir()
    (tmp_path/'figures/a.png').write_bytes(b'preview')
    (tmp_path/'index.html').write_text('<a href="examples.html#art">Gallery</a>', encoding='utf-8')
    (tmp_path/'examples.html').write_text('<div id="art"><a href="index.html">Home</a><img src="figures/a.png" data-animation="figures/a.png"></div>', encoding='utf-8')
    arrange_pages(tmp_path)
    assert list(tmp_path.glob('*.html')) == [tmp_path/'index.html']
    page = tmp_path/'gallery/index.html'
    content = page.read_text(encoding='utf-8')
    assert 'href="../index.html"' in content
    assert 'data-animation="../figures/a.png"' in content
    assert not check_site(tmp_path)
    arrange_pages(tmp_path)
    assert page.read_text(encoding='utf-8') == content
    arrange_pages(tmp_path, flat=True)
    assert (tmp_path/'examples.html').exists()
    assert not check_site(tmp_path)
    arrange_pages(tmp_path)
    assert page.read_text(encoding='utf-8') == content
