"""Reproducible visual catalogue with palette filters, explanations, and timings."""
from dataclasses import asdict
from html import escape
from pathlib import Path
from time import perf_counter
import json
import platform
import importlib.metadata
import networkx as nx
from .samples import EXAMPLES, build_example, explain_option, describe_example
from typing import Any
from collections.abc import Sequence, Mapping
from .gallery_page import gallery_page, page_content
from .styles import GraphStyle
from .rendering import export_graph
from .validation import validate_graph
from .option_gallery import generate_controls


def generate_gallery(output: str | Path = 'docs', *, quick: bool = False, all_palettes: bool = False) -> Path:
    destination = Path(output)
    from .site_paths import arrange_pages
    arrange_pages(destination, flat=True)
    figures = destination/'figures'
    figures.mkdir(parents=True, exist_ok=True)
    regular = [example for example in EXAMPLES if example.target_nodes < 1000]
    palettes = GraphStyle.palette_names()
    selected = ('arctic','arctic','linen','blueprint','aurora','porcelain','forest','arctic','orchid','ember','forest','blueprint','linen','porcelain','porcelain','porcelain','porcelain','porcelain','porcelain','blueprint')
    cases = [(example, palette) for example in regular[:3] for palette in ('arctic','ember')] if quick else [(example, palette) for example in regular for palette in palettes] if all_palettes else list(zip(regular, selected))
    if not quick:
        cases.extend((example, palette) for example, palette in zip(EXAMPLES[-3:], ('arctic', 'aurora', 'blueprint')))
        cases.extend((example, palette) for example in EXAMPLES if example.name in ('uk_population','uk_density_only','uk_colors','spain_population') for palette in ('porcelain','arctic'))
    records: list[dict[str, object]] = []
    for spec, palette in cases:
        graph = build_example(spec.name, palette=palette, nodes=120 if quick else None)
        initial = len(graph.nodes)
        started = perf_counter()
        graph.build()
        generation_seconds = perf_counter()-started
        started = perf_counter()
        validation = validate_graph(graph)
        validation_seconds = perf_counter()-started
        style = GraphStyle.named(palette)
        stem = f'{spec.name}-{palette}'
        started = perf_counter()
        dimensions = export_graph(graph, figures/f'{stem}.png', frame='region', margin=16, background=style.background)
        export_graph(graph, figures/f'{stem}.svg', frame='region', margin=16, background=style.background)
        render_seconds = perf_counter()-started
        run = graph.growth()
        accepted = len(graph.nodes)+run.removed_nodes-initial+run.loops_added+run.bridges_added
        command = f'python -m graph_ics render --example {spec.name} --palette {palette} --seed 7'+(' --nodes 120' if quick else '')+f' --output examples/output/{stem}.png'
        report: dict[str, object] = dict(example=spec.name, palette=palette, seed=7, fill_area=run.settings.fill_area, target_nodes=graph.target_nodes, nodes=len(graph.nodes), edges=len(graph.edges),
                                        dimensions=dimensions, attempts=run.attempts, accepted_attempts=accepted, rejected_attempts=run.attempts-accepted, status=run.status.value,
                                        generation_seconds=generation_seconds, validation_seconds=validation_seconds, render_seconds=render_seconds,
                                        validation=asdict(validation), quality=asdict(run.quality_report()), components=nx.number_connected_components(graph.to_networkx()),
                                        command=command, options=spec.options, explanation=spec.explanation, limitation=spec.limitation)
        if run.coverage is not None: report['coverage'] = asdict(run.coverage_report())
        if graph.contours is not None: report['contours'] = asdict(graph.contour_report())
        records.append(report)
        print(f'{stem}: {len(graph.nodes)} nodes, {generation_seconds:.2f}s growth, {validation_seconds:.2f}s validation', flush=True)
    environment = dict(python=platform.python_version(), platform=platform.platform(), dependencies={name: importlib.metadata.version(name) for name in ('graph-ics', 'shapely', 'networkx', 'pycairo')})
    (destination/'manifest.json').write_text(json.dumps(dict(environment=environment, quick=quick, all_palettes=all_palettes, cases=records), indent=2)+'\n', encoding='utf-8')
    from .logo import generate_logos
    generate_logos(destination/'logo')
    generate_controls(destination)
    write_gallery_index(destination, records, quick=quick)
    from .site_structure import build_structure
    build_structure(destination)
    arrange_pages(destination)
    return destination/'index.html'


