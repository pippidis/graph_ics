"""Refresh the public website from existing artwork and Markdown manuals."""
from pathlib import Path
import json
import re
import shutil

from graph_ics.gallery import write_gallery_index
from graph_ics.gallery_page import gallery_page, page_content


def main() -> None:
    import markdown
    from PIL import Image
    root = Path(__file__).resolve().parents[1]
    site = root/'docs'
    from graph_ics.site_paths import arrange_pages
    arrange_pages(site, flat=True)
    shutil.copy2(root/'LICENSE',site/'LICENSE.txt')
    shutil.copy2(root/'LICENSE-ARTWORK',site/'LICENSE-ARTWORK.txt')
    manuals = site/'manuals'
    manuals.mkdir(exist_ok=True)
    documents = sorted((root/'scripts/site_content').glob('*.md'))
    items = []
    for source in documents:
        text = source.read_text(encoding='utf-8')
        title = text.splitlines()[0].lstrip('# ')
        content = markdown.markdown(text, extensions=['fenced_code', 'tables', 'toc'])
        content = re.sub(r'href="([A-Z_]+)\.md([#][^"]*)?"', lambda match: 'href="'+match[1]+'.html'+(match[2] or '')+'"', content)
        content = content.replace('href="../../docs/', 'href="../')
        content = content.replace('href="../../README.md"', 'href="index.html"')
        content = content.replace('href="../../src/data/README.md"', 'href="DATA.html"')
        content = re.sub(r'href="(?!https?:|#)([^"]+\.py)"', r'href="sources/\1"', content)
        # Source-code links are downloadable copies, without depending on the future repository URL.
        for match in re.finditer(r'href="sources/([^"]+)"', content):
            original = (source.parent/match[1]).resolve()
            if original.is_file() and original.is_relative_to(root):
                target = manuals/'sources'/original.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original,target)
                content = content.replace(match[0], 'href="sources/'+original.relative_to(root).as_posix()+'"')
        (manuals/(source.stem+'.html')).write_text(gallery_page(title, '<article class="manual">'+content+'</article>', active='manuals'),encoding='utf-8')
        items.append(f'<li><a href="{source.stem}.html">{title}</a></li>')
    data = markdown.markdown((root/'src/data/README.md').read_text(encoding='utf-8'), extensions=['tables'])
    for match in re.finditer(r'href="([^":]+)"',data):
        original=root/'src/data'/match[1]
        if original.is_file(): shutil.copy2(original,manuals/original.name)
    (manuals/'DATA.html').write_text(gallery_page('Data sources','<article class="manual">'+data+'</article>',active='manuals'),encoding='utf-8')
    (manuals/'index.html').write_text(gallery_page('Manuals','<header class="intro"><h1>Make a graph of your own.</h1><p>Install the package, choose a recipe, or describe a composition with Python, JSON or YAML.</p></header><ul>'+''.join(items)+'<li><a href="DATA.html">Data sources and attribution</a></li></ul>',active='manuals'),encoding='utf-8')
    with Image.open(site/'figures/growth.gif') as animation:
        animation.seek(animation.n_frames-1)
        animation.convert('RGB').save(site/'figures/growth-poster.png')
    for name in ('controls.html','uk_population.html','logo/index.html'):
        path=site/name
        content=page_content(path.read_text(encoding='utf-8'))
        content=content.replace('The GIF loops automatically.', 'Use Play animation to watch the sequence, or pause to return to the completed artwork.')
        content=content.replace('src="figures/growth.gif"', 'src="figures/growth-poster.png" data-poster="figures/growth-poster.png" data-animation="figures/growth.gif"')
        page=gallery_page('Logo' if name.startswith('logo') else 'Visual guide' if name.startswith('controls') else 'Spatial maps',content,active='logo' if name.startswith('logo') else 'controls')
        path.write_text(page,encoding='utf-8')
    manifest=json.loads((site/'manifest.json').read_text(encoding='utf-8'))
    write_gallery_index(site,manifest['cases'],quick=manifest.get('quick',False))
    from graph_ics.site_structure import build_structure
    build_structure(site)
    # Store thumbnails separately; original artwork remains available in the viewer/downloads.
    thumbs=site/'thumbnails'
    thumbs.mkdir(exist_ok=True)
    for path in site.glob('*.html'):
        html=path.read_text(encoding='utf-8')
        def thumbnail(match: re.Match[str]) -> str:
            source=site/match[1]
            if not source.is_file(): return match[0]
            with Image.open(source) as image:
                if image.width<=800 and image.height<=800: return match[0]
                image.thumbnail((800,800))
                image.convert('RGB').save(thumbs/source.name,optimize=True)
            return 'src="thumbnails/'+source.name+'"'
        html=re.sub(r'src="(figures/[^"/]+\.png)"',thumbnail,html)
        path.write_text(html,encoding='utf-8')
    arrange_pages(site)
    print('Refreshed gallery, logo page, thumbnails and Markdown manuals.')


if __name__ == '__main__':
    main()
