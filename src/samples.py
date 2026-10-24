"""Documented, deterministic example factories shared by Python, CLI, and gallery."""
from __future__ import annotations
from dataclasses import dataclass, replace
from math import sin, pi
from .graph import Graph
from .node import NodeShape
from .edge import EdgeStyle
from .styles import GraphStyle
from .fields import SpatialFields, CallableField, ImageField
from .contours import RegionSpec, ContourSettings
from .colonies import Colony, ColonySettings, Interaction
from .growth import GrowthSettings, NewestTip
from .coverage import CoverageSettings
from .quality import AngleSettings
from .text import Text
from shapely.geometry import box, Polygon, MultiPolygon


@dataclass(frozen=True)
class Example:
    name: str
    title: str
    explanation: str
    options: tuple[str, ...]
    limitation: str
    target_nodes: int = 480
    width: float = 600
    height: float = 400


EXAMPLES: tuple[Example, ...] = (
    Example('sprawl', 'Sprawling coverage', 'Balanced branching across a rectangular canvas with bounded reseeding.', ('coverage.tile_size', 'coverage.reseed_attempts', 'failures_per_parent'), 'A node target is an upper goal, not a guarantee of complete packing.'),
    Example('typography', 'Text with breathing room', 'Graph growth wraps around a measured text rectangle; padding scales with font size.', ('Text.size', 'Text.padding_em', 'Text.align'), 'The exclusion is a rectangle, not individual glyph outlines.'),
    Example('density', 'Density gradient', 'Desired population and spacing vary smoothly from dense left to sparse right.', ('SpatialFields.density', 'CoverageSettings', 'spacing_limits'), 'Density is in nodes per square world unit and remains a packing heuristic.'),
    Example('raster', 'Image density map', 'A small scalar image creates a dense central band using world-coordinate bilinear interpolation.', ('ImageField.pixels', 'ImageField.bounds', 'ImageField.outside'), 'Row zero maps to minimum y; a lower-resolution raster smooths small features.'),
    Example('scale', 'Coordinated sizes', 'Rings, gaps, buffers, lengths, and stroke widths grow together across the canvas.', ('SpatialFields.coordinated_scale', 'scale_limits', 'ring_ratio'), 'Large geometry can displace small details; field feasibility is not guaranteed.'),
    Example('obstacles', 'Irregular region and exclusions', 'Full nodes and strokes stay inside a concave outline and outside an internal obstacle.', ('outline_polygon', 'illegal_areas', 'draw_border'), 'Exact containment does not imply every narrow pocket will be filled.'),
    Example('band', 'Contour band', 'Grow within a finite-width band around a supplied polygon.', ('RegionSpec.mode=band', 'band_width', 'padding'), 'This uses supplied polygons. Glyph regions are supported through Text; importing arbitrary SVG paths remains separate.'),
    Example('follow', 'Boundary following experiment', 'Bias growth along a boundary while retaining interior branches.', ('ContourSettings.mode=follow', 'boundary_fraction', 'guidance'), 'Experimental: gaps can remain and a closed boundary loop is not promised.'),
    Example('terminate', 'Boundary terminals experiment', 'Bias branch tips toward the region boundary.', ('ContourSettings.mode=terminate', 'strict_terminals', 'tolerance'), 'Experimental: terminal anchoring can remain unmet; inspect the contour report.'),
    Example('cooperate', 'Cooperating colonies', 'Two colored colonies attract and can join through validated component bridges.', ('Interaction.attraction', 'allow_join', 'target_bridges'), 'Joining is a permission, not a guaranteed connection; ownership survives a join.'),
    Example('compete', 'Repulsion and hard separation', 'Colony headings turn away while an explicit rival gap separates rings and full strokes.', ('Interaction.attraction=-0.3', 'clearance=10', 'Colony.weight'), 'Repulsion alone does not guarantee clearance; weights grant attempts, not area.'),
    Example('loops', 'Controlled cycles', 'Additional short edges close existing components after branch growth.', ('target_extra_edges', 'max_degree', 'loop_distance'), 'Every loop must still pass collision, degree, and both-endpoint angle checks.'),
    Example('newest', 'Newest-tip paths', 'Select the most recent active node for winding, less evenly distributed growth.', ('NewestTip', 'failures_per_parent', 'node_direction_function'), 'An explicit parent policy cannot be combined with coverage scheduling or colonies.'),
    Example('quality', 'Junction quality and cleanup', 'A hard 40-degree limit and preferred 75-degree angle reduce sharp clusters; refill retries freed space.', ('AngleSettings', 'remove_isolated_nodes', 'refill_passes'), 'Stricter aesthetic constraints can increase rejection and underfill.'),
    Example('angles_free', 'Angles / unrestricted', 'No hard or soft angle rule: more acute junctions can survive.', ('minimum=0', 'preferred=0', 'penalty=0'), 'Collision checks still forbid overlapping strokes.'),
    Example('angles_hard', 'Angles / hard minimum', 'Reject every junction below 45 degrees.', ('minimum=45', 'penalty=0'), 'This can reduce feasible connections.'),
    Example('angles_soft', 'Angles / soft preference', 'Prefer 80 degrees with a 0.9 soft penalty, without a hard angle ban.', ('minimum=0', 'preferred=80', 'penalty=0.9'), 'Soft penalties can still accept sharp angles.'),
    Example('angles_strict', 'Angles / strict junctions', 'Combine a 60-degree ban with a 90-degree preference.', ('minimum=60', 'preferred=90', 'penalty=0.9'), 'Stricter controls may leave more open space.'),
    Example('shapes', 'Polygon rings', 'Hexagonal hollow nodes retain the same reserved radius as circles.', ('node_shape=hexagon', 'node_outer_radius'), 'Collision and edge clipping use conservative enclosing disks.'),
    Example('lines', 'Double connections', 'Parallel strokes share a single reserved full-width corridor.', ('edge_style=double', 'edge_thickness=2'), 'Style changes do not open gaps in collision protection.'),
    Example('uk_density_only', 'UK / spacing only', 'The same population raster changes spacing while node dimensions stay fixed.', ('SpatialFields.density',), 'Population is mapped logarithmically; dots are not individual people.', 18000,2192,4000),
    Example('uk_colors', 'UK / colour only', 'Population controls colour; geometry uses uniform dimensions and spacing.', ('color_map',), 'Colour encodes log population density, not node count.', 18000,2192,4000),
    Example('spain_population', 'Spain / population density', 'Population guides spacing and size in Spain, including the Balearics and excluding the Canary Islands.', ('SpatialFields.density','SpatialFields.coordinated_scale'), 'Small territories may remain empty; this is an artistic map, not a population total.', 32000,5000,4000),
    Example('uk_population', 'United Kingdom / population density', 'WorldPop 2020 population density guides spacing and scale inside a Natural Earth UK boundary.', ('log density mapping', 'variable scale', '12000 target nodes'), 'Artistic logarithmic mapping, not one dot per person. Small islands and narrow coasts can remain empty.', 18000, 2192, 4000),
    Example('arctic_atlas', 'graph_ics / large', 'A broad, dense name composition intended for close inspection at full resolution.', ('target_nodes=4000', 'Text.padding_em', 'coverage'), 'Large output takes more generation, validation, and export time.', 4000, 1600, 1000),
    Example('panorama', 'Panoramic network / large', 'A wide network with a coordinated wave in scale and a central title.', ('target_nodes=7000', 'coordinated_scale', 'output dimensions'), 'A high node target may still leave local gaps.', 7000, 2600, 1400),
    Example('archipelago', 'Territorial archipelago / large', 'Three colonies claim a large canvas around obstacle islands with hard rival gaps.', ('target_nodes=8000', 'three colonies', 'pairwise clearance'), 'This is spatial competition, not resource consumption or biological survival.', 8000, 3200, 1800),
)


