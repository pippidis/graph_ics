"""Command-line entry points using the same documented Python example factories."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from pathlib import Path
import json
import sys
from math import isfinite
from .samples import EXAMPLES, build_example, describe_example, example_names, explain_option
from .styles import GraphStyle
from .rendering import export_graph
from .replay import EventRecorder, EventLog, Playback
from .animation import ReplayRenderer
from .gallery import generate_gallery
from .validation import validate_graph
from .node import NODE_SHAPES
from .edge import EDGE_STYLES
from .quality import AngleSettings
from .scene import SceneConfig


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog='graph-ics', description='Generate sprawling graph artwork, explained examples, and replay frames.')
    commands = root.add_subparsers(dest='command', required=True)
    commands.add_parser('list', help='List examples and palettes')
    describe = commands.add_parser('describe', help='Explain an example and the controls it demonstrates')
    describe.add_argument('example', choices=example_names())
    for name in ('render', 'frames'):
        command = commands.add_parser(name, help='Export SVG/PNG' if name == 'render' else 'Export replay PNG sequence', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        command.add_argument('--fill-area', action='store_true', help='Keep searching underfilled space; --nodes is a safety cap, not a completion claim')
        command.add_argument('--config', type=Path, help='Load a complete JSON/YAML scene; geometry comes from this file')
        for option in ('node-inner-radius','node-outer-radius','node-buffer','edge-thickness','edge-node-distance','edge-length-min','edge-length-max'):
            command.add_argument('--'+option, type=float, help='Override '+option.replace('-', ' ')+' in world units; see the visual dimensions guide')
        command.add_argument('--example', choices=example_names(), default='typography', help='Recipe to build; describe NAME explains its settings')
        command.add_argument('--palette', choices=GraphStyle.palette_names(), default='arctic', help='Named colour scheme for nodes, lines, text and background')
        command.add_argument('--seed', type=int, default=7, help='Random seed; repeat it to reproduce geometry')
        command.add_argument('--nodes', type=int, help='Requested total nodes, including seeds; packing can stop below this target')
        command.add_argument('--output', type=Path, required=True, help='PNG/SVG file for render, or a new directory for frames')
        command.add_argument('--scale', type=float, default=1, help='Output units per world unit; changes resolution, not growth')
        command.add_argument('--margin', type=float, default=16, help='Empty margin around the region in world units')
        command.add_argument('--transparent', action='store_true', help='Omit the palette background; preserve alpha')
        command.add_argument('--node-shape', choices=NODE_SHAPES, help='Hollow shape inside the reserved node radius')
        command.add_argument('--edge-style', choices=EDGE_STYLES, help='Stroke pattern inside the reserved connection corridor')
        command.add_argument('--minimum-angle', type=float, help='Hard minimum between incident edges, in degrees (0 to 180)')
        command.add_argument('--preferred-angle', type=float, help='Preferred junction angle in degrees; enables a soft target')
        command.add_argument('--angle-penalty', type=float, help='Rejection strength below the preferred angle (0 to 1)')
        if name == 'render':
            command.add_argument('--record', type=Path, help='Also save replay JSONL')
            command.add_argument('--force', action='store_true', help='Replace an existing output/recording')
        else:
            command.add_argument('--gif', action='store_true', help='Export one looping GIF instead of PNG frames; requires an opaque background')
            command.add_argument('--log', type=Path, help='Replay a saved log instead of building an example')
            command.add_argument('--fps', type=float, default=24, help='Frames per second; higher values sample the same replay more often')
            command.add_argument('--seconds-per-event', type=float, default=0.04, help='Seconds allocated to each recorded event; larger values slow growth')
            command.add_argument('--max-frames', type=int, default=10000, help='Safety limit: reject an export requiring more frames')
    gallery = commands.add_parser('gallery', help='Generate the explained visual sample library', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    gallery.add_argument('--output', type=Path, default=Path('docs'), help='Gallery directory; index.html sits above figures/ and controls.html')
    selection = gallery.add_mutually_exclusive_group()
    selection.add_argument('--all-palettes', action='store_true', help='Expand every regular recipe across all ten palettes')
    selection.add_argument('--quick', action='store_true', help='Six small scenes for a smoke check')
    return root


def main(argv: list[str] | None = None) -> int:
    tokens = sys.argv[1:] if argv is None else argv
    args = parser().parse_args(tokens)
    try:
        if args.command == 'list':
            print('Palettes: '+', '.join(GraphStyle.palette_names()))
            for example in EXAMPLES: print(f'{example.name}: {example.title} ({example.target_nodes} target nodes)')
            return 0
        if args.command == 'describe':
            print(json.dumps(dict(asdict(describe_example(args.example)), option_notes={option: explain_option(option) for option in describe_example(args.example).options}), indent=2))
            return 0
        if args.command == 'gallery':
            path = generate_gallery(args.output, quick=args.quick, all_palettes=args.all_palettes).resolve()
            print('Gallery: '+str(path))
            print('Open: '+path.as_uri())
            return 0
        if not isfinite(args.scale) or args.scale <= 0 or not isfinite(args.margin) or args.margin < 0: raise ValueError('Require finite positive scale and nonnegative margin')
        if args.command == 'frames' and (not isfinite(args.fps) or args.fps <= 0 or not isfinite(args.seconds_per_event) or args.seconds_per_event <= 0 or args.max_frames <= 0): raise ValueError('Frame rate, event duration, and frame cap must be positive')
        overrides = {name: getattr(args,name) for name in ('node_inner_radius','node_outer_radius','node_buffer','edge_thickness','edge_node_distance','edge_length_min','edge_length_max') if getattr(args,name) is not None}
        if args.config and any(token.split('=',1)[0] in ('--example','--palette','--seed') for token in tokens): raise ValueError('Put example-independent colours and seed in the scene when using --config')
        scene = SceneConfig.load(args.config) if args.config else None
        if scene and (args.fill_area or overrides or any(value is not None for value in (args.node_shape,args.edge_style,args.minimum_angle,args.preferred_angle,args.angle_penalty,args.nodes))): raise ValueError('Put geometry overrides inside the scene when using --config')
        background = None if args.transparent else scene.background if scene else GraphStyle.named(args.palette).background
        if args.command == 'frames' and args.log is not None:
            if args.config or overrides or args.fill_area: raise ValueError('Cannot rebuild a saved log with config or dimension overrides')
            if any(value is not None for value in (args.node_shape, args.edge_style, args.minimum_angle, args.preferred_angle, args.angle_penalty)):
                raise ValueError('Saved logs preserve shapes, lines and angles; omit geometry overrides with --log')
            log = EventLog.load(args.log)
        else:
            if args.command == 'render':
                if args.output.suffix.lower() not in ('.png', '.svg'): raise ValueError('Output must end in .png or .svg')
                if args.record is not None and args.record.resolve() == args.output.resolve(): raise ValueError('Artwork and replay log need distinct paths')
                for path in (args.output, args.record):
                    if path is not None and path.exists() and not args.force: raise FileExistsError(f'{path} exists; use --force to replace')
            graph = scene.graph if scene else build_example(args.example, fill_area=args.fill_area, style_overrides=overrides, palette=args.palette, seed=args.seed, nodes=args.nodes, node_shape=args.node_shape, edge_style=args.edge_style)
            if any(value is not None for value in (args.minimum_angle, args.preferred_angle, args.angle_penalty)):
                graph.angles = AngleSettings(args.minimum_angle if args.minimum_angle is not None else graph.angles.minimum,
                                            args.preferred_angle if args.preferred_angle is not None else graph.angles.preferred,
                                            args.angle_penalty if args.angle_penalty is not None else graph.angles.penalty)
            if args.command == 'frames' or args.record is not None:
                with EventRecorder(graph, path=args.record if args.command == 'render' else None) as recorder: graph.build()
                log = recorder.snapshot()
            else: graph.build()
            validate_graph(graph)
            if args.command == 'render':
                dimensions = export_graph(graph, args.output, scale=args.scale, margin=args.margin, frame='region', background=background)
                print(json.dumps(dict(output=str(args.output), dimensions=dimensions, nodes=len(graph.nodes), attempts=graph.growth().attempts, status=graph.growth().status.value, coverage=asdict(graph.growth().coverage_report()) if graph.growth().coverage else None)))
                return 0
        renderer = ReplayRenderer(Playback(log, seconds_per_event=args.seconds_per_event), scale=args.scale, margin=args.margin, background=background)
        if args.gif:
            print(renderer.export_gif(args.output, fps=args.fps, max_frames=args.max_frames))
            return 0
        paths = renderer.export_sequence(args.output, fps=args.fps, max_frames=args.max_frames)
        print(f'{len(paths)} frames: {args.output}')
        return 0
    except (ValueError, OSError, ImportError) as error:
        print(f'graph-ics: {error}', file=sys.stderr)
        return 2
