# Spain / population density

Population guides spacing and size in Spain, including the Balearics and excluding the Canary Islands.

```console
python -m examples.spain_population.example
python -m scripts.generate_examples spain_population --seed 19 --nodes 120
```

The default uses seed 7 and the Porcelain palette. The library recipe is defined in `src/samples.py`; the Python entry point calls that same factory so CLI and Python results stay consistent. Edit the returned graph before building to explore settings.

- `SpatialFields.density`: Requested nodes per square world unit, converted to preferred spacing.
- `SpatialFields.coordinated_scale`: Scale radii, lengths, gaps and stroke widths together.

`output/figure.png` and `output/figure.svg` show the same geometry. `output/results.json` records the seed, requested/achieved nodes, edges, stop reason, validation and timing. Large country and panorama recipes can take several minutes; `--nodes 120` is a smoke check, not a representative final composition.

Limit: Small territories may remain empty; this is an artistic map, not a population total.

![Example output](output/figure.png)

[Example index](../README.md) | [User guide](../../docs/guide/index.html)