def example_names() -> tuple[str, ...]:
    return tuple(example.name for example in EXAMPLES)


def describe_example(name: str) -> Example:
    try: return next(example for example in EXAMPLES if example.name == name)
    except StopIteration as error: raise ValueError(f'Unknown example {name!r}') from error


def build_example(name: str = 'typography', *, palette: str = 'arctic', seed: int = 7, nodes: int | None = None, node_shape: NodeShape | None = None, edge_style: EdgeStyle | None = None, angles: AngleSettings | None = None, style: GraphStyle | None = None, fill_area: bool = False, style_overrides: dict[str, float] | None = None) -> Graph:
    """Construct and configure an example; the caller controls build/step/recording."""
    spec = describe_example(name)
    style = style or GraphStyle.named(palette)
    if node_shape is not None: style = replace(style, node_shape=node_shape)
    if edge_style is not None: style = replace(style, edge_style=edge_style)
    if name == "shapes" and node_shape is None: style = replace(style, node_shape="hexagon")
    if name == "lines": style = replace(style, edge_style=edge_style or "double", edge_thickness=2)
    count = spec.target_nodes if nodes is None else nodes
    if type(count) is not int or count < 0: raise ValueError('Node target must be a nonnegative integer')
    width, height = spec.width, spec.height
    outline: Polygon | MultiPolygon = box(0, 0, width, height)
    fields = SpatialFields()
    texts: tuple[Text, ...] = ()
    region = None
    contours = None
    colonies = None
    obstacles: list[Polygon] = []
    if name in ('typography', 'arctic_atlas', 'panorama'):
        title = 'graph_ics'
        texts = (Text(title, width/2, height*0.53, size=height*0.14, align='center', padding=0, padding_em=0.18, color=style.text_color),)
    if name == 'density': fields = SpatialFields(density=CallableField(lambda x, y: 1/(17+25*x/width)**2))
    if name == 'raster': fields = SpatialFields(density=ImageField(((0.0007, 0.003, 0.0007), (0.0007, 0.003, 0.0007)), (0, 0, width, height)))
    if name == 'scale': fields = SpatialFields(coordinated_scale=CallableField(lambda x, y: 0.65+0.8*x/width))
    if name == 'panorama': fields = SpatialFields(coordinated_scale=CallableField(lambda x, y: 0.8+0.35*(1+sin(x/width*4*pi))))
    if name == 'obstacles':
        outline = Polygon([(0, 0), (width, 0), (width, height), (width*0.6, height), (width*0.5, height*0.7), (width*0.4, height), (0, height)])
        obstacles = [box(width*0.4, height*0.2, width*0.6, height*0.45)]
    if name == 'band': region = RegionSpec(box(80, 70, width-80, height-70), mode='band', band_width=90)
    if name in ('follow', 'terminate'): contours = ContourSettings(mode='follow' if name == 'follow' else 'terminate', guidance=0.65, boundary_fraction=0.35)
    if name in ('cooperate', 'compete', 'archipelago'):
        positions = ((width*0.2, height*0.5), (width*0.8, height*0.5)) if name != 'archipelago' else ((width*0.15, height*0.3), (width*0.8, height*0.3), (width*0.5, height*0.8))
        population = tuple(Colony(f'colony_{i}', (point,), color=style.colony_colors[i % len(style.colony_colors)]) for i, point in enumerate(positions))
        if count < len(population): raise ValueError('Node target must accommodate every colony seed')
        rules = tuple(Interaction(a.id, b.id, attraction=0.3 if name == 'cooperate' else -0.3, allow_join=name == 'cooperate', clearance=0 if name == 'cooperate' else 10)
                      for i, a in enumerate(population) for b in population[i+1:])
        colonies = ColonySettings(population, rules, influence_distance=width*0.8 if name == 'cooperate' else 150, target_bridges=1 if name == 'cooperate' else 0, bridge_attempts=600, bridge_distance=55)
    if name == 'archipelago':
        obstacles = [box(width*0.3, height*0.2, width*0.37, height*0.5), box(width*0.6, height*0.55, width*0.7, height*0.7)]
    if name in ('uk_population','uk_density_only','uk_colors','spain_population'):
        from .uk import population_region, population_fields
        country = 'spain' if name == 'spain_population' else 'uk'
        outline, fields = population_region(country), population_fields(country)
        if name == 'uk_density_only': fields = SpatialFields(density=fields.density)
        if name == 'uk_colors':
            from .fields import ConstantField
            fields = SpatialFields(density=ConstantField(1/12**2), spacing_limits=(12,12))
        style = replace(style, node_inner_radius=1.2, node_outer_radius=2.4, node_buffer=0.6, edge_length_min=5, edge_length_max=12, edge_thickness=0.8, edge_node_distance=0.8)
    if style_overrides:
        allowed={'node_inner_radius','node_outer_radius','node_buffer','edge_thickness','edge_node_distance','edge_length_min','edge_length_max'}
        if style_overrides.keys()-allowed: raise ValueError('Unknown dimension override')
        style=replace(style,node_inner_radius=style_overrides.get('node_inner_radius',style.node_inner_radius),node_outer_radius=style_overrides.get('node_outer_radius',style.node_outer_radius),
                      node_buffer=style_overrides.get('node_buffer',style.node_buffer),edge_thickness=style_overrides.get('edge_thickness',style.edge_thickness),
                      edge_node_distance=style_overrides.get('edge_node_distance',style.edge_node_distance),edge_length_min=style_overrides.get('edge_length_min',style.edge_length_min),
                      edge_length_max=style_overrides.get('edge_length_max',style.edge_length_max))
    angle_presets = {'angles_free': AngleSettings(), 'angles_hard': AngleSettings(45), 'angles_soft': AngleSettings(0, 80, 0.9), 'angles_strict': AngleSettings(60, 90, 0.9)}
    selected_angles = angles if angles is not None else angle_presets.get(name, AngleSettings(40, 75, 0.85) if name == 'quality' else AngleSettings(30, 60, 0.5))
    graph = style.create_graph(target_nodes=count, target_seed_nodes=min(150,max(1,count//20)) if name in ('uk_population','uk_density_only','uk_colors','spain_population') else 5, target_extra_edges=25 if name == 'loops' else 0, seed=seed,
                               outline_polygon=None if region else outline, region=region, illegal_areas=obstacles, fields=fields, texts=texts, colonies=colonies, contours=contours,
                               angles=selected_angles, draw_border=name in ('obstacles', 'band', 'follow', 'terminate', 'uk_population','uk_density_only','uk_colors','spain_population'))
    if name == 'uk_colors':
        from .color_fields import ColorRamp
        from .uk import population_field, intensity
        raster = population_field()
        graph.color_field = ColorRamp(CallableField(lambda x,y: intensity(raster.sample(x,y))), (style.edge_color,style.node_color,style.text_color))
    settings = GrowthSettings(fill_area=fill_area, coverage=CoverageSettings(tile_size=40, max_tiles=4096, reseed_attempts=300), failures_per_parent=12, total_attempts=max(3000, count*35),
                              max_degree=5, loop_attempts=500, loop_distance=50, refill_passes=1, refill_attempts=max(100, count*2))
    if name in ('uk_population','uk_density_only','uk_colors','spain_population'): settings = replace(settings, fill_area=True, failures_per_parent=24, seed_attempts=2000, coverage=CoverageSettings(tile_size=60, max_tiles=8192, reseed_attempts=5000, reseed_interval=100, seed_components=True))
    if name == 'uk_colors': settings = replace(settings, refill_passes=2,refill_attempts=100000,coverage=CoverageSettings(tile_size=25,max_tiles=32768,reseed_attempts=15000,reseed_interval=30,seed_components=True))
    if name == 'newest': graph.growth(settings=replace(settings, coverage=None), policy=NewestTip())
    else: graph.growth(settings=settings)
    return graph


OPTION_NOTES: dict[str, str] = {
    'color_map': 'A spatial scalar mapped through colour stops; geometry remains independent.',
    'coverage.tile_size': 'Size of coverage cells used to find underfilled areas.',
    'coverage.reseed_attempts': 'Budget for starting new components in empty space.',
    'failures_per_parent': 'Accumulated failed attempts before retiring a parent node.',
    'Text.size': 'Font size in world units; measured text excludes growth.',
    'Text.padding_em': 'Additional whitespace as a fraction of the font size.',
    'Text.align': 'Left, centre or right alignment around the text anchor.',
    'SpatialFields.density': 'Requested nodes per square world unit, converted to preferred spacing.',
    'CoverageSettings': 'Bias generation toward underfilled cells with finite reseeding.',
    'spacing_limits': 'Minimum and maximum preferred centre spacing from density.',
    'ImageField.pixels': 'Scalar raster values sampled by bilinear interpolation.',
    'ImageField.bounds': 'World rectangle mapping the first and last pixel centres.',
    'ImageField.outside': 'Clamp, return a constant, or error outside the raster.',
    'SpatialFields.coordinated_scale': 'Scale radii, lengths, gaps and stroke widths together.',
    'scale_limits': 'Clamp local geometry multipliers to a positive interval.',
    'ring_ratio': 'Inner radius divided by outer radius; controls the hollow centre.',
    'outline_polygon': 'Allowed shape; full node disks and edge strokes must fit.',
    'illegal_areas': 'Additional polygon obstacles that block visible geometry.',
    'draw_border': 'Draw the supplied outline, independently of growth.',
    'RegionSpec.mode': 'Inside, outside or a finite-width band around a contour.',
    'band_width': 'Full width of the permitted boundary band.',
    'padding': 'Inset or offset that reserves whitespace around the boundary.',
    'ContourSettings.mode': 'Contain, follow tangents, or aim terminal nodes at anchors.',
    'boundary_fraction': 'Fraction of proposals receiving boundary guidance.',
    'guidance': 'Strength of the contour direction bias.',
    'strict_terminals': 'Require terminal constraints; unmet conditions are reported.',
    'tolerance': 'Boundary target tolerance in output units.',
    'Interaction.attraction': 'Signed steering: negative repels, positive attracts.',
    'allow_join': 'Permit bridges between the specified colonies.',
    'target_bridges': 'Requested number of validated inter-colony connections.',
    'clearance': 'Hard minimum separation between rival visible geometry.',
    'Colony.weight': 'Relative share of growth attempts, not guaranteed territory.',
    'target_extra_edges': 'Requested extra connections after branching to create cycles.',
    'max_degree': 'Maximum incident edges at a node.',
    'loop_distance': 'Search radius for possible extra connections.',
    'NewestTip': 'Grow preferentially from the most recently accepted active node.',
    'node_direction_function': 'Optional callback returning a proposal heading in radians.',
    'AngleSettings': 'Hard minimum angle and probabilistic soft preference at junctions.',
    'remove_isolated_nodes': 'Remove unconnected dots when construction finishes.',
    'refill_passes': 'Bounded retries after cleanup frees space.',
    'target_nodes': 'Requested population, including seeds; constraints can prevent it.',
    'coverage': 'Bounded spatial scheduling and reseeding for more even filling.',
    'coordinated_scale': 'Position-dependent scaling of all geometry dimensions.',
    'output dimensions': 'World frame times export scale, including margins.',
    'three colonies': 'Three independently owned seed groups share the region.',
    'pairwise clearance': 'Separate hard exclusion distances for each colony pair.',
    'minimum': 'Hard lower bound on the smaller incident angle, in degrees.',
    'preferred': 'Soft preferred incident angle, in degrees.',
    'penalty': 'Probability-reduction strength below the preferred angle, from 0 to 1.',
    'node_shape': 'Visible hollow outline contained within the reserved outer disk.',
    'node_outer_radius': 'Circumscribed radius used by collision checks and clipping.',
    'edge_style': 'Solid, dashed, dotted or double strokes in one protected corridor.',
    'edge_thickness': 'Full reserved stroke width; double lines use one third per stroke.',
    'log density mapping': 'Compress population density logarithmically for readable spacing.',
    'variable scale': 'Shrink geometry in dense areas to retain city detail.',
    '12000 target nodes': 'Request a large map; the actual count is reported after packing.',
}


def explain_option(option: str) -> str:
    return OPTION_NOTES[option.split('=', 1)[0]]
