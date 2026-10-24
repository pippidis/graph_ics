# Newest-tip paths

Select the most recent active node for winding, less evenly distributed growth.

```console
python -m examples.newest.example
python -m scripts.generate_examples newest --seed 19 --nodes 120
```

The default uses seed 7 and the Porcelain palette. The library recipe is defined in `src/samples.py`; the Python entry point calls that same factory so CLI and Python results stay consistent. Edit the returned graph before building to explore settings.

- `NewestTip`: Grow preferentially from the most recently accepted active node.
- `failures_per_parent`: Accumulated failed attempts before retiring a parent node.
- `node_direction_function`: Optional callback returning a proposal heading in radians.

`output/figure.png` and `output/figure.svg` show the same geometry. `output/results.json` records the seed, requested/achieved nodes, edges, stop reason, validation and timing. Large country and panorama recipes can take several minutes; `--nodes 120` is a smoke check, not a representative final composition.

Limit: An explicit parent policy cannot be combined with coverage scheduling or colonies.

![Example output](output/figure.png)

[Example index](../README.md) | [User guide](../../docs/guide/index.html)
