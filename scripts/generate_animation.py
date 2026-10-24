"""Generate replay logs, interactive PNG playback, and measured render timings."""
from pathlib import Path
from time import perf_counter
import json
import platform
import tracemalloc
from graph_ics import Graph, GraphStyle, Text, GrowthSettings, CoverageSettings, Colony, ColonySettings, Interaction
from graph_ics import EventRecorder, EventLog, Playback, ReplayRenderer, export_graph


def main() -> None:
    output = Path(__file__).resolve().parents[1]/'examples/animation/output'
    figures = output/'figures'
    figures.mkdir(parents=True, exist_ok=True)
    colonies = ColonySettings((Colony('coral', ((30, 50),), color='#ef916c'), Colony('blue', ((70, 50),), color='#71b9e8')),
                              (Interaction('coral', 'blue', allow_join=True),), target_bridges=1, bridge_distance=80)
    cases = [('branches', Graph(target_nodes=50, seed=7)),
             ('cleanup_refill', Graph(target_nodes=60, target_seed_nodes=15, target_extra_edges=3, seed=7)),
             ('joining', Graph(target_nodes=2, colonies=colonies, edge_length_max=40, seed=0)),
             ('composition', GraphStyle.historical().create_graph(target_nodes=420, seed=7, texts=(Text('Replay', 300, 195, size=65, align='center', padding=0, padding_em=0.15),)))]
    records: list[dict[str, object]] = []
    for name, graph in cases:
        graph.growth(settings=GrowthSettings(coverage=CoverageSettings(tile_size=40), failures_per_parent=12, total_attempts=12000, loop_attempts=150, refill_passes=1, refill_attempts=150))
        tracemalloc.start()
        started = perf_counter()
        with EventRecorder(graph, path=output/f'{name}.jsonl') as recorder: graph.build()
        growth_seconds = perf_counter()-started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        log = EventLog.load(output/f'{name}.jsonl')
        clock = Playback(log, seconds_per_event=4/max(1, len(log.events)-1))
        renderer = ReplayRenderer(clock, scale=1, margin=10, background='#101318')
        # Gallery output is regenerated intentionally; sequence API itself refuses overwrite.
        destination = figures/name
        destination.mkdir(exist_ok=True)
        times = []
        render_times = []
        write_times = []
        frames = []
        for index in range(49):
            started = perf_counter()
            path = destination/f'frame_{index:03d}.png'
            surface = renderer.render(clock.duration*index/48)
            rendered = perf_counter()
            surface.write_to_png(str(path))
            render_times.append((rendered-started)*1000)
            write_times.append((perf_counter()-rendered)*1000)
            times.append((perf_counter()-started)*1000)
            frames.append(f'figures/{name}/{path.name}')
        export_graph(graph, figures/f'{name}-static.png', frame='region', margin=10, background='#101318')
        records.append(dict(name=name, frames=frames, events=len(recorder.events), nodes=len(graph.nodes), generation_seconds=growth_seconds,
                            generation_peak_bytes=peak, mean_render_ms=sum(render_times)/len(render_times), mean_png_write_ms=sum(write_times)/len(write_times), mean_frame_ms=sum(times)/len(times), max_frame_ms=max(times), log_bytes=(output/f'{name}.jsonl').stat().st_size))
    (output/'manifest.json').write_text(json.dumps(dict(python=platform.python_version(), platform=platform.platform(), cases=records), indent=2)+'\n', encoding='utf-8')
    data = json.dumps(records)
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Growth replay</title><style>body{background:#101318;color:#ddd;font:16px sans-serif;margin:24px}article{margin-bottom:32px}img{display:block;max-width:100%;min-width:240px}input{width:300px}button,select{margin:8px;padding:6px}</style><h1>Growth replay</h1><p>Play, pause, scrub, and change speed. Frames include growing edges, endpoint reveals, cleanup, and colony joins. Static text stays visible. PNGs and logs are local; no video dependency.</p><main></main><script>
const scenes=DATA;
for(const scene of scenes){const card=document.createElement('article');card.innerHTML=`<h2>${scene.name}</h2><p>${scene.nodes} nodes, ${scene.events} events; ${scene.mean_frame_ms.toFixed(2)} ms mean render + PNG write. <a href="${scene.name}.jsonl">Replay log</a> | <a href="figures/${scene.name}-static.png">Static comparison</a></p><img alt="${scene.name} replay"><button>Play</button><input aria-label="Replay position" type="range" min="0" max="48" value="0"><select aria-label="Playback speed"><option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="2">2x</option></select>`;document.querySelector('main').append(card);const image=card.querySelector('img'),button=card.querySelector('button'),slider=card.querySelector('input'),speed=card.querySelector('select');let playing=false,position=0,last=0;const show=()=>{slider.value=Math.floor(position);image.src=scene.frames[Math.floor(position)];};button.onclick=()=>{playing=!playing;if(position>=48)position=0;button.textContent=playing?'Pause':'Play';};slider.oninput=()=>{position=Number(slider.value);show();};function tick(now){if(last&&playing){position=Math.min(48,position+(now-last)/1000*12*Number(speed.value));if(position===48){playing=false;button.textContent='Play';}show();}last=now;requestAnimationFrame(tick);}show();requestAnimationFrame(tick);}
</script></html>""".replace('DATA', data)
    (output/'index.html').write_text(html, encoding='utf-8')
    print(f'Generated {len(records)} replay scenes and 196 frames: {output / "index.html"}')


if __name__ == '__main__':
    main()
