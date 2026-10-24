# Polygon rings

Hexagonal hollow nodes retain the same reserved radius as circles.

```console
python -m examples.shapes.example
python -m scripts.generate_examples shapes --seed 19 --nodes 120
```

The default uses seed 7 and the Porcelain palette. The library recipe is defined in `src/samples.py`; the Python entry point calls that same factory so CLI and Python results stay consistent. Edit the returned graph before building to explore settings.

- `node_shape=hexagon`: Visible hollow outline contained within the reserved outer disk.
- `node_outer_radius`: Circumscribed radius used by collision checks and clipping.

`output/figure.png` and `output/figure.svg` show the same geometry. `output/results.json` records the seed, requested/achieved nodes, edges, stop reason, validation and timing. Large country and panorama recipes can take several minutes; `--nodes 120` is a smoke check, not a representative final composition.

Limit: Collision and edge clipping use conservative enclosing disks.

![Example output](output/figure.png)

[Example index](../README.md) | [User guide](../../docs/guide/index.html)