def write_gallery_index(destination: Path, records: Sequence[Mapping[str, Any]], *, quick: bool = False) -> None:
    """Present measured outputs without rerunning generation or changing their metadata."""
    cards: list[str] = []
    for record in records:
        spec = describe_example(str(record['example']))
        palette = str(record['palette'])
        style = GraphStyle.named(palette)
        stem = f'{spec.name}-{palette}'
        dimensions = record['dimensions']
        swatches = ''.join(f'<span title="{color}" style="background:{color}"></span>' for color in (style.node_color, style.edge_color, style.background or '#ffffff'))
        notes = ''.join(f'<li><code>{escape(option)}</code>: {escape(explain_option(option))}</li>' for option in spec.options)
        count = f"{record['nodes']:,} nodes"
        if record.get('fill_area'): count += f" (cap {record['target_nodes']:,})"
        elif record['nodes'] < record['target_nodes']: count += f" of {record['target_nodes']:,} requested"
        title = spec.title.replace(' / large', '').replace(' experiment', ' (experimental)')
        coverage = record.get('coverage', {})
        coverage_note = f'<p class="hint">Coverage: {coverage.get("occupied_tiles",0)}/{coverage.get("usable_tiles",0)} tiles contain nodes. Tile occupancy is not exact area coverage.</p>' if coverage else ''
        cards.append(f'<article data-palette="{palette}" data-example="{spec.name}" data-large="{str(spec.target_nodes >= 1000).lower()}">'
                     f'<a class="image-link" href="figures/{stem}.png" aria-label="Open {escape(title)} in {palette}"><img loading="lazy" src="figures/{stem}.png" alt="{escape(title)} in {palette}"></a>'
                     f'<div class="swatches" aria-label="Palette colours">{swatches}</div><h2>{escape(title)}</h2><p class="meta">{palette.title()} &middot; {count}<br>{dimensions[0]} &times; {dimensions[1]}</p>'
                     f'<p>{escape(spec.explanation)}</p><div class="downloads"><a href="figures/{stem}.png" download>Download PNG</a><a href="figures/{stem}.svg" download>Download SVG</a></div>'
                     f'<details><summary>Options, limits, and command</summary><ul>{notes}</ul><p class="notice">{escape(spec.limitation)}</p><pre class="command">{escape(str(record["command"]))}</pre>'
                     f'{coverage_note}<p class="hint">Seed {record["seed"]}. {record["attempts"]:,} placement attempts; {record["generation_seconds"]:.2f}s growth. Stop: {escape(str(record["status"]).replace("_", " "))}.</p></details></article>')
    palettes = sorted({str(record['palette']) for record in records})
    names = sorted({str(record['example']) for record in records})
    palette_options = ''.join(f'<option value="{name}">{name.title()}</option>' for name in palettes)
    example_options = ''.join(f'<option value="{name}">{escape(describe_example(name).title)}</option>' for name in names)
    mode = 'Quick preview' if quick else 'Example library'
    content = f'<header class="intro"><span class="eyebrow">{mode}</span><h1>Art grown from connections.</h1><p>graph_ics is a visual art project and Python library for growing sprawling networks. Shape them with text, boundaries and spatial maps, then export still images or animate their growth.</p><div class="paths"><a class="button" href="#examples">Explore the artwork</a><a class="button" href="#start">Make your first graph</a></div></header>'
    hero = next((record for record in records if record['example'] == 'arctic_atlas'), records[0]) if records else None
    if (destination/'logo/figures/landscape@2x.png').exists(): content = '<div class="hero">'+content+'<a href="logo/index.html"><img src="logo/figures/landscape@2x.png" alt="graph_ics wordmark in a continuing graph network"></a></div>'
    elif hero is not None: content = '<div class="hero">'+content+f'<a href="figures/{hero["example"]}-{hero["palette"]}.png"><img src="figures/{hero["example"]}-{hero["palette"]}.png" alt="graph_ics network artwork"></a></div>'
    content += '<section id="examples"><h2>Find your starting point</h2><p class="hint">New here? Start with Sprawling coverage or Text with breathing room. The visual guide compares shapes, connections and angles side by side. Click any image to inspect its full resolution.</p>'
    if quick: content += '<p class="notice">This is the six-scene preview. Run <code>graph-ics gallery</code> without <code>--quick</code> for all recipes and large compositions. Add <code>--all-palettes</code> for every recipe-colour combination.</p>'
    content += '<div class="filters" role="search" aria-label="Filter examples"><label>Search<input id="search" type="search" placeholder="Try angles, text, density..."></label><label>Palette<select id="palette"><option value="">All palettes</option>'+palette_options+'</select></label><label>Example<select id="example"><option value="">All examples</option>'+example_options+'</select></label><label class="check"><input id="large" type="checkbox"> Large compositions</label><button id="reset" type="button">Reset</button><span id="count" aria-live="polite"></span></div><noscript>All examples are shown below. Search, filters and command-copy buttons need JavaScript; images and downloads work without it.</noscript><div class="cards">'+''.join(cards)+'</div><p id="empty" hidden>No examples match. Try a different filter or reset the selection.</p><button id="more" type="button" hidden>Show more examples</button><details><summary>How these examples are generated</summary><p>Each image is built from a fixed recipe and seed, then checked for containment, collisions, angle limits and rival clearance. The displayed node count is the achieved result; dense or narrow regions can stop short of the requested target. Boundary following and terminal anchoring are experimental.</p><p><a href="manifest.json">Download generation measurements and environment details (JSON)</a>. PNG and SVG use the same geometry. Colour previews can differ slightly between screens and renderers.</p></details>'
    content += '</section>'
    content += '<section id="guide">'+page_content((destination/'controls.html').read_text(encoding='utf-8')).replace('<h1>','<h2>').replace('</h1>','</h2>')+'</section>'
    content += '<section id="population-map">'+page_content((destination/'uk_population.html').read_text(encoding='utf-8')).replace('<h1>','<h2>').replace('</h1>','</h2>')+'</section>'
    content += '<section id="start" class="start"><h2>Make it yours</h2><p>From the repository root, install the rendering dependencies in your Python environment and generate your first image.</p><pre class="command">python -m pip install -e ".[render]"\ngraph-ics render --example typography --palette arctic --output examples/output/arctic.png</pre><p>Use <code>graph-ics describe NAME</code> to inspect a recipe and <code>graph-ics render --help</code> for the full command reference. <code>graph-ics gallery --all-palettes</code> generates the complete colour matrix. PNGs, SVGs and replay frames are written locally.</p></section>'
    content += '<section class="about"><h2>About the project</h2><p>graph_ics began in 2022, when I needed graphics for a presentation about money laundering and anti-money laundering and decided to build a generator to create them. It went through several iterations over the years before I finally had time to bring it together as a usable library and share the results.</p><p><a href="https://pippidis.no">Johannes Pippidis Lorentzen</a> &middot; <a href="manuals/index.html">Read the manuals</a></p></section>'
    script = """
const cards=[...document.querySelectorAll('article[data-example]')];const search=document.getElementById('search'),palette=document.getElementById('palette'),example=document.getElementById('example'),large=document.getElementById('large'),more=document.getElementById('more');let limit=9;
function filter(){const query=search.value.trim().toLowerCase();const matches=cards.filter(card=>(!palette.value||card.dataset.palette===palette.value)&&(!example.value||card.dataset.example===example.value)&&(!large.checked||card.dataset.large==='true')&&(!query||card.textContent.toLowerCase().includes(query)));const shown=new Set(matches.slice(0,limit));for(const card of cards)card.hidden=!shown.has(card);document.getElementById('count').textContent=matches.length+' examples';document.getElementById('empty').hidden=matches.length!==0;more.hidden=matches.length<=limit;more.textContent='Show '+Math.min(24,Math.max(0,matches.length-limit))+' more examples';}
for(const control of [search,palette,example,large])control.addEventListener('input',()=>{limit=9;filter();});more.addEventListener('click',()=>{limit+=24;filter();});document.getElementById('reset').addEventListener('click',()=>{search.value=palette.value=example.value='';large.checked=false;limit=9;filter();});filter();
"""
    (destination/'index.html').write_text(gallery_page('Example library', content, script=script), encoding='utf-8')
