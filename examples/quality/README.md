# Junction quality and cleanup

A hard 40-degree limit and preferred 75-degree angle reduce sharp clusters; refill retries freed space.

```console
python -m examples.quality.example
python -m scripts.generate_examples quality --seed 19 --nodes 120
```

The default uses seed 7 and the Porcelain palette. The library recipe is defined in `src/samples.py`; the Python entry point calls that same factory so CLI and Python results stay consistent. Edit the returned graph before building to explore settings.

- `AngleSettings`: Hard minimum angle and probabilistic soft preference at junctions.
- `remove_isolated_nodes`: Remove unconnected dots when construction finishes.
- `refill_passes`: Bounded retries after cleanup frees space.

`output/figure.png` and `output/figure.svg` show the same geometry. `output/results.json` records the seed, requested/achieved nodes, edges, stop reason, validation and timing. Large country and panorama recipes can take several minutes; `--nodes 120` is a smoke check, not a representative final composition.

Limit: Stricter aesthetic constraints can increase rejection and underfill.

![Example output](output/figure.png)

[Example index](../README.md) | [User guide](../../docs/guide/index.html)
