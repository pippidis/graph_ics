from pathlib import Path
from scripts.check_site import check_site


def test_site_checks_relative_paths_and_anchors(tmp_path: Path) -> None:
    (tmp_path/'index.html').write_text('<a href="manual.html#intro">Manual</a><img src="image.png"><a href="https://example.org">External</a>')
    (tmp_path/'manual.html').write_text('<h1 id="intro">Manual</h1>')
    (tmp_path/'image.png').write_bytes(b'preview')
    assert check_site(tmp_path) == []
    (tmp_path/'manual.html').write_text('<h1>Missing anchor</h1>')
    (tmp_path/'image.png').unlink()
    errors=check_site(tmp_path)
    assert len(errors) == 2
    assert any('missing anchor' in error for error in errors)
    assert any('missing image.png' in error for error in errors)


def test_balanced_section_extraction() -> None:
    from graph_ics.site_structure import element
    html='<section id="outer"><h2>Outer</h2><section id="inner">Inner</section></section><section id="next">Next</section>'
    assert element(html,'section','outer') == '<section id="outer"><h2>Outer</h2><section id="inner">Inner</section></section>'


def test_guide_navigation_and_unboxed_content() -> None:
    from graph_ics.site_structure import guide_layout
    html=guide_layout('<h1>Text</h1><p>Introduction.</p><h2 id="sizing">Sizing</h2>','text')
    assert 'href="boundaries.html">Previous: Boundaries and filling' in html
    assert 'href="colonies.html">Next: Multiple colonies' in html
    assert 'href="text.html" aria-current="page"' in html
    assert html.index('<h1>Text</h1>') < html.index('On this page')
    assert '<article class="manual">' not in html


def test_brand_returns_home_from_nested_pages() -> None:
    from graph_ics.gallery_page import gallery_page
    for active in ('guide','manuals','logo'):
        html=gallery_page('Example','<h1>Example</h1>',active=active)
        assert 'class="brand" href="../index.html"' in html
        assert '>Home</a>' in html and '>Gallery</a>' in html and '>About</a>' in html


def test_reference_pages_have_one_hierarchy_and_specific_breadcrumb() -> None:
    from graph_ics.site_structure import guide_layout
    html=guide_layout('<h1>Python API</h1><p>Interface.</p>','reference',reference=True,document='API')
    assert 'Reference documents' not in html
    assert 'href="API.html" aria-current="page"' in html
    assert 'href="../guide/reference.html">Reference</a> / <span aria-current="page">Python API</span>' in html
    assert 'Next: Parameters' in html
    assert 'Previous: Scene files' not in html
