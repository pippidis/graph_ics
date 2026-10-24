"""Compose the public Home, Gallery, integrated Guide and About from existing assets."""
from html import escape
from pathlib import Path
import re

from .gallery_page import gallery_page, page_content

CHAPTERS = (
    ('index', 'Getting started'), ('nodes', 'Nodes and connections'), ('maps', 'Colours and spatial maps'),
    ('boundaries', 'Boundaries and filling'), ('text', 'Text'), ('colonies', 'Multiple colonies'),
    ('animation', 'Animation and export'), ('scenes', 'Scene files'), ('reference', 'Reference'),
)


def element(html: str, tag: str, identifier: str) -> str:
    """Extract a balanced element, including nested sections of the same kind."""
    opening=re.search(r'<'+tag+r'\b[^>]*\bid="'+re.escape(identifier)+r'"[^>]*>',html)
    if opening is None: raise ValueError(f'Missing {tag} #{identifier}')
    depth=1
    for match in re.finditer(r'</?'+tag+r'\b[^>]*>',html[opening.end():]):
        depth += -1 if match[0].startswith('</') else 1
        if depth==0: return html[opening.start():opening.end()+match.end()]
    raise ValueError(f'Unclosed {tag} #{identifier}')


REFERENCES = (('API','Python API'),('PARAMETERS','Parameters'),('ALGORITHM','Algorithm'),('SCENES','Scene schema'),('ANIMATION','Replay and export'),('INSTALLATION','Installation'),('EXAMPLES','CLI recipes'),('DATA','Data credits'))


def guide_layout(content: str, current: str, *, reference: bool = False, document: str | None = None) -> str:
    prefix='../guide/' if reference else ''
    ref_prefix='' if reference else '../manuals/'
    items=[]
    for slug,title in CHAPTERS:
        selected=slug==current and document is None
        link=f'<a href="{prefix}{slug}.html"'+(' aria-current="page"' if selected else '')+f'>{title}</a>'
        if slug=='reference' and current=='reference':
            link+='<ul class="reference-nav">'+''.join(f'<li><a href="{ref_prefix}{name}.html"'+(' aria-current="page"' if name==document else '')+f'>{label}</a></li>' for name,label in REFERENCES)+'</ul>'
        items.append('<li>'+link+'</li>')
    nav='<ol>'+''.join(items)+'</ol>'
    pager=[]
    if document is not None:
        position=next(i for i,(name,_) in enumerate(REFERENCES) if name==document)
        previous=REFERENCES[position-1] if position else None
        pager.append(f'<a href="{previous[0]}.html">Previous: {previous[1]}</a>' if previous else f'<a href="{prefix}reference.html">Reference overview</a>')
        if position+1<len(REFERENCES):
            name,label=REFERENCES[position+1]
            pager.append(f'<a href="{name}.html">Next: {label}</a>')
    else:
        index=next(i for i,(slug,_) in enumerate(CHAPTERS) if slug==current)
        for position,label in ((index-1,'Previous'),(index+1,'Next')):
            if 0<=position<len(CHAPTERS):
                slug,title=CHAPTERS[position]
                pager.append(f'<a href="{prefix}{slug}.html">{label}: {title}</a>')
    breadcrumb='<a href="../index.html">Home</a> / <a href="'+prefix+'index.html">Guide</a>'
    if document is not None:
        breadcrumb+=' / <a href="'+prefix+'reference.html">Reference</a> / <span aria-current="page">'+dict(REFERENCES)[document]+'</span>'
    else: breadcrumb+=' / <span aria-current="page">'+dict(CHAPTERS)[current]+'</span>'
    headings=re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>',content,re.S)
    toc='<nav class="on-this-page" aria-label="On this page"><strong>On this page</strong><ul>'+''.join(f'<li><a href="#{identifier}">{re.sub("<[^>]+>","",title)}</a></li>' for identifier,title in headings)+'</ul></nav>' if headings else ''
    content='<!-- CHAPTER CONTENT -->'+content+'<!-- CHAPTER END -->'
    insertion=content.find('</p>')
    if insertion>=0: content=content[:insertion+4]+toc+content[insertion+4:]
    else: content+=toc
    return '<nav class="breadcrumbs" aria-label="Breadcrumb">'+breadcrumb+'</nav><div class="guide-layout"><aside class="chapter-nav"><nav aria-label="Guide chapters">'+nav+'</nav></aside><div class="guide-body"><details class="mobile-chapters"><summary>Guide chapters</summary><nav aria-label="Guide chapters">'+nav+'</nav></details>'+content+'<nav class="chapter-pager" aria-label="Chapter navigation">'+''.join(pager)+'</nav></div></div>'


