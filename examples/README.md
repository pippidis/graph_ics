# Runnable examples

Each folder contains an entry point, a maintained explanation and local outputs. Run commands from the repository root after installing `.[dev,render]`. The installed library also offers these recipes through `graph-ics list` and `graph-ics render`.

```console
python -m scripts.generate_examples --list
python -m scripts.generate_examples --quick
python -m scripts.generate_examples density text_hug --seed 7
python -m scripts.generate_examples --all
```

The default quick set covers geometry, density, quality, glyph exclusion and scene input. Full generation includes expensive country maps and large compositions. Use `--nodes` for smaller validation runs; it changes the artwork. The runner never rewrites README files. It records a summary in `examples/results.json` and exits nonzero if any selected example fails.

- [Factory and event log](sample_library/README.md)
- [Name composition](name_composition/README.md)
- [Historical graph](basic_graph/README.md)
- [Sprawling coverage](sprawl/README.md)
- [Text with breathing room](typography/README.md)
- [Density gradient](density/README.md)
- [Image density map](raster/README.md)
- [Coordinated sizes](scale/README.md)
- [Irregular region and exclusions](obstacles/README.md)
- [Contour band](band/README.md)
- [Boundary following experiment](follow/README.md)
- [Boundary terminals experiment](terminate/README.md)
- [Cooperating colonies](cooperate/README.md)
- [Repulsion and hard separation](compete/README.md)
- [Controlled cycles](loops/README.md)
- [Newest-tip paths](newest/README.md)
- [Junction quality and cleanup](quality/README.md)
- [Angles / unrestricted](angles_free/README.md)
- [Angles / hard minimum](angles_hard/README.md)
- [Angles / soft preference](angles_soft/README.md)
- [Angles / strict junctions](angles_strict/README.md)
- [Polygon rings](shapes/README.md)
- [Double connections](lines/README.md)
- [UK / spacing only](uk_density_only/README.md)
- [UK / colour only](uk_colors/README.md)
- [Spain / population density](spain_population/README.md)
- [United Kingdom / population density](uk_population/README.md)
- [graph_ics / large](arctic_atlas/README.md)
- [Panoramic network / large](panorama/README.md)
- [Territorial archipelago / large](archipelago/README.md)
- [Fine Rings](fine_rings/README.md)
- [Heavy Rings](heavy_rings/README.md)
- [Solid Nodes](solid_nodes/README.md)
- [Fine Lines](fine_lines/README.md)
- [Heavy Lines](heavy_lines/README.md)
- [Short Links](short_links/README.md)
- [Long Links](long_links/README.md)
- [Wide Gaps](wide_gaps/README.md)
- [Wide Buffers](wide_buffers/README.md)
- [Text Box](text_box/README.md)
- [Text Hug](text_hug/README.md)
- [Graph Lettering](graph_lettering/README.md)
- [Colour Gradient](colour_gradient/README.md)
- [Colour Raster](colour_raster/README.md)
- [Radial Density](radial_density/README.md)
- [Painted Density](painted_density/README.md)
- [Variable Dimensions](variable_dimensions/README.md)
- [Boundary Hidden](boundary_hidden/README.md)
- [Boundary Fine](boundary_fine/README.md)
- [Boundary Bold](boundary_bold/README.md)
- [Area Fill](area_fill/README.md)
- [Animation and replay](animation/README.md)