def build_structure(site: Path) -> None:
    manuals=site/'manuals'
    manuals.mkdir(exist_ok=True)
    for name in ('INSTALLATION','API','PARAMETERS','SCENES','ANIMATION','ALGORITHM','EXAMPLES','DATA'):
        path=manuals/f'{name}.html'
        if not path.exists():
            content=f'<h1>{name.title()}</h1><p>This generated gallery includes the visual guide. The complete reference is available in the source checkout or on the <a href="https://graph-ics.pippidis.no/manuals/{name}.html">project website</a>.</p>'
            path.write_text(gallery_page(name,content,active='manuals'),encoding='utf-8')
    guide=site/'guide' 
    guide.mkdir(exist_ok=True)
    old=(site/'index.html').read_text(encoding='utf-8')
    controls=page_content((site/'controls.html').read_text(encoding='utf-8'))
    scenes=element(controls,'section','scene-files')
    def section(name: str) -> str:
        result=element(controls,'section',name)
        result=re.sub(r'<h2>',f'<h2 id="{name}-heading">',result,count=1)
        return result
    def scene_cards(names: tuple[str,...]) -> str:
        cards=re.findall(r'<article\b.*?</article>',scenes,re.S)
        return '<div class="grid">'+''.join(card for card in cards if any(f'scenes/{name}.json' in card for name in names))+'</div>'
    def doc(name: str) -> str:
        content=page_content((site/'manuals'/f'{name}.html').read_text(encoding='utf-8'))
        if '<!-- CHAPTER CONTENT -->' in content:
            content=content.split('<!-- CHAPTER CONTENT -->',1)[1].split('<!-- CHAPTER END -->',1)[0]
            content=re.sub(r'<nav class="on-this-page".*?</nav>', '',content,flags=re.S)
        return re.sub(r'^<article class="manual">|</article>$','',content)
    def ref(name: str,label: str) -> str:
        return f'<p><a href="../manuals/{name}.html">{label}</a></p>'
    intro={
        'index':'Install the package, make an image, then change one setting at a time. The following chapters combine visual comparisons with runnable examples.',
        'nodes':'Node dimensions and connection rules determine the texture of the artwork. Compare the same kind of graph with different walls, spacing and angles.',
        'maps':'Colour fields change appearance; density and scale fields change where nodes fit. Keep those roles separate when interpreting a map.',
        'boundaries':'A boundary defines where the graph can grow. Filling asks the generator to search for more usable space, within the available node and attempt budgets.',
        'text':'Choose whether text needs a clear rectangular area, a graph that hugs its actual glyphs, or a network that forms the letters themselves.',
        'colonies':'Several growing networks can approach, connect or compete for space. Separation prevents rival geometry from colliding.',
        'animation':'Record accepted growth events once, then replay the same geometry at different speeds or export a still image.',
        'scenes':'Save a complete composition in JSON or YAML, including geometry, maps, text and boundary styling. Use these files as reproducible starting points.',
        'reference':'Look up exact CLI options, Python interfaces and algorithm details. For visual explanations, use the topic chapters in the sidebar.',
    }
    bodies={}
    bodies['index']='<h2 id="first-image">Your first image</h2><p>From a source checkout, create and activate a Python virtual environment, then install the rendering extra. PyPI publication is planned; the commands here work with the repository.</p><pre class="command">python -m pip install -e ".[render]"\ngraph-ics render --example sprawl --palette porcelain --output examples/output/first.png</pre><p>Open <code>examples/output/first.png</code>. Use <code>graph-ics list</code> to find recipes and <code>graph-ics describe sprawl</code> for its settings.</p>'+ref('INSTALLATION','Installation by platform and optional dependencies')+section('seeds')+section('files')
    bodies['nodes']='<h2 id="dimensions">Radius, wall and spacing</h2><p>Ring wall thickness is outer radius minus inner radius. Connection gap separates a line from its endpoint nodes; buffer reserves clearance from unrelated geometry. Length settings describe the visible connection.</p>'+scene_cards(('fine-rings','heavy-rings','solid-nodes','fine-lines','heavy-lines','short-links','long-links','wide-gaps','wide-buffers'))+section('shapes')+section('lines')+section('angles')+ref('PARAMETERS','All geometry parameters and units')
    bodies['maps']=section('palettes')+'<h2 id="fields">Colour, density and scale</h2>'+scene_cards(('colour-gradient','colour-raster','radial-density','painted-density','variable-dimensions'))+'<h2 id="country-maps">Population as one possible input</h2><p>The UK and Spain examples use bundled population estimates. Other scalar measurements or painted fields work too. These maps are illustrative transformations, not one node per person.</p>'+page_content((site/'uk_population.html').read_text(encoding='utf-8')).replace('<h1>','<h2>').replace('</h1>','</h2>')+ref('DATA','Sources, licensing and transformations')
    bodies['boundaries']='<h2 id="contours">Contours and holes</h2><p>Use a GeoJSON Polygon or MultiPolygon. Border visibility and width style the outline; they do not change the allowed region or add collision padding.</p>'+scene_cards(('boundary-hidden','boundary-fine','boundary-bold'))+'<h2 id="coverage">Fill the available area</h2>'+scene_cards(('area-fill',))+section('population')+'<p>Small islands and narrow passages may not fit the selected geometry. Reduce node sizes and edge lengths, or increase the region size. More attempts can improve a bounded search but do not guarantee complete packing. Boundary following and terminal anchoring are experimental.</p>'+ref('PARAMETERS','Coverage, budgets and experimental contour settings')
    bodies['text']='<h2 id="text-modes">Three ways to use text</h2>'+scene_cards(('text-box','text-hug','graph-lettering'))+'<h2 id="sizing">Fit the graph to the letter strokes</h2><p>A stroke must be wider than twice the node outer radius to fit a node. A connection also needs both endpoint radii, endpoint gaps and its visible length. Enlarge the text or shrink the geometry for finer strokes. Glyph holes remain excluded when the graph forms the letters.</p><p>Fonts are resolved locally: use the same installed font to reproduce contours. Complex scripts and narrow glyph features need visual checking.</p>'+ref('SCENES','Text fields, glyph modes and sizing examples')
    cards=re.findall(r'<article\b.*?</article>',element(old,'section','examples'),re.S)
    bodies['colonies']='<h2 id="territories">Cooperation and competition</h2><div class="grid">'+''.join(card for card in cards if any(f'data-example="{name}"' in card for name in ('compete','cooperate')) )+'</div><p>Choose competing colonies for separate territories, or cooperative growth where connections are allowed. Clearance and repulsion serve different purposes: clearance rejects collisions; repulsion steers approaching growth away.</p>'+ref('PARAMETERS','Colony settings and separation rules')+ref('API','Python colony API')
    bodies['animation']=section('animation')+section('output')+ref('ANIMATION','Recording, replay and export reference')
    bodies['scenes']='<h2 id="scene-command">Run a saved scene</h2><pre class="command">graph-ics render --config docs/scenes/area-fill.json --output examples/output/area-fill.png</pre><p>JSON and YAML describe the same scene schema. Paths to boundary files resolve relative to the scene file. Unknown keys are rejected so misspelled options are not silently ignored.</p>'+scene_cards(('area-fill','text-hug','colour-gradient'))+ref('SCENES','Complete scene schema and field definitions')
    bodies['reference']='<h2 id="references">Reference documents</h2><ul>'+''.join(f'<li><a href="../manuals/{name}.html">{label}</a></li>' for name,label in [('API','Python API'),('PARAMETERS','Parameters and units'),('ALGORITHM','Growth algorithm'),('SCENES','Scene schema'),('ANIMATION','Replay format and export'),('INSTALLATION','Installation'),('EXAMPLES','CLI recipes')])+'</ul>'+element(controls,'details','cli')
    for slug,title in CHAPTERS:
        body='<h1>'+title+'</h1><p class="lead">'+intro[slug]+'</p>'+bodies[slug]
        # Embedded previews originate at the website root; chapters sit one directory below it.
        body=re.sub(r'((?:href|src|data-animation|data-poster)=")(figures/|thumbnails/|scenes/|example-growth.jsonl)',r'\1../\2',body)
        body=body.replace('href="controls.html','href="../controls.html').replace('href="index.html#','href="../examples.html#')
        if slug=='reference':
            for anchor,target in [('shapes','nodes'),('lines','nodes'),('angles','nodes'),('seeds','index'),('population','boundaries'),('palettes','maps'),('output','animation'),('animation','animation'),('files','index'),('scene-files','scenes')]:
                body=body.replace(f'href="#{anchor}"',f'href="{target}.html'+('"' if anchor=='scene-files' else f'#{anchor}"'))
        (guide/f'{slug}.html').write_text(gallery_page(title,guide_layout(body,slug),active='guide'),encoding='utf-8')
    # Reference pages share chapter navigation and are not boxed like artwork cards.
    for path in (site/'manuals').glob('*.html'):
        if path.stem in ('index','RELEASING'): continue
        content=doc(path.stem)
        path.write_text(gallery_page(path.stem.title(),guide_layout(content,'reference',reference=True,document=path.stem),active='manuals'),encoding='utf-8')
    (site/'manuals/index.html').write_text(gallery_page('Guide','<h1>The guide</h1><p>Visual explanations and reference documents now belong to one guide.</p><p><a href="../guide/index.html">Start reading the guide</a></p>',active='manuals'),encoding='utf-8')
    releasing=site/'manuals/RELEASING.html'
    if releasing.exists(): releasing.unlink()
    # Retain the existing filtering script, but give the examples their own page.
    content='<header class="intro"><h1>The gallery</h1><p>Explore the artwork, inspect its settings, and find a starting point for your own composition. <a href="guide/index.html">Learn how in the guide.</a></p></header>'+element(old,'section','examples')
    script=old.split('<script>',1)[1].split('</script>',1)[0]
    (site/'examples.html').write_text(gallery_page('Gallery',content,active='gallery',script=script[script.index('const cards='):] if 'const cards=' in script else ''),encoding='utf-8')
    home='<div class="hero"><header class="intro"><span class="eyebrow">Generative network art</span><h1>Art grown from connections.</h1><p>graph_ics is a visual art project and Python library for growing sprawling networks. Shape them with text, boundaries and spatial maps, then export still images or animate their growth.</p><div class="paths"><a class="button" href="examples.html">Explore the gallery</a><a class="button" href="guide/index.html">Make your first graph</a></div><p>A project by <a href="https://pippidis.no">Johannes Pippidis Lorentzen</a>.</p></header><img src="logo/figures/landscape@2x.png" alt="graph_ics lettering in a continuing graph network"></div><section><h2>Give the network a direction.</h2><div class="feature-grid">'
    for name,title,target,description in [('scene-text-hug','Text that belongs in the artwork','text','Let branches hug the shapes of letters, or grow the letters themselves.'),('scene-area-fill','A shape to grow into','boundaries','Explore contours, holes and the space between connections.'),('scene-colour-gradient','Fields of colour and density','maps','Turn a gradient, painted mask or spatial measurement into a composition.')]:
        filename=next((p.name for p in (site/'figures').glob('*.png') if name in p.stem),None)
        if filename: home+=f'<div><a href="guide/{target}.html"><img src="figures/{filename}" alt="{escape(title)}"></a><h3>{title}</h3><p>{description}</p><a href="guide/{target}.html">Explore {target}</a></div>'
    home+='</div></section><section><h2>From a first sketch to a detailed composition.</h2><p>Choose node shapes, connection styles and palettes. Guide growth with boundaries, text, density fields or multiple colonies. Save a scene in JSON or YAML, use the Python API, or record the growth for animation.</p><p><a href="guide/animation.html">Watch the network grow</a> &middot; <a href="about.html">The story behind graph_ics</a></p></section>'
    home_script="function legacyRoute(){if(location.hash){const routes={'#examples':'examples.html#examples','#guide':'guide/index.html','#population-map':'guide/maps.html#country-maps','#start':'guide/index.html'};if(routes[location.hash])location.replace(routes[location.hash]);}}legacyRoute();window.addEventListener('hashchange',legacyRoute);"
    home += '<span id="scene-files"></span>'
    home_script += "if(location.hash==='#scene-files')location.replace('guide/scenes.html');"
    (site/'index.html').write_text(gallery_page('Home',home,active='home',script=home_script),encoding='utf-8')
    about='<header class="intro"><span class="eyebrow">About graph_ics</span><h1>A long-running experiment in connections.</h1><p>graph_ics began in 2022, when I needed graphics for a presentation about money laundering and anti-money laundering and decided to build a generator to create them. It went through several iterations over the years before I finally had time to bring it together as a usable library and share the results.</p><p>A project by <a href="https://pippidis.no">Johannes Pippidis Lorentzen</a>.</p></header><section><h2>Artwork first, a library to explore it.</h2><p>The project explores how small connections fill space, respond to contours and form patterns. The gallery is a collection of reproducible starting points, not a fixed set of finished designs.</p></section><section><h2>Where it is still experimental</h2><p>Boundary following and terminal anchoring need further work. Bounded filling can leave gaps, especially in narrow regions or small disconnected islands. Fonts affect glyph geometry. The guide explains these limitations alongside the relevant examples.</p></section><section><h2>Identity and credits</h2><p>The small branching icon and Porcelain palette reflect the artwork: four hollow blue nodes meet at a red junction.</p><p><a href="logo/index.html">Logo, icon and banner downloads</a> &middot; <a href="manuals/DATA.html">Map data and attribution</a> &middot; <a href="https://creativecommons.org/licenses/by-nc/4.0/">Artwork licence</a> &middot; <a href="https://polyformproject.org/licenses/noncommercial/1.0.0">Code licence</a></p></section>'
    about += '<section><h2>Non-commercial use and commercial licensing</h2><p>The code is available under <a href="https://polyformproject.org/licenses/noncommercial/1.0.0">PolyForm Noncommercial 1.0.0</a>; project-owned artwork and documentation use <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>. For commercial permission, contact <a href="https://pippidis.no">Johannes Pippidis Lorentzen</a> to discuss a separate paid licence. Third-party data retains its own terms.</p></section>'
    (site/'about.html').write_text(gallery_page('About','<div class="about-page">'+about+'</div>',active='about'),encoding='utf-8')
